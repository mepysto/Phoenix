"""Tests for StrongKeyExtractor."""

import pytest
from datetime import datetime, timezone

from src.services.connectors.base import RawEvent
from src.services.dedup.strong_keys import StrongKeyExtractor, PATTERNS


class TestPatterns:
    """Test regex patterns for strong keys."""

    def test_glide_pattern_valid(self):
        """GLIDE pattern should match valid codes."""
        pattern = PATTERNS["glide"]
        assert pattern.search("Event DR-2024-000001-PHL occurred")
        assert pattern.search("EQ-2023-012345-USA is active")
        assert pattern.search("FL-2024-000100-BGD flooding")
        assert pattern.search("TC-2024-000050-JPN typhoon")

    def test_glide_pattern_invalid(self):
        """GLIDE pattern should not match invalid codes."""
        pattern = PATTERNS["glide"]
        assert not pattern.search("DR2024000001PHL")  # Missing dashes
        assert not pattern.search("DR-2024-00001-PHL")  # Wrong number format (5 digits)
        assert not pattern.search("DR-2024-0000001-PHL")  # Wrong number format (7 digits)
        assert not pattern.search("DR-2024-000001-PH")  # 2-letter country code
        assert not pattern.search("D-2024-000001-PHL")  # 1-letter type
        assert not pattern.search("DRX-2024-000001-PHL")  # 3-letter type

    def test_glide_pattern_extracts_correctly(self):
        """GLIDE pattern should extract correct value."""
        pattern = PATTERNS["glide"]
        match = pattern.search("Disaster DR-2024-000001-PHL affected many")
        assert match is not None
        assert match.group(1) == "DR-2024-000001-PHL"

    def test_usgs_pattern_valid(self):
        """USGS pattern should match valid IDs (hex characters only)."""
        pattern = PATTERNS["usgs"]
        assert pattern.search("us7000abcd")
        assert pattern.search("US60008abc")  # Case insensitive (hex chars only)
        assert pattern.search("us7000abcdef12")  # 12 chars
        assert pattern.search("Earthquake us7000abcd magnitude 6.5")

    def test_usgs_pattern_invalid(self):
        """USGS pattern should not match invalid IDs."""
        pattern = PATTERNS["usgs"]
        assert not pattern.search("us7000ab")  # Too short (7 chars after 'us')
        assert not pattern.search("uk7000abcd")  # Wrong prefix
        assert not pattern.search("us7000abcdef123")  # Too long (13 chars)

    def test_usgs_pattern_extracts_correctly(self):
        """USGS pattern should extract correct value."""
        pattern = PATTERNS["usgs"]
        match = pattern.search("Event us7000abcd occurred")
        assert match is not None
        assert match.group(1).lower() == "us7000abcd"

    def test_emsr_pattern_valid(self):
        """EMSR pattern should match Copernicus codes."""
        pattern = PATTERNS["copernicus_emsr"]
        assert pattern.search("EMSR123")
        assert pattern.search("emsr001234")  # Case insensitive
        assert pattern.search("EMSR999999")  # 6 digits
        assert pattern.search("Activation EMSR789 for flooding")

    def test_emsr_pattern_invalid(self):
        """EMSR pattern should not match invalid codes."""
        pattern = PATTERNS["copernicus_emsr"]
        assert not pattern.search("EMSR12")  # Too few digits
        assert not pattern.search("EMSR1234567")  # Too many digits
        assert not pattern.search("EMR123")  # Wrong prefix

    def test_emsr_pattern_extracts_correctly(self):
        """EMSR pattern should extract correct value."""
        pattern = PATTERNS["copernicus_emsr"]
        match = pattern.search("Copernicus EMSR789 activation")
        assert match is not None
        assert match.group(1).upper() == "EMSR789"

    def test_eonet_pattern_valid(self):
        """EONET pattern should match EONET IDs."""
        pattern = PATTERNS["eonet"]
        assert pattern.search("EONET_1234")
        assert pattern.search("eonet_12345")  # Case insensitive
        assert pattern.search("EONET_123456")  # 6 digits

    def test_eonet_pattern_invalid(self):
        """EONET pattern should not match invalid IDs."""
        pattern = PATTERNS["eonet"]
        assert not pattern.search("EONET_123")  # Too few digits
        assert not pattern.search("EONET_1234567")  # Too many digits
        assert not pattern.search("EONET1234")  # Missing underscore


