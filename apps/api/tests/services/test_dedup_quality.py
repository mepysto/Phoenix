"""Tests for QualityScorer."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.models.event import Event, EventType, GeoPrecision, SeverityLevel
from src.services.connectors.base import RawEvent
from src.services.dedup.quality import (
    QualityScorer,
    QualityWeights,
    SOURCE_RELIABILITY,
    GEO_PRECISION_SCORE,
)


class TestSourceReliability:
    """Test source reliability constants."""

    def test_gdacs_highest(self):
        """GDACS should have highest reliability."""
        assert SOURCE_RELIABILITY["GDACS"] == 1.0

    def test_usgs_high(self):
        """USGS should have high reliability."""
        assert SOURCE_RELIABILITY["USGS"] == 0.95

    def test_copernicus_medium(self):
        """Copernicus should have medium reliability."""
        assert SOURCE_RELIABILITY["COPERNICUS"] == 0.85

    def test_eonet_lower(self):
        """EONET should have lower but still good reliability."""
        assert SOURCE_RELIABILITY["EONET"] == 0.8

    def test_all_sources_in_valid_range(self):
        """All source reliability values should be between 0 and 1."""
        for source, reliability in SOURCE_RELIABILITY.items():
            assert 0.0 <= reliability <= 1.0, f"{source} has invalid reliability"


class TestGeoPrecisionScore:
    """Test geo precision scoring constants."""

    def test_exact_highest(self):
        """Exact geo precision should have highest score."""
        assert GEO_PRECISION_SCORE[GeoPrecision.exact] == 1.0

    def test_approximate_medium(self):
        """Approximate geo precision should have medium score."""
        assert GEO_PRECISION_SCORE[GeoPrecision.approximate] == 0.7

    def test_admin1_lower(self):
        """Admin1 geo precision should have lower score."""
        assert GEO_PRECISION_SCORE[GeoPrecision.admin1] == 0.5

    def test_country_low(self):
        """Country geo precision should have low score."""
        assert GEO_PRECISION_SCORE[GeoPrecision.country] == 0.3

    def test_unknown_zero(self):
        """Unknown geo precision should have zero score."""
        assert GEO_PRECISION_SCORE[GeoPrecision.unknown] == 0.0

    def test_precision_ordering(self):
        """Precision scores should be ordered from exact to unknown."""
        assert GEO_PRECISION_SCORE[GeoPrecision.exact] > GEO_PRECISION_SCORE[GeoPrecision.approximate]
        assert GEO_PRECISION_SCORE[GeoPrecision.approximate] > GEO_PRECISION_SCORE[GeoPrecision.admin1]
        assert GEO_PRECISION_SCORE[GeoPrecision.admin1] > GEO_PRECISION_SCORE[GeoPrecision.country]
        assert GEO_PRECISION_SCORE[GeoPrecision.country] > GEO_PRECISION_SCORE[GeoPrecision.unknown]


class TestQualityWeights:
    """Test QualityWeights dataclass."""

    def test_default_weights(self):
        """Default weights should sum to 1.0."""
        weights = QualityWeights()
        total = (
            weights.source_reliability +
            weights.geo_precision +
            weights.completeness +
            weights.recency
        )
        assert abs(total - 1.0) < 0.001

    def test_default_source_reliability_weight(self):
        """Source reliability should have highest default weight."""
        weights = QualityWeights()
        assert weights.source_reliability == 0.4

    def test_default_geo_precision_weight(self):
        """Geo precision should have second highest weight."""
        weights = QualityWeights()
        assert weights.geo_precision == 0.3

    def test_custom_weights(self):
        """Should accept custom weight values."""
        weights = QualityWeights(
            source_reliability=0.5,
            geo_precision=0.3,
            completeness=0.1,
            recency=0.1,
        )
        assert weights.source_reliability == 0.5
        assert weights.geo_precision == 0.3


class TestQualityScorerIncoming:
    """Test QualityScorer.score_incoming method."""

    @pytest.fixture
    def scorer(self):
        return QualityScorer()

    def test_score_incoming_gdacs_exact(self, scorer):
        """GDACS event with exact geo should have high quality."""
        event = RawEvent(
            external_id="test-1",
            source_name="GDACS",
            title="Earthquake in Japan",
            description="Strong earthquake with magnitude 7.2",
            lat=35.6762,
            lng=139.6503,
            country="Japan",
            start_date=datetime.now(timezone.utc),
            glide_number="EQ-2024-000001-JPN",
        )

        score = scorer.score_incoming(
            event,
            GeoPrecision.exact,
            datetime.now(timezone.utc),
        )

        assert score.source_reliability == 1.0
        assert score.geo_precision == 1.0  # exact
        assert score.completeness > 0.8  # Most fields filled
        assert score.recency > 0.9  # Very recent
        assert score.total > 0.9

    def test_score_incoming_eonet_approximate(self, scorer):
        """EONET event with approximate geo should have lower quality."""
        event = RawEvent(
            external_id="test-2",
            source_name="EONET",
            title="Wildfire",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event,
            GeoPrecision.approximate,
            datetime.now(timezone.utc),
        )

        assert score.source_reliability == 0.8
        assert score.geo_precision == 0.7  # approximate
        assert score.total < 0.9

    def test_score_incoming_unknown_source(self, scorer):
        """Unknown source should get default reliability."""
        event = RawEvent(
            external_id="test-3",
            source_name="UNKNOWN_SOURCE",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event,
            GeoPrecision.unknown,
            datetime.now(timezone.utc),
        )

        assert score.source_reliability == 0.5  # Default

    def test_score_incoming_case_insensitive_source(self, scorer):
        """Source name matching should be case insensitive."""
        event = RawEvent(
            external_id="test-4",
            source_name="gdacs",  # lowercase
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event,
            GeoPrecision.exact,
            datetime.now(timezone.utc),
        )

        assert score.source_reliability == 1.0  # Should match GDACS

    def test_recency_decay(self, scorer):
        """Old events should have lower recency score."""
        event = RawEvent(
            external_id="test-4",
            source_name="GDACS",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        # Recent
        score_recent = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc)
        )

        # 30 days ago
        score_old = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc) - timedelta(days=30)
        )

        assert score_recent.recency > score_old.recency

    def test_recency_exponential_decay(self, scorer):
        """Recency should decay exponentially with 30-day half-life."""
        event = RawEvent(
            external_id="test-5",
            source_name="GDACS",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        # At time 0, recency should be ~1.0
        score_now = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc)
        )
        assert score_now.recency > 0.99

        # At 30 days, recency should be ~0.37 (1/e)
        score_30d = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc) - timedelta(days=30)
        )
        assert 0.35 < score_30d.recency < 0.40

    def test_completeness_all_fields(self, scorer):
        """Event with all fields should have high completeness."""
        event = RawEvent(
            external_id="test-6",
            source_name="GDACS",
            title="Complete Event",
            description="Full description here",
            lat=35.0,
            lng=139.0,
            country="Japan",
            start_date=datetime.now(timezone.utc),
            glide_number="EQ-2024-000001-JPN",
        )

        score = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc)
        )

        assert score.completeness == 1.0  # All 6 fields filled

    def test_completeness_minimal_fields(self, scorer):
        """Event with only required fields should have low completeness."""
        event = RawEvent(
            external_id="test-7",
            source_name="OTHER",
            title="Minimal Event",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event, GeoPrecision.unknown, datetime.now(timezone.utc)
        )

        # Only title and start_date are filled (2/6)
        assert score.completeness < 0.5

    def test_custom_weights(self):
        """Custom weights should affect total score."""
        # 100% source reliability weight
        scorer = QualityScorer(
            weights=QualityWeights(
                source_reliability=1.0,
                geo_precision=0.0,
                completeness=0.0,
                recency=0.0,
            )
        )

        event = RawEvent(
            external_id="test-8",
            source_name="GDACS",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event, GeoPrecision.unknown, datetime.now(timezone.utc)
        )

        assert score.total == score.source_reliability

    def test_custom_source_reliability(self):
        """Custom source reliability mapping should be used."""
        scorer = QualityScorer(
            source_reliability={"CUSTOM_SOURCE": 0.99}
        )

        event = RawEvent(
            external_id="test-9",
            source_name="CUSTOM_SOURCE",
            title="Event",
            start_date=datetime.now(timezone.utc),
        )

        score = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc)
        )

        assert score.source_reliability == 0.99

    def test_score_total_in_valid_range(self, scorer):
        """Total score should always be between 0 and 1."""
        event = RawEvent(
            external_id="test-10",
            source_name="GDACS",
            title="Event",
            description="Description",
            lat=35.0,
            lng=139.0,
            country="Japan",
            start_date=datetime.now(timezone.utc),
            glide_number="EQ-2024-000001-JPN",
        )

        score = scorer.score_incoming(
            event, GeoPrecision.exact, datetime.now(timezone.utc)
        )

        assert 0.0 <= score.total <= 1.0
        assert 0.0 <= score.source_reliability <= 1.0
        assert 0.0 <= score.geo_precision <= 1.0
        assert 0.0 <= score.completeness <= 1.0
        assert 0.0 <= score.recency <= 1.0


class TestQualityScorerExisting:
    """Test QualityScorer.score_existing method."""

    @pytest.fixture
    def scorer(self):
        return QualityScorer()

    @pytest.fixture
    def mock_event(self):
        """Create a mock Event for testing."""
        event = MagicMock(spec=Event)
        event.id = MagicMock()
        event.type = EventType.earthquake
        event.title = "Test Earthquake"
        event.description = "A test earthquake event"
        event.latitude = 35.0
        event.longitude = 139.0
        event.geo_precision = GeoPrecision.exact
        event.region = "Japan"
        event.country_code = "JP"
        event.start_date = datetime.now(timezone.utc)
        event.glide_number = "EQ-2024-000001-JPN"
        event.affected_population = 10000
        event.sources = []
        event.created_at = datetime.now(timezone.utc)
        event.updated_at = datetime.now(timezone.utc)
        return event

    def test_score_existing_with_source_name(self, scorer, mock_event):
        """Should use provided source name for reliability."""
        score = scorer.score_existing(mock_event, primary_source_name="GDACS")

        assert score.source_reliability == 1.0

    def test_score_existing_from_event_sources(self, scorer, mock_event):
        """Should use first event source if no source name provided."""
        # Setup mock source
        mock_data_source = MagicMock()
        mock_data_source.name = "USGS"
        mock_event_source = MagicMock()
        mock_event_source.source = mock_data_source
        mock_event.sources = [mock_event_source]

        score = scorer.score_existing(mock_event)

        assert score.source_reliability == 0.95  # USGS reliability

    def test_score_existing_no_source(self, scorer, mock_event):
        """Should use default reliability if no source available."""
        mock_event.sources = []

        score = scorer.score_existing(mock_event)

        assert score.source_reliability == 0.5  # Default

    def test_score_existing_geo_precision(self, scorer, mock_event):
        """Should score geo precision correctly."""
        mock_event.geo_precision = GeoPrecision.exact
        score_exact = scorer.score_existing(mock_event, primary_source_name="GDACS")

        mock_event.geo_precision = GeoPrecision.country
        score_country = scorer.score_existing(mock_event, primary_source_name="GDACS")

        assert score_exact.geo_precision > score_country.geo_precision

    def test_score_existing_completeness(self, scorer, mock_event):
        """Should calculate completeness from event fields."""
        # All fields filled
        score_complete = scorer.score_existing(mock_event, primary_source_name="GDACS")

        # Remove some fields
        mock_event.description = None
        mock_event.glide_number = None
        mock_event.affected_population = None
        score_incomplete = scorer.score_existing(mock_event, primary_source_name="GDACS")

        assert score_complete.completeness > score_incomplete.completeness

    def test_score_existing_recency(self, scorer, mock_event):
        """Should calculate recency from updated_at."""
        mock_event.updated_at = datetime.now(timezone.utc)
        score_recent = scorer.score_existing(mock_event, primary_source_name="GDACS")

        mock_event.updated_at = datetime.now(timezone.utc) - timedelta(days=60)
        score_old = scorer.score_existing(mock_event, primary_source_name="GDACS")

        assert score_recent.recency > score_old.recency
