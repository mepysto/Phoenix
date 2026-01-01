"""Deduplication service facade for cross-source event matching."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event, EventType, GeoPrecision
from src.repositories import EventRepository, EventSourceRepository
from src.services.connectors.base import RawEvent
from src.services.dedup.fuzzy import FuzzyConfig, FuzzyMatcher
from src.services.dedup.merge import EventMerger, MergePatch
from src.services.dedup.quality import QualityScorer, QualityWeights
from src.services.dedup.strong_keys import StrongKeyExtractor
from src.services.dedup.types import MatchCandidate, MergeResult, QualityScore

logger = logging.getLogger(__name__)


class DedupService:
    """Facade for cross-source event deduplication.
    
    Orchestrates:
    1. Strong key matching (GLIDE, USGS ID, EMSR code, EONET ID)
    2. Fuzzy spatiotemporal matching
    3. Quality-based merge decisions
    """
    
    def __init__(
        self,
        session: AsyncSession,
        fuzzy_config: FuzzyConfig | None = None,
        quality_weights: QualityWeights | None = None,
    ):
        """Initialize dedup service.
        
        Args:
            session: Database session
            fuzzy_config: Configuration for fuzzy matching
            quality_weights: Weights for quality scoring
        """
        self.session = session
        self.event_repo = EventRepository(session)
        self.event_source_repo = EventSourceRepository(session)
        
        self.key_extractor = StrongKeyExtractor()
        self.quality_scorer = QualityScorer(quality_weights)
        self.merger = EventMerger()
        self.fuzzy_matcher = FuzzyMatcher(self.event_repo, fuzzy_config)
    
    async def find_matching_event(
        self,
        raw_event: RawEvent,
        event_type: EventType,
        geo_precision: GeoPrecision,
    ) -> MatchCandidate | None:
        """Find an existing event that matches the incoming raw event.
        
        Strategy:
        1. Try strong key matching first (deterministic)
        2. If no match, try fuzzy spatiotemporal matching
        
        Args:
            raw_event: Incoming event to match
            event_type: Normalized event type
            geo_precision: Determined geo precision
            
        Returns:
            MatchCandidate if found, None otherwise
        """
        # 1. Strong key matching
        match = await self._try_strong_key_match(raw_event)
        if match:
            logger.debug(
                f"Strong key match found for {raw_event.external_id}: "
                f"event_id={match.event_id}, method={match.method}"
            )
            return match
        
        # 2. Fuzzy matching (only if coordinates available)
        if raw_event.lat is not None and raw_event.lng is not None:
            match = await self._try_fuzzy_match(raw_event, event_type)
            if match:
                logger.debug(
                    f"Fuzzy match found for {raw_event.external_id}: "
                    f"event_id={match.event_id}, score={match.score:.2f}"
                )
                return match
        
        return None
    
    async def _try_strong_key_match(
        self, raw_event: RawEvent
    ) -> MatchCandidate | None:
        """Try to find match using strong keys."""
        keys = self.key_extractor.extract(raw_event)
        
        for key in keys:
            if key.key_type == "glide":
                # GLIDE is stored in events.glide_number
                event = await self.event_repo.find_by_glide_number(key.key_value)
                if event:
                    return MatchCandidate(
                        event_id=event.id,
                        method="strong_key",
                        score=key.confidence,
                        reasons=(f"glide_match: {key.key_value}",),
                    )
        
        # Other strong keys (USGS, EMSR, EONET) could be looked up via
        # event_sources table if needed, but for now GLIDE is primary
        
        return None
    
    async def _try_fuzzy_match(
        self,
        raw_event: RawEvent,
        event_type: EventType,
    ) -> MatchCandidate | None:
        """Try to find match using fuzzy spatiotemporal criteria."""
        if not raw_event.start_date:
            return None
        
        # Find candidates
        candidates = await self.fuzzy_matcher.find_candidates(
            event_type=event_type,
            lat=raw_event.lat,
            lng=raw_event.lng,
            start_date=raw_event.start_date,
        )
        
        if not candidates:
            return None
        
        # Score each candidate and pick the best
        best_match: MatchCandidate | None = None
        
        for candidate in candidates:
            match = self.fuzzy_matcher.score_candidate(raw_event, candidate)
            if match and (best_match is None or match.score > best_match.score):
                best_match = match
        
        return best_match
    
    def compute_incoming_quality(
        self,
        raw_event: RawEvent,
        geo_precision: GeoPrecision,
    ) -> QualityScore:
        """Compute quality score for incoming event.
        
        Args:
            raw_event: Incoming event
            geo_precision: Determined precision
            
        Returns:
            QualityScore
        """
        return self.quality_scorer.score_incoming(
            raw_event,
            geo_precision,
            datetime.now(timezone.utc),
        )
    
    def compute_existing_quality(
        self,
        event: Event,
        source_name: str | None = None,
    ) -> QualityScore:
        """Compute quality score for existing event.
        
        Args:
            event: Existing event
            source_name: Primary source name
            
        Returns:
            QualityScore
        """
        return self.quality_scorer.score_existing(event, source_name)
    
    async def get_event_with_sources(self, event_id: UUID) -> Event | None:
        """Get event with sources loaded.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Event with sources or None
        """
        return await self.event_repo.get_by_id_with_sources(event_id)
    
    def build_merge_patch(
        self,
        existing: Event,
        incoming_data: dict[str, Any],
        incoming_quality: float,
        existing_quality: float,
    ) -> MergePatch | None:
        """Build merge patch for updating existing event.
        
        Args:
            existing: Existing event
            incoming_data: Dict of incoming fields
            incoming_quality: Quality score of incoming
            existing_quality: Quality score of existing
            
        Returns:
            MergePatch or None if no updates needed
        """
        return self.merger.build_merge_patch(
            existing=existing,
            incoming=incoming_data,
            incoming_quality=incoming_quality,
            existing_quality=existing_quality,
        )
    
    def create_merge_result(
        self,
        event_id: UUID,
        patch: MergePatch | None,
        incoming_quality: float,
        existing_quality: float,
    ) -> MergeResult:
        """Create merge result.
        
        Args:
            event_id: Event ID
            patch: Applied patch
            incoming_quality: Incoming quality score
            existing_quality: Existing quality score
            
        Returns:
            MergeResult
        """
        return self.merger.create_merge_result(
            event_id, patch, incoming_quality, existing_quality
        )
