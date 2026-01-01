"""Deduplication types and data structures."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class EventKeyCandidate:
    """Strong key extracted from event data."""
    
    key_type: Literal["glide", "usgs", "copernicus_emsr", "eonet"]
    key_value: str
    confidence: float  # 0.0 ~ 1.0
    origin: Literal["field", "title", "description", "source_url", "raw_data"]


@dataclass(frozen=True)
class MatchCandidate:
    """A potential match for cross-source deduplication."""
    
    event_id: UUID
    method: Literal["strong_key", "fuzzy"]
    score: float  # 0.0 ~ 1.0
    reasons: tuple[str, ...]  # Use tuple for frozen dataclass


@dataclass(frozen=True)
class QualityScore:
    """Quality score breakdown for an event."""
    
    source_reliability: float
    geo_precision: float
    completeness: float
    recency: float
    total: float


@dataclass
class MergeResult:
    """Result of merging an event into an existing one."""
    
    event_id: UUID
    updated_fields: list[str]
    chosen_primary_reason: str
    incoming_quality: float
    existing_quality: float
