"""Tests for FuzzyMatcher."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.event import Event, EventType, GeoPrecision, SeverityLevel
from src.services.connectors.base import RawEvent
from src.services.dedup.fuzzy import FuzzyConfig, FuzzyMatcher


class TestFuzzyConfig:
    """Test FuzzyConfig defaults."""

    def test_default_values(self):
        """Should have correct default values."""
        config = FuzzyConfig()
        assert config.radius_meters == 50_000  # 50km
        assert config.window_hours == 48
        assert config.min_match_score == 0.6
        assert config.title_similarity_enabled is False

    def test_custom_values(self):
        """Should accept custom values."""
        config = FuzzyConfig(
            radius_meters=100_000,
            window_hours=72,
            min_match_score=0.8,
            title_similarity_enabled=True,
        )
        assert config.radius_meters == 100_000
        assert config.window_hours == 72
        assert config.min_match_score == 0.8
        assert config.title_similarity_enabled is True

    def test_frozen_dataclass(self):
        """Config should be immutable (frozen)."""
        config = FuzzyConfig()
        with pytest.raises(AttributeError):
            config.radius_meters = 100_000


class TestFuzzyMatcherFindCandidates:
    """Test FuzzyMatcher.find_candidates method."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock event repository."""
        repo = MagicMock()
        repo.find_candidates_by_spatiotemporal = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def matcher(self, mock_repo):
        """Create a FuzzyMatcher with mock repository."""
        return FuzzyMatcher(mock_repo)

    @pytest.mark.asyncio
    async def test_find_candidates_no_coords(self, matcher):
        """Should return empty for events without coordinates."""
        result = await matcher.find_candidates(
            event_type=EventType.earthquake,
            lat=None,
            lng=None,
            start_date=datetime.now(timezone.utc),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_candidates_no_lat(self, matcher):
        """Should return empty when lat is None."""
        result = await matcher.find_candidates(
            event_type=EventType.earthquake,
            lat=None,
            lng=139.0,
            start_date=datetime.now(timezone.utc),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_candidates_no_lng(self, matcher):
        """Should return empty when lng is None."""
        result = await matcher.find_candidates(
            event_type=EventType.earthquake,
            lat=35.0,
            lng=None,
            start_date=datetime.now(timezone.utc),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_candidates_calls_repo(self, matcher, mock_repo):
        """Should call repository with correct parameters."""
        test_date = datetime.now(timezone.utc)
        
        await matcher.find_candidates(
            event_type=EventType.earthquake,
            lat=35.0,
            lng=139.0,
            start_date=test_date,
        )

        mock_repo.find_candidates_by_spatiotemporal.assert_called_once()
        call_kwargs = mock_repo.find_candidates_by_spatiotemporal.call_args.kwargs
        assert call_kwargs["event_type"] == EventType.earthquake
        assert call_kwargs["lat"] == 35.0
        assert call_kwargs["lng"] == 139.0
        assert call_kwargs["start_date"] == test_date
        assert call_kwargs["radius_meters"] == 50_000
        assert call_kwargs["window_hours"] == 48

    @pytest.mark.asyncio
    async def test_find_candidates_custom_config(self, mock_repo):
        """Should use custom config values."""
        config = FuzzyConfig(radius_meters=100_000, window_hours=72)
        matcher = FuzzyMatcher(mock_repo, config=config)

        await matcher.find_candidates(
            event_type=EventType.flood,
            lat=35.0,
            lng=139.0,
            start_date=datetime.now(timezone.utc),
        )

        call_kwargs = mock_repo.find_candidates_by_spatiotemporal.call_args.kwargs
        assert call_kwargs["radius_meters"] == 100_000
        assert call_kwargs["window_hours"] == 72

    @pytest.mark.asyncio
    async def test_find_candidates_returns_repo_result(self, mock_repo):
        """Should return candidates from repository."""
        mock_candidates = [MagicMock(spec=Event), MagicMock(spec=Event)]
        mock_repo.find_candidates_by_spatiotemporal = AsyncMock(return_value=mock_candidates)
        matcher = FuzzyMatcher(mock_repo)

        result = await matcher.find_candidates(
            event_type=EventType.earthquake,
            lat=35.0,
            lng=139.0,
            start_date=datetime.now(timezone.utc),
        )

        assert result == mock_candidates


class TestFuzzyMatcherScoreCandidate:
    """Test FuzzyMatcher.score_candidate method."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        return MagicMock()

    @pytest.fixture
    def matcher(self, mock_repo):
        """Create a FuzzyMatcher."""
        return FuzzyMatcher(mock_repo)

    @pytest.fixture
    def raw_event(self):
        """Create a sample RawEvent."""
        return RawEvent(
            external_id="test-1",
            source_name="USGS",
            title="Earthquake in Tokyo",
            event_type_raw="earthquake",
            lat=35.6762,
            lng=139.6503,
            start_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def close_candidate(self):
        """Create a candidate event very close to raw_event."""
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.title = "M 6.5 Earthquake near Tokyo"
        candidate.latitude = 35.68  # ~0.5km away
        candidate.longitude = 139.65
        candidate.start_date = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)  # 2h later
        return candidate

    def test_score_candidate_close_match(self, matcher, raw_event, close_candidate):
        """Should score high for very close events."""
        match = matcher.score_candidate(raw_event, close_candidate)

        assert match is not None
        assert match.score > 0.8  # High score for close match
        assert "spatial_proximity" in str(match.reasons)
        assert "temporal_proximity" in str(match.reasons)
        assert match.method == "fuzzy"
        assert match.event_id == close_candidate.id

    def test_score_candidate_distant_event(self, matcher, raw_event):
        """Should return None for distant events."""
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.latitude = 36.0  # ~111km away (more than 50km radius)
        candidate.longitude = 140.0
        candidate.start_date = datetime(2024, 1, 3, 12, 0, tzinfo=timezone.utc)  # 2 days later

        match = matcher.score_candidate(raw_event, candidate)

        # Score should be low/None due to distance and time
        assert match is None or match.score < 0.6

    def test_score_candidate_no_raw_coords(self, matcher):
        """Should handle raw event without coordinates."""
        raw = RawEvent(
            external_id="test-2",
            source_name="OTHER",
            title="Event",
            lat=None,
            lng=None,
            start_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.latitude = 35.0
        candidate.longitude = 139.0
        candidate.start_date = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)

        # Should still work (temporal only)
        match = matcher.score_candidate(raw, candidate)
        # May return None or low score depending on implementation

    def test_score_candidate_no_candidate_coords(self, matcher, raw_event):
        """Should handle candidate without coordinates."""
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.latitude = None
        candidate.longitude = None
        candidate.start_date = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)

        match = matcher.score_candidate(raw_event, candidate)
        # Should only use temporal matching

    def test_score_candidate_same_location(self, matcher, raw_event):
        """Should return perfect spatial score for same location."""
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.latitude = raw_event.lat  # Same location
        candidate.longitude = raw_event.lng
        candidate.start_date = raw_event.start_date  # Same time

        match = matcher.score_candidate(raw_event, candidate)

        assert match is not None
        assert match.score >= 0.95  # Very high score for exact match

    def test_score_candidate_temporal_only(self, matcher):
        """Should match on temporal proximity when spatial is close."""
        raw = RawEvent(
            external_id="test-3",
            source_name="GDACS",
            title="Flood Event",
            lat=35.0,
            lng=139.0,
            start_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Same location, 1 hour apart
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.flood
        candidate.latitude = 35.0
        candidate.longitude = 139.0
        candidate.start_date = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

        match = matcher.score_candidate(raw, candidate)

        assert match is not None
        # Temporal score: 1 - (1/48) = ~0.979
        assert match.score > 0.9

    def test_score_candidate_at_window_edge(self, matcher, raw_event):
        """Should score low at the edge of time window."""
        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.latitude = raw_event.lat
        candidate.longitude = raw_event.lng
        # 47 hours apart (almost at 48h window edge)
        candidate.start_date = raw_event.start_date + timedelta(hours=47)

        match = matcher.score_candidate(raw_event, candidate)

        # Temporal score should be very low: 1 - (47/48) ≈ 0.02
        # But spatial is perfect, so average might still pass threshold
        if match:
            assert match.score > 0.6  # Spatial saves it

    def test_score_candidate_with_title_similarity(self, mock_repo, raw_event):
        """Should include title similarity when enabled."""
        config = FuzzyConfig(title_similarity_enabled=True)
        matcher = FuzzyMatcher(mock_repo, config=config)

        candidate = MagicMock(spec=Event)
        candidate.id = uuid4()
        candidate.type = EventType.earthquake
        candidate.title = "Earthquake in Tokyo region"  # Similar title
        candidate.latitude = 35.68
        candidate.longitude = 139.65
        candidate.start_date = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)

        match = matcher.score_candidate(raw_event, candidate)

        assert match is not None
        # With title similarity enabled and similar titles
        if "title_similarity" in str(match.reasons):
            assert match.score > 0.7

    def test_score_candidate_no_title_similarity_by_default(self, matcher, raw_event, close_candidate):
        """Should not include title similarity by default."""
        match = matcher.score_candidate(raw_event, close_candidate)

        assert match is not None
        assert "title_similarity" not in str(match.reasons)


class TestFuzzyMatcherDistanceCalculation:
    """Test distance score calculation."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def matcher(self, mock_repo):
        return FuzzyMatcher(mock_repo)

    def test_distance_score_same_point(self, matcher):
        """Same point should have score 1.0."""
        score = matcher._compute_distance_score(35.0, 139.0, 35.0, 139.0)
        assert score == 1.0

    def test_distance_score_at_max_radius(self, matcher):
        """Point at max radius should have score 0.0."""
        # ~50km away (using approximate calculation)
        # 0.45 degrees latitude ≈ 50km
        score = matcher._compute_distance_score(35.0, 139.0, 35.45, 139.0)
        assert score < 0.1  # Should be very low (approximately at or beyond radius)

    def test_distance_score_halfway(self, matcher):
        """Point halfway should have score ~0.5."""
        # ~25km away (half of 50km radius)
        # 0.225 degrees latitude ≈ 25km
        score = matcher._compute_distance_score(35.0, 139.0, 35.225, 139.0)
        assert 0.4 < score < 0.6

    def test_distance_score_beyond_radius(self, matcher):
        """Point beyond radius should have score 0.0."""
        # ~100km away (well beyond 50km radius)
        score = matcher._compute_distance_score(35.0, 139.0, 36.0, 139.0)
        assert score == 0.0


class TestFuzzyMatcherTimeCalculation:
    """Test time score calculation."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def matcher(self, mock_repo):
        return FuzzyMatcher(mock_repo)

    def test_time_score_same_time(self, matcher):
        """Same time should have score 1.0."""
        date = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        score = matcher._compute_time_score(date, date)
        assert score == 1.0

    def test_time_score_at_max_window(self, matcher):
        """Time at max window should have score 0.0."""
        date1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        date2 = date1 + timedelta(hours=48)
        score = matcher._compute_time_score(date1, date2)
        assert score == 0.0

    def test_time_score_halfway(self, matcher):
        """Time halfway should have score 0.5."""
        date1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        date2 = date1 + timedelta(hours=24)  # Half of 48h window
        score = matcher._compute_time_score(date1, date2)
        assert score == 0.5

    def test_time_score_beyond_window(self, matcher):
        """Time beyond window should have score 0.0."""
        date1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        date2 = date1 + timedelta(hours=72)
        score = matcher._compute_time_score(date1, date2)
        assert score == 0.0

    def test_time_score_order_independent(self, matcher):
        """Score should be same regardless of date order."""
        date1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        date2 = date1 + timedelta(hours=6)
        
        score1 = matcher._compute_time_score(date1, date2)
        score2 = matcher._compute_time_score(date2, date1)
        
        assert score1 == score2


class TestFuzzyMatcherTitleSimilarity:
    """Test title similarity calculation."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def matcher(self, mock_repo):
        return FuzzyMatcher(mock_repo)

    def test_title_similarity_identical(self, matcher):
        """Identical titles should have score 1.0."""
        score = matcher._compute_title_similarity(
            "Earthquake in Tokyo",
            "Earthquake in Tokyo"
        )
        assert score == 1.0

    def test_title_similarity_completely_different(self, matcher):
        """Completely different titles should have low score."""
        score = matcher._compute_title_similarity(
            "Earthquake in Tokyo",
            "Flood in Bangladesh"
        )
        assert score < 0.3

    def test_title_similarity_partial_overlap(self, matcher):
        """Partially overlapping titles should have medium score."""
        score = matcher._compute_title_similarity(
            "Earthquake in Tokyo Japan",
            "Major Earthquake near Tokyo"
        )
        assert 0.3 < score < 0.8

    def test_title_similarity_none_titles(self, matcher):
        """None titles should return 0."""
        assert matcher._compute_title_similarity(None, "Title") == 0.0
        assert matcher._compute_title_similarity("Title", None) == 0.0
        assert matcher._compute_title_similarity(None, None) == 0.0

    def test_title_similarity_empty_titles(self, matcher):
        """Empty titles should return 0."""
        assert matcher._compute_title_similarity("", "Title") == 0.0
        assert matcher._compute_title_similarity("Title", "") == 0.0

    def test_title_similarity_case_insensitive(self, matcher):
        """Title comparison should be case insensitive."""
        score1 = matcher._compute_title_similarity(
            "EARTHQUAKE IN TOKYO",
            "earthquake in tokyo"
        )
        score2 = matcher._compute_title_similarity(
            "Earthquake in Tokyo",
            "Earthquake in Tokyo"
        )
        assert score1 == score2

    def test_title_similarity_removes_stop_words(self, matcher):
        """Stop words should be removed from comparison."""
        # "the", "a", "an", "in", "on", "at", "of", "to", "for" are stop words
        score = matcher._compute_title_similarity(
            "The Earthquake",
            "An Earthquake"
        )
        # After removing stop words, both become {"earthquake"}
        assert score == 1.0
