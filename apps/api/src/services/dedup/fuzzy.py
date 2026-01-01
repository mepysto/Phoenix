"""Fuzzy matching for spatiotemporal event deduplication."""

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from src.models.event import Event, EventType
from src.services.connectors.base import RawEvent
from src.services.dedup.types import MatchCandidate

if TYPE_CHECKING:
    from src.repositories.event_repository import EventRepository


@dataclass(frozen=True)
class FuzzyConfig:
    """Configuration for fuzzy matching."""
    
    radius_meters: int = 50_000       # 50km
    window_hours: int = 48            # 48 hours
    min_match_score: float = 0.6      # Minimum score to consider a match
    title_similarity_enabled: bool = False  # 선택적 title 유사도


class FuzzyMatcher:
    """Fuzzy matching based on spatiotemporal proximity."""
    
    def __init__(
        self,
        event_repo: "EventRepository",
        config: FuzzyConfig | None = None,
    ):
        """Initialize fuzzy matcher.
        
        Args:
            event_repo: Repository for event queries
            config: Matching configuration
        """
        self.event_repo = event_repo
        self.config = config or FuzzyConfig()
    
    async def find_candidates(
        self,
        *,
        event_type: EventType,
        lat: float | None,
        lng: float | None,
        start_date: datetime,
    ) -> list[Event]:
        """Find candidate events using spatiotemporal criteria.
        
        Args:
            event_type: Event type to match
            lat: Latitude (None if no coordinates)
            lng: Longitude (None if no coordinates)
            start_date: Reference start date
            
        Returns:
            List of candidate Events
        """
        # Cannot do spatial matching without coordinates
        if lat is None or lng is None:
            return []
        
        return await self.event_repo.find_candidates_by_spatiotemporal(
            event_type=event_type,
            lat=lat,
            lng=lng,
            start_date=start_date,
            radius_meters=self.config.radius_meters,
            window_hours=self.config.window_hours,
        )
    
    def score_candidate(
        self,
        raw_event: RawEvent,
        candidate: Event,
    ) -> MatchCandidate | None:
        """Score a candidate event for fuzzy match.
        
        Args:
            raw_event: Incoming event to match
            candidate: Potential matching event
            
        Returns:
            MatchCandidate if score >= threshold, None otherwise
        """
        reasons: list[str] = []
        score_components: list[float] = []
        
        # 1. Type match (required - should already be filtered)
        raw_type = (raw_event.event_type_raw or "").lower()
        if candidate.type.value != raw_type:
            # Type already filtered in find_candidates, but double-check
            pass
        
        # 2. Spatial proximity (already filtered by ST_DWithin)
        if raw_event.lat is not None and raw_event.lng is not None:
            if candidate.latitude is not None and candidate.longitude is not None:
                distance_score = self._compute_distance_score(
                    raw_event.lat, raw_event.lng,
                    candidate.latitude, candidate.longitude,
                )
                score_components.append(distance_score)
                reasons.append(f"spatial_proximity={distance_score:.2f}")
        
        # 3. Temporal proximity
        if raw_event.start_date and candidate.start_date:
            time_score = self._compute_time_score(
                raw_event.start_date, candidate.start_date
            )
            score_components.append(time_score)
            reasons.append(f"temporal_proximity={time_score:.2f}")
        
        # 4. Title similarity (optional)
        if self.config.title_similarity_enabled:
            title_score = self._compute_title_similarity(
                raw_event.title, candidate.title
            )
            if title_score > 0.5:
                score_components.append(title_score)
                reasons.append(f"title_similarity={title_score:.2f}")
        
        if not score_components:
            return None
        
        # Average of all scores
        final_score = sum(score_components) / len(score_components)
        
        if final_score < self.config.min_match_score:
            return None
        
        return MatchCandidate(
            event_id=candidate.id,
            method="fuzzy",
            score=final_score,
            reasons=tuple(reasons),
        )
    
    def _compute_distance_score(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """Compute distance-based score (closer = higher).
        
        Uses Haversine formula for distance, then converts to score.
        Score = 1 - (distance / max_distance)
        """
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        # Convert to score (0 at max_distance, 1 at 0)
        max_distance = self.config.radius_meters
        score = max(0, 1 - (distance / max_distance))
        
        return score
    
    def _compute_time_score(
        self,
        date1: datetime,
        date2: datetime,
    ) -> float:
        """Compute time-based score (closer = higher).
        
        Score = 1 - (hours_diff / max_hours)
        """
        diff_seconds = abs((date1 - date2).total_seconds())
        hours_diff = diff_seconds / 3600
        
        max_hours = self.config.window_hours
        score = max(0, 1 - (hours_diff / max_hours))
        
        return score
    
    def _compute_title_similarity(
        self,
        title1: str | None,
        title2: str | None,
    ) -> float:
        """Compute title similarity using simple token overlap.
        
        Uses Jaccard similarity of lowercase tokens.
        """
        if not title1 or not title2:
            return 0.0
        
        # Simple tokenization (split on non-alphanumeric)
        tokens1 = set(re.findall(r'\w+', title1.lower()))
        tokens2 = set(re.findall(r'\w+', title2.lower()))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'of', 'to', 'for'}
        tokens1 -= stop_words
        tokens2 -= stop_words
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
