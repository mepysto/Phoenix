"""Need/offer matching score."""

from uuid import uuid4

from src.services.community.matching import (
    NeedInput,
    OfferInput,
    clean_categories,
    haversine_km,
    rank_offers,
    score_offer,
)

EVENT = uuid4()


def need(**kw):
    base = dict(categories=frozenset({"water"}), event_id=EVENT, lat=10.0, lng=20.0, quantity=100, unit="kits")
    return NeedInput(**{**base, **kw})


def offer(**kw):
    base = dict(
        id=uuid4(), offer_type="goods", categories=frozenset({"water"}), event_id=EVENT,
        lat=10.1, lng=20.1, quantity=100, unit="Kits",
    )
    return OfferInput(**{**base, **kw})


def test_perfect_match_scores_one():
    m = score_offer(need(), offer())
    assert m is not None
    assert m.score >= 0.99  # ~15 km apart costs a little distance fit
    assert set(m.reasons) == {"category_match", "same_event", "nearby", "covers_all"}


def test_unrelated_category_is_excluded_but_funding_is_not():
    assert score_offer(need(), offer(categories=frozenset({"education"}))) is None
    funding = score_offer(need(), offer(offer_type="funding", categories=frozenset({"cash"})))
    assert funding is not None and "funding_any" in funding.reasons


def test_partial_quantity_and_other_event():
    m = score_offer(need(), offer(quantity=25, event_id=uuid4()))
    assert m is not None
    assert "covers_part" in m.reasons
    assert "same_event" not in m.reasons
    assert m.score < score_offer(need(), offer()).score


def test_units_must_agree_for_quantity():
    m = score_offer(need(), offer(unit="litres"))
    assert m is not None and "covers_all" not in m.reasons


def test_ranking_prefers_closer_then_better():
    near = offer(lat=10.0, lng=20.0)
    far = offer(lat=-30.0, lng=150.0)
    ranked = rank_offers(need(), [far, near])
    assert [m.offer_id for m in ranked] == [near.id, far.id]
    assert ranked[1].distance_km and ranked[1].distance_km > 5000


def test_clean_categories_keeps_known_in_order():
    assert clean_categories(["Water", "shelter", "bogus", "water"]) == ["shelter", "water"]


def test_haversine():
    assert round(haversine_km(0, 0, 0, 1)) == 111
