"""Quality scoring for event deduplication."""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.models.event import Event, GeoPrecision
from src.services.connectors.base import RawEvent
from src.services.dedup.types import QualityScore


# Source reliability scores (확정된 정책)
SOURCE_RELIABILITY: dict[str, float] = {
    "GDACS": 1.0,       # 가장 신뢰도 높음
    "USGS": 0.95,       # 실시간 지진 데이터
    "COPERNICUS": 0.85, # 위성 기반
    "EONET": 0.8,       # NASA 자연 이벤트
}

# GeoPrecision scores
GEO_PRECISION_SCORE: dict[GeoPrecision, float] = {
    GeoPrecision.exact: 1.0,
    GeoPrecision.approximate: 0.7,
    GeoPrecision.admin1: 0.5,
    GeoPrecision.country: 0.3,
    GeoPrecision.unknown: 0.0,
}


@dataclass(frozen=True)
class QualityWeights:
    """Weights for quality score calculation."""
    
    source_reliability: float = 0.4
    geo_precision: float = 0.3
    completeness: float = 0.2
    recency: float = 0.1


class QualityScorer:
    """Calculate quality scores for events."""
    
    def __init__(
        self,
        weights: QualityWeights | None = None,
        source_reliability: dict[str, float] | None = None,
    ):
        """Initialize scorer with optional custom weights.
        
        Args:
            weights: Custom weights for score components
            source_reliability: Custom source reliability mapping
        """
        self.weights = weights or QualityWeights()
        self.source_reliability = source_reliability or SOURCE_RELIABILITY
    
    def score_incoming(
        self,
        raw_event: RawEvent,
        geo_precision: GeoPrecision,
        fetched_at: datetime,
    ) -> QualityScore:
        """Calculate quality score for an incoming raw event.
        
        Args:
            raw_event: The raw event to score
            geo_precision: Determined precision level
            fetched_at: When the event was fetched
            
        Returns:
            QualityScore with breakdown
        """
        # Source reliability
        source_name = (raw_event.source_name or "").upper()
        source_score = self.source_reliability.get(source_name, 0.5)
        
        # Geo precision
        geo_score = GEO_PRECISION_SCORE.get(geo_precision, 0.0)
        
        # Completeness (count non-null important fields)
        completeness_score = self._compute_completeness_incoming(raw_event)
        
        # Recency (based on fetched_at)
        recency_score = self._compute_recency(fetched_at)
        
        # Weighted total
        total = (
            self.weights.source_reliability * source_score +
            self.weights.geo_precision * geo_score +
            self.weights.completeness * completeness_score +
            self.weights.recency * recency_score
        )
        
        return QualityScore(
            source_reliability=source_score,
            geo_precision=geo_score,
            completeness=completeness_score,
            recency=recency_score,
            total=total,
        )
    
    def score_existing(
        self,
        event: Event,
        primary_source_name: str | None = None,
    ) -> QualityScore:
        """Calculate quality score for an existing event.
        
        Args:
            event: The existing event to score
            primary_source_name: Name of the primary source (optional)
            
        Returns:
            QualityScore with breakdown
        """
        # Source reliability (from primary source or first EventSource)
        source_name = primary_source_name
        if not source_name and event.sources:
            # Use the first source as primary
            first_source = event.sources[0]
            source_name = first_source.source.name if first_source.source else None
        
        source_score = self.source_reliability.get(
            (source_name or "").upper(), 0.5
        )
        
        # Geo precision
        geo_precision = event.geo_precision or GeoPrecision.unknown
        geo_score = GEO_PRECISION_SCORE.get(geo_precision, 0.0)
        
        # Completeness
        completeness_score = self._compute_completeness_existing(event)
        
        # Recency (based on updated_at or created_at)
        recency_score = self._compute_recency(event.updated_at or event.created_at)
        
        # Weighted total
        total = (
            self.weights.source_reliability * source_score +
            self.weights.geo_precision * geo_score +
            self.weights.completeness * completeness_score +
            self.weights.recency * recency_score
        )
        
        return QualityScore(
            source_reliability=source_score,
            geo_precision=geo_score,
            completeness=completeness_score,
            recency=recency_score,
            total=total,
        )
    
    def _compute_completeness_incoming(self, raw_event: RawEvent) -> float:
        """Compute completeness score for incoming event."""
        fields = [
            raw_event.title,
            raw_event.description,
            raw_event.lat is not None and raw_event.lng is not None,
            raw_event.country,
            raw_event.start_date,
            raw_event.glide_number,
        ]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)
    
    def _compute_completeness_existing(self, event: Event) -> float:
        """Compute completeness score for existing event."""
        fields = [
            event.title,
            event.description,
            event.latitude is not None and event.longitude is not None,
            event.region or event.country_code,
            event.start_date,
            event.glide_number,
            event.affected_population,
        ]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)
    
    def _compute_recency(self, timestamp: datetime | None) -> float:
        """Compute recency score (newer = higher).
        
        Uses exponential decay: score = exp(-days_old / 30)
        """
        if timestamp is None:
            return 0.0
        
        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        age_seconds = (now - timestamp).total_seconds()
        days_old = max(0, age_seconds / 86400)
        
        # Exponential decay with 30-day half-life
        return math.exp(-days_old / 30)