class TestStrongKeyExtractor:
    """Test StrongKeyExtractor class."""

    @pytest.fixture
    def extractor(self):
        return StrongKeyExtractor()

    def test_extract_glide_from_field(self, extractor):
        """Should extract GLIDE from glide_number field with highest confidence."""
        event = RawEvent(
            external_id="test-1",
            source_name="GDACS",
            title="Test Earthquake",
            glide_number="EQ-2024-000123-USA",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        assert len(keys) >= 1
        glide_key = next((k for k in keys if k.key_type == "glide"), None)
        assert glide_key is not None
        assert glide_key.key_value == "EQ-2024-000123-USA"
        assert glide_key.confidence == 1.0
        assert glide_key.origin == "field"

    def test_extract_usgs_from_external_id(self, extractor):
        """Should extract USGS ID from external_id for USGS source."""
        event = RawEvent(
            external_id="us7000abcd",
            source_name="USGS",
            title="M 6.5 - 10km NW of Tokyo",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        usgs_key = next((k for k in keys if k.key_type == "usgs"), None)
        assert usgs_key is not None
        assert usgs_key.key_value == "us7000abcd"
        assert usgs_key.confidence == 1.0

    def test_extract_emsr_from_external_id(self, extractor):
        """Should extract EMSR code from Copernicus external_id."""
        event = RawEvent(
            external_id="EMSR789",
            source_name="COPERNICUS",
            title="Flood in Germany",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        emsr_key = next((k for k in keys if k.key_type == "copernicus_emsr"), None)
        assert emsr_key is not None
        assert emsr_key.key_value == "EMSR789"
        assert emsr_key.confidence == 1.0

    def test_extract_eonet_from_external_id(self, extractor):
        """Should extract EONET ID from EONET source."""
        event = RawEvent(
            external_id="12345",
            source_name="EONET",
            title="Wildfire in California",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        eonet_key = next((k for k in keys if k.key_type == "eonet"), None)
        assert eonet_key is not None
        assert eonet_key.key_value == "EONET_12345"
        assert eonet_key.confidence == 1.0

    def test_extract_glide_from_title(self, extractor):
        """Should extract GLIDE from title with lower confidence."""
        event = RawEvent(
            external_id="test-2",
            source_name="OTHER",
            title="Flooding DR-2024-000456-BRA affected 10000 people",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        glide_key = next((k for k in keys if k.key_type == "glide"), None)
        assert glide_key is not None
        assert glide_key.key_value == "DR-2024-000456-BRA"
        assert glide_key.confidence < 1.0  # Lower confidence from text
        assert glide_key.confidence == 0.9  # Title confidence
        assert glide_key.origin == "title"

    def test_extract_glide_from_description(self, extractor):
        """Should extract GLIDE from description with lower confidence."""
        event = RawEvent(
            external_id="test-3",
            source_name="OTHER",
            title="Severe Earthquake",
            description="The earthquake EQ-2024-000789-JPN caused major damage",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        glide_key = next((k for k in keys if k.key_type == "glide"), None)
        assert glide_key is not None
        assert glide_key.key_value == "EQ-2024-000789-JPN"
        assert glide_key.confidence == 0.7  # Description confidence
        assert glide_key.origin == "description"

    def test_extract_glide_from_source_url(self, extractor):
        """Should extract GLIDE from source_url."""
        event = RawEvent(
            external_id="test-4",
            source_name="OTHER",
            title="Disaster Event",
            source_url="https://example.com/disasters/FL-2024-000100-BGD",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        glide_key = next((k for k in keys if k.key_type == "glide"), None)
        assert glide_key is not None
        assert glide_key.key_value == "FL-2024-000100-BGD"
        assert glide_key.confidence == 0.8  # source_url confidence
        assert glide_key.origin == "source_url"

    def test_extract_deduplicates(self, extractor):
        """Should deduplicate keys with same type and value, keeping highest confidence."""
        event = RawEvent(
            external_id="test-5",
            source_name="GDACS",
            title="Event EQ-2024-000789-JPN",
            description="The earthquake EQ-2024-000789-JPN was severe",
            glide_number="EQ-2024-000789-JPN",  # Same GLIDE in field and text
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)
        glide_keys = [k for k in keys if k.key_type == "glide"]

        # Should have only one GLIDE key (deduplicated)
        assert len(glide_keys) == 1
        # Should keep highest confidence (from field)
        assert glide_keys[0].confidence == 1.0
        assert glide_keys[0].origin == "field"

    def test_extract_multiple_different_keys(self, extractor):
        """Should extract multiple different key types."""
        event = RawEvent(
            external_id="us7000abcd",
            source_name="USGS",
            title="M 6.5 Earthquake EQ-2024-000100-JPN",
            glide_number="EQ-2024-000100-JPN",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        key_types = {k.key_type for k in keys}
        assert "usgs" in key_types
        assert "glide" in key_types

    def test_extract_empty_event(self, extractor):
        """Should return empty list for event with no extractable keys."""
        event = RawEvent(
            external_id="simple-event",
            source_name="OTHER",
            title="Simple event title without any identifiers",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        # Should be empty or have no high-confidence keys
        assert all(k.confidence < 1.0 for k in keys) or len(keys) == 0

    def test_extract_preserves_case_normalization(self, extractor):
        """Should normalize key values correctly."""
        # GLIDE should be uppercase
        event1 = RawEvent(
            external_id="test",
            source_name="GDACS",
            title="Event",
            glide_number="eq-2024-000001-jpn",  # lowercase
            start_date=datetime.now(timezone.utc),
        )
        keys1 = extractor.extract(event1)
        glide_key = next((k for k in keys1 if k.key_type == "glide"), None)
        assert glide_key is not None
        assert glide_key.key_value == "EQ-2024-000001-JPN"  # uppercase

        # USGS should be lowercase
        event2 = RawEvent(
            external_id="US7000ABCD",  # uppercase
            source_name="USGS",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )
        keys2 = extractor.extract(event2)
        usgs_key = next((k for k in keys2 if k.key_type == "usgs"), None)
        assert usgs_key is not None
        assert usgs_key.key_value == "us7000abcd"  # lowercase

    def test_extract_sorted_by_confidence(self, extractor):
        """Should return keys sorted by confidence descending."""
        event = RawEvent(
            external_id="test",
            source_name="OTHER",
            title="Event EQ-2024-000001-JPN",
            description="Related to FL-2024-000002-BGD",
            start_date=datetime.now(timezone.utc),
        )

        keys = extractor.extract(event)

        # Keys should be sorted by confidence descending
        confidences = [k.confidence for k in keys]
        assert confidences == sorted(confidences, reverse=True)

    def test_extract_handles_none_fields(self, extractor):
        """Should handle None optional fields gracefully."""
        event = RawEvent(
            external_id="test",
            source_name="OTHER",
            title="Simple Event",
            description=None,
            source_url=None,
            glide_number=None,
            start_date=datetime.now(timezone.utc),
        )

        # Should not raise an exception
        keys = extractor.extract(event)
        assert isinstance(keys, list)
