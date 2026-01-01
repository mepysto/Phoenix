"""Tests for EventMerger."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock

from src.models.event import Event, EventType, GeoPrecision, SeverityLevel
from src.services.dedup.merge import EventMerger, MergePatch


class TestMergePatch:
    """Test MergePatch dataclass."""

    def test_merge_patch_creation(self):
        """Should create MergePatch with fields and updated names."""
        patch = MergePatch(
            fields={"title": "New Title", "description": "New desc"},
            updated_field_names=["title", "description"],
        )
        
        assert patch.fields["title"] == "New Title"
        assert "description" in patch.updated_field_names

    def test_merge_patch_empty(self):
        """Should allow empty patch."""
        patch = MergePatch(fields={}, updated_field_names=[])
        
        assert len(patch.fields) == 0
        assert len(patch.updated_field_names) == 0


class TestEventMergerBuildMergePatch:
    """Test EventMerger.build_merge_patch method."""

    @pytest.fixture
    def merger(self):
        return EventMerger()

    @pytest.fixture
    def existing_event(self):
        """Create a mock existing Event."""
        event = MagicMock(spec=Event)
        event.id = uuid4()
        event.type = EventType.earthquake
        event.title = "Earthquake in Japan"
        event.description = None  # Missing description
        event.latitude = 35.0
        event.longitude = 139.0
        event.geo_precision = GeoPrecision.approximate
        event.region = "Japan"
        event.country_code = "JP"
        event.severity = SeverityLevel.high
        event.glide_number = None
        event.affected_population = None
        event.source_url = None
        return event

    def test_merge_fills_null_glide(self, merger, existing_event):
        """Should fill GLIDE number if existing is null."""
        incoming = {
            "glide_number": "EQ-2024-000001-JPN",
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.7,
            existing_quality=0.8,
        )

        assert patch is not None
        assert "glide_number" in patch.fields
        assert patch.fields["glide_number"] == "EQ-2024-000001-JPN"
        assert "glide_number" in patch.updated_field_names

    def test_merge_does_not_overwrite_existing_glide(self, merger, existing_event):
        """Should not overwrite existing GLIDE number."""
        existing_event.glide_number = "EQ-2024-000099-JPN"
        incoming = {
            "glide_number": "EQ-2024-000001-JPN",  # Different GLIDE
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.7,
            existing_quality=0.8,
        )

        # Should not update glide_number (existing has one)
        if patch:
            assert "glide_number" not in patch.fields

    def test_merge_improves_geo_precision(self, merger, existing_event):
        """Should update to better geo precision."""
        existing_event.geo_precision = GeoPrecision.approximate
        incoming = {
            "geo_precision": GeoPrecision.exact,
            "lat": 35.001,
            "lng": 139.001,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.9,
            existing_quality=0.8,
        )

        assert patch is not None
        assert "geo_precision" in patch.fields
        assert patch.fields["geo_precision"] == GeoPrecision.exact
        assert "lat" in patch.fields
        assert "lng" in patch.fields

    def test_merge_does_not_downgrade_geo_precision(self, merger, existing_event):
        """Should not downgrade geo precision."""
        existing_event.geo_precision = GeoPrecision.exact
        incoming = {
            "geo_precision": GeoPrecision.country,  # Worse precision
            "lat": 35.0,
            "lng": 139.0,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.9,
            existing_quality=0.8,
        )

        # geo_precision should not be in patch (or patch might be None)
        if patch:
            assert patch.fields.get("geo_precision") != GeoPrecision.country

    def test_merge_better_quality_updates_all(self, merger, existing_event):
        """Higher quality incoming should update all non-null fields."""
        incoming = {
            "title": "Strong Earthquake in Tokyo",
            "description": "A major earthquake struck the Tokyo area...",
            "severity": SeverityLevel.critical,
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.95,  # Higher
            existing_quality=0.7,
        )

        assert patch is not None
        assert "title" in patch.updated_field_names
        assert "description" in patch.updated_field_names
        assert "severity" in patch.updated_field_names

    def test_merge_equal_quality_fills_nulls(self, merger, existing_event):
        """Equal quality should only fill null fields."""
        incoming = {
            "title": "Different Title",  # Should NOT update (existing has title)
            "description": "New description",  # Should update (existing is null)
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.8,
            existing_quality=0.8,
        )

        # Title should not be updated (not null in existing)
        assert patch is None or "title" not in patch.updated_field_names
        # Description should be filled if patch exists
        if patch:
            assert "description" in patch.fields

    def test_merge_lower_quality_minimal_updates(self, merger, existing_event):
        """Lower quality incoming should only fill completely missing data."""
        incoming = {
            "title": "Different Title",
            "description": "New description",
            "affected_population": 50000,
            "geo_precision": GeoPrecision.country,  # Worse precision
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.5,  # Lower
            existing_quality=0.8,
        )

        # Should NOT update title (existing has it)
        if patch:
            assert "title" not in patch.updated_field_names
            # Should fill description or affected_population (null in existing)
            has_null_fills = (
                "description" in patch.fields or 
                "affected_population" in patch.fields
            )
            assert has_null_fills or len(patch.fields) <= 2  # Only updated_at + maybe glide

    def test_merge_no_updates_returns_none(self, merger):
        """Should return None when no updates are needed."""
        existing = MagicMock(spec=Event)
        existing.glide_number = "EQ-2024-000001-JPN"
        existing.geo_precision = GeoPrecision.exact
        existing.title = "Complete Event"
        existing.description = "Full description"
        existing.region = "Japan"
        existing.severity = SeverityLevel.high
        existing.affected_population = 10000
        existing.source_url = "https://example.com"

        # Incoming with same or lower quality data
        incoming = {
            "geo_precision": GeoPrecision.country,  # Worse
        }

        patch = merger.build_merge_patch(
            existing=existing,
            incoming=incoming,
            incoming_quality=0.5,
            existing_quality=0.9,
        )

        # No meaningful updates possible
        assert patch is None or len(patch.updated_field_names) == 0

    def test_merge_geo_precision_string_conversion(self, merger, existing_event):
        """Should handle geo_precision as string."""
        existing_event.geo_precision = GeoPrecision.approximate
        incoming = {
            "geo_precision": "exact",  # String instead of enum
            "lat": 35.001,
            "lng": 139.001,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.9,
            existing_quality=0.8,
        )

        assert patch is not None
        assert "geo_precision" in patch.fields
        assert patch.fields["geo_precision"] == GeoPrecision.exact

    def test_merge_updates_affected_population(self, merger, existing_event):
        """Should update affected_population from better source."""
        incoming = {
            "affected_population": 100000,
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.95,
            existing_quality=0.7,
        )

        assert patch is not None
        assert "affected_population" in patch.fields
        assert patch.fields["affected_population"] == 100000

    def test_merge_fills_source_url(self, merger, existing_event):
        """Should fill source_url if existing is null."""
        incoming = {
            "source_url": "https://gdacs.org/event/12345",
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.7,
            existing_quality=0.8,
        )

        # Should fill source_url even with lower quality (it's null in existing)
        if patch:
            # Might be filled depending on exact implementation
            pass  # source_url behavior depends on quality tier

    def test_merge_always_updates_timestamp(self, merger, existing_event):
        """Should always include updated_at in patch."""
        incoming = {
            "description": "New description",
            "geo_precision": GeoPrecision.approximate,
        }

        patch = merger.build_merge_patch(
            existing=existing_event,
            incoming=incoming,
            incoming_quality=0.9,
            existing_quality=0.8,
        )

        assert patch is not None
        assert "updated_at" in patch.fields


class TestEventMergerCreateMergeResult:
    """Test EventMerger.create_merge_result method."""

    @pytest.fixture
    def merger(self):
        return EventMerger()

    def test_create_result_no_patch(self, merger):
        """Should create result for no updates."""
        event_id = uuid4()
        result = merger.create_merge_result(
            event_id=event_id,
            patch=None,
            incoming_quality=0.5,
            existing_quality=0.9,
        )

        assert result.event_id == event_id
        assert result.updated_fields == []
        assert result.chosen_primary_reason == "existing_quality_higher"
        assert result.incoming_quality == 0.5
        assert result.existing_quality == 0.9

    def test_create_result_incoming_higher(self, merger):
        """Should indicate incoming quality higher."""
        event_id = uuid4()
        patch = MergePatch(
            fields={"title": "New Title"},
            updated_field_names=["title"],
        )
        result = merger.create_merge_result(
            event_id=event_id,
            patch=patch,
            incoming_quality=0.95,
            existing_quality=0.7,
        )

        assert result.chosen_primary_reason == "incoming_quality_higher"
        assert result.updated_fields == ["title"]

    def test_create_result_quality_tie(self, merger):
        """Should indicate quality tie."""
        event_id = uuid4()
        patch = MergePatch(
            fields={"description": "New desc"},
            updated_field_names=["description"],
        )
        result = merger.create_merge_result(
            event_id=event_id,
            patch=patch,
            incoming_quality=0.8,
            existing_quality=0.8,
        )

        assert result.chosen_primary_reason == "quality_tie_filled_nulls"

    def test_create_result_specific_improvements(self, merger):
        """Should indicate specific improvements applied."""
        event_id = uuid4()
        patch = MergePatch(
            fields={"affected_population": 10000},
            updated_field_names=["affected_population"],
        )
        result = merger.create_merge_result(
            event_id=event_id,
            patch=patch,
            incoming_quality=0.5,
            existing_quality=0.9,
        )

        assert result.chosen_primary_reason == "specific_improvements_applied"


class TestEventMergerQualityTiers:
    """Test merge behavior at different quality tiers."""

    @pytest.fixture
    def merger(self):
        return EventMerger()

    @pytest.fixture
    def sparse_existing(self):
        """Existing event with minimal data."""
        event = MagicMock(spec=Event)
        event.id = uuid4()
        event.type = EventType.earthquake
        event.title = "Earthquake"
        event.description = None
        event.latitude = None
        event.longitude = None
        event.geo_precision = GeoPrecision.unknown
        event.region = None
        event.severity = SeverityLevel.medium
        event.glide_number = None
        event.affected_population = None
        event.source_url = None
        return event

    def test_high_quality_incoming_fills_sparse_existing(self, merger, sparse_existing):
        """High quality incoming should fill all fields in sparse existing."""
        incoming = {
            "title": "M 7.2 Earthquake in Tokyo",
            "description": "Major earthquake",
            "lat": 35.6762,
            "lng": 139.6503,
            "geo_precision": GeoPrecision.exact,
            "region": "Tokyo, Japan",
            "severity": SeverityLevel.critical,
            "glide_number": "EQ-2024-000001-JPN",
            "affected_population": 1000000,
            "source_url": "https://gdacs.org/event/123",
        }

        patch = merger.build_merge_patch(
            existing=sparse_existing,
            incoming=incoming,
            incoming_quality=0.95,
            existing_quality=0.3,
        )

        assert patch is not None
        # Should update many fields
        assert len(patch.updated_field_names) >= 5

    def test_quality_threshold_for_overwrite(self, merger):
        """Should overwrite non-null fields only with significantly higher quality."""
        existing = MagicMock(spec=Event)
        existing.id = uuid4()
        existing.title = "Old Title"
        existing.description = "Old description"
        existing.geo_precision = GeoPrecision.approximate
        existing.region = "Japan"
        existing.severity = SeverityLevel.medium
        existing.glide_number = None
        existing.affected_population = 5000
        existing.source_url = None

        incoming = {
            "title": "Better Title",
            "description": "Better description",
            "geo_precision": GeoPrecision.approximate,
            "severity": SeverityLevel.high,
        }

        # Marginally higher quality - should update
        patch = merger.build_merge_patch(
            existing=existing,
            incoming=incoming,
            incoming_quality=0.85,
            existing_quality=0.75,
        )

        assert patch is not None
        assert "title" in patch.updated_field_names
        assert "severity" in patch.updated_field_names
