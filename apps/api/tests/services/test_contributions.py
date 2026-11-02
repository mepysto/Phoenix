"""Contribution points and badges."""

from src.services.community.contributions import BADGES, score


def test_nothing_done_earns_nothing():
    c = score({})
    assert c.points == 0
    assert not any(b.earned for b in c.badges)
    assert len(c.badges) == len(BADGES)


def test_points_and_badges_follow_counts():
    c = score({"offers": 2, "connections": 1, "plans_public": 1, "forks_received": 4})
    assert c.points == 2 * 1 + 5 + 3 + 4 * 2
    earned = {b.id for b in c.badges if b.earned}
    assert earned == {"first_offer", "connector", "planner", "remixed"}
    steady = next(b for b in c.badges if b.id == "steady_connector")
    assert (steady.progress, steady.target, steady.earned) == (1, 5, False)


def test_progress_is_capped_at_target():
    remixed = next(b for b in score({"forks_received": 40}).badges if b.id == "remixed")
    assert remixed.progress == remixed.target == 3
