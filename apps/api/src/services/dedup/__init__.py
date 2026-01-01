"""Deduplication module for cross-source event matching."""

from src.services.dedup.fuzzy import FuzzyConfig, FuzzyMatcher
from src.services.dedup.merge import EventMerger, MergePatch
from src.services.dedup.quality import (
    QualityScorer,
    QualityWeights,
    SOURCE_RELIABILITY,
)
from src.services.dedup.strong_keys import StrongKeyExtractor
from src.services.dedup.types import (
    EventKeyCandidate,
    MatchCandidate,
    MergeResult,
    QualityScore,
)

# Facade
from src.services.dedup.dedup_service import DedupService

__all__ = [
    # Types
    "EventKeyCandidate",
    "MatchCandidate",
    "MergeResult",
    "QualityScore",
    # Components
    "StrongKeyExtractor",
    "QualityScorer",
    "QualityWeights",
    "SOURCE_RELIABILITY",
    "FuzzyConfig",
    "FuzzyMatcher",
    "EventMerger",
    "MergePatch",
    # Facade
    "DedupService",
]
