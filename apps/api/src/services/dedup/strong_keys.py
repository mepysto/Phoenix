"""Strong key extraction for deterministic event matching."""

import re
from typing import Any

from src.services.connectors.base import RawEvent
from src.services.dedup.types import EventKeyCandidate


# Regex patterns for strong keys
PATTERNS: dict[str, re.Pattern[str]] = {
    # GLIDE: e.g., DR-2024-000001-PHL, EQ-2024-000123-USA
    "glide": re.compile(r"\b([A-Z]{2}-\d{4}-\d{6}-[A-Z]{3})\b"),
    
    # USGS event ID: e.g., us7000abcd, us60008xyz
    "usgs": re.compile(r"\b(us[0-9a-f]{8,12})\b", re.IGNORECASE),
    
    # Copernicus EMSR code: e.g., EMSR123, EMSR001234
    "copernicus_emsr": re.compile(r"\b(EMSR\d{3,6})\b", re.IGNORECASE),
    
    # EONET ID: e.g., EONET_1234, EONET_12345 (or pure numeric ID)
    "eonet": re.compile(r"\b(EONET_\d{4,6})\b", re.IGNORECASE),
}


class StrongKeyExtractor:
    """Extract strong keys from event data for deterministic matching."""
    
    def extract(self, raw_event: RawEvent) -> list[EventKeyCandidate]:
        """Extract all strong keys from a raw event.
        
        Priority:
        1. Direct field (glide_number from RawEvent)
        2. external_id pattern matching (source-specific)
        3. Text extraction from title/description/source_url
        
        Args:
            raw_event: The raw event to extract keys from
            
        Returns:
            List of extracted EventKeyCandidate, ordered by confidence
        """
        candidates: list[EventKeyCandidate] = []
        
        # 1. Direct GLIDE field (highest confidence)
        if raw_event.glide_number:
            candidates.append(EventKeyCandidate(
                key_type="glide",
                key_value=raw_event.glide_number.upper(),
                confidence=1.0,
                origin="field",
            ))
        
        # 2. Source-specific external_id patterns
        candidates.extend(self._extract_from_external_id(raw_event))
        
        # 3. Text extraction
        candidates.extend(self._extract_from_text(raw_event))
        
        # Sort by confidence (descending) and deduplicate
        return self._deduplicate_and_sort(candidates)
    
    def _extract_from_external_id(
        self, raw_event: RawEvent
    ) -> list[EventKeyCandidate]:
        """Extract keys from external_id based on source patterns."""
        candidates: list[EventKeyCandidate] = []
        external_id = raw_event.external_id
        source_name = (raw_event.source_name or "").upper()
        
        if not external_id:
            return candidates
        
        # USGS: external_id is the USGS event ID
        if source_name == "USGS" and PATTERNS["usgs"].match(external_id):
            candidates.append(EventKeyCandidate(
                key_type="usgs",
                key_value=external_id.lower(),
                confidence=1.0,
                origin="field",
            ))
        
        # Copernicus: external_id is the EMSR code
        if source_name == "COPERNICUS":
            emsr_match = PATTERNS["copernicus_emsr"].match(external_id)
            if emsr_match:
                candidates.append(EventKeyCandidate(
                    key_type="copernicus_emsr",
                    key_value=emsr_match.group(1).upper(),
                    confidence=1.0,
                    origin="field",
                ))
        
        # EONET: external_id is the EONET event ID
        if source_name == "EONET":
            candidates.append(EventKeyCandidate(
                key_type="eonet",
                key_value=f"EONET_{external_id}",
                confidence=1.0,
                origin="field",
            ))
        
        return candidates
    
    def _extract_from_text(self, raw_event: RawEvent) -> list[EventKeyCandidate]:
        """Extract keys from text fields (title, description, source_url)."""
        candidates: list[EventKeyCandidate] = []
        
        # Text sources with their origins and confidence weights
        text_sources: list[tuple[str | None, str, float]] = [
            (raw_event.title, "title", 0.9),
            (raw_event.description, "description", 0.7),
            (raw_event.source_url, "source_url", 0.8),
        ]
        
        for text, origin, base_confidence in text_sources:
            if not text:
                continue
            
            for key_type, pattern in PATTERNS.items():
                for match in pattern.finditer(text):
                    key_value = match.group(1)
                    
                    # Normalize key values
                    if key_type == "glide":
                        key_value = key_value.upper()
                    elif key_type == "usgs":
                        key_value = key_value.lower()
                    elif key_type == "copernicus_emsr":
                        key_value = key_value.upper()
                    elif key_type == "eonet":
                        key_value = key_value.upper()
                    
                    # Type assertion for origin literal
                    origin_literal: str = origin
                    if origin_literal in ("title", "description", "source_url"):
                        candidates.append(EventKeyCandidate(
                            key_type=key_type,  # type: ignore[arg-type]
                            key_value=key_value,
                            confidence=base_confidence,
                            origin=origin_literal,  # type: ignore[arg-type]
                        ))
        
        return candidates
    
    def _extract_from_raw_data(
        self, raw_data: dict[str, Any] | None
    ) -> list[EventKeyCandidate]:
        """Extract keys from raw_data JSON (if needed in future)."""
        # Reserved for future extension
        return []
    
    def _deduplicate_and_sort(
        self, candidates: list[EventKeyCandidate]
    ) -> list[EventKeyCandidate]:
        """Remove duplicates and sort by confidence."""
        # Deduplicate by (key_type, key_value), keeping highest confidence
        seen: dict[tuple[str, str], EventKeyCandidate] = {}
        
        for candidate in candidates:
            key = (candidate.key_type, candidate.key_value)
            if key not in seen or candidate.confidence > seen[key].confidence:
                seen[key] = candidate
        
        # Sort by confidence descending
        return sorted(seen.values(), key=lambda x: x.confidence, reverse=True)
