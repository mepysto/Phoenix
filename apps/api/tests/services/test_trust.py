"""Event confidence and lifecycle stage."""

from datetime import UTC, datetime, timedelta

from src.utils.trust import compute_trust

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def trust(sources, *, active=True, age=timedelta(hours=1), end=None, seen=None):
    start = NOW - age
    return compute_trust(
        source_names=sources,
        is_active=active,
        start_date=start,
        end_date=end,
        updated_at=seen if seen is not None else NOW,
        now=NOW,
    )


def test_more_independent_sources_raise_confidence():
    one = trust(["USGS"])
    two = trust(["USGS", "GDACS"])
    assert one.confidence == 0.6
    assert two.confidence == 0.75
    assert two.source_count == 2
    assert "multi_source" in two.reasons


def test_same_source_twice_counts_once():
    assert trust(["USGS", "usgs ", ""]).source_count == 1


def test_confidence_is_capped():
    assert trust(["USGS", "GDACS", "Copernicus", "EONET", "ReliefWeb"]).confidence == 1.0


def test_unknown_single_source_is_only_detected_at_first():
    t = trust(["Some Feed"], age=timedelta(hours=2))
    assert t.confidence == 0.4
    assert t.lifecycle == "detected"


def test_authoritative_single_source_is_verified():
    assert trust(["GDACS"], age=timedelta(hours=2)).lifecycle == "verified"


def test_stages_follow_age():
    assert trust(["USGS"], age=timedelta(days=3)).lifecycle == "responding"
    assert trust(["USGS"], age=timedelta(days=30)).lifecycle == "recovering"


def test_inactive_or_ended_is_closed():
    assert trust(["USGS"], active=False).lifecycle == "closed"
    assert trust(["USGS"], end=NOW - timedelta(hours=1)).lifecycle == "closed"
    # An end date in the future does not close the event yet
    assert trust(["USGS"], end=NOW + timedelta(days=1)).lifecycle == "verified"


def test_active_event_unconfirmed_for_days_loses_confidence():
    stale = trust(["USGS"], age=timedelta(days=5), seen=NOW - timedelta(days=4))
    assert stale.confidence < 0.6
    assert "stale" in stale.reasons
    # Never more than the cap, and never below the floor
    very = trust(["Feed"], age=timedelta(days=90), seen=NOW - timedelta(days=80))
    assert very.confidence >= 0.1


def test_no_sources():
    t = trust([])
    assert t.source_count == 0
    assert t.confidence == 0.3
    assert "no_source" in t.reasons
