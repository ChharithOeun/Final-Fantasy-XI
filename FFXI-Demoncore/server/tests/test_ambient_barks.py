"""Tests for ambient bark catalog + selector."""
from __future__ import annotations

import random

from server.ambient_barks import (
    Bark,
    BarkCatalog,
    BarkSelector,
    BarkSituation,
    seed_default_catalog,
)
from server.faction_reputation import ReputationBand


def _seeded() -> BarkCatalog:
    return seed_default_catalog(BarkCatalog())


def test_catalog_seeds_meaningful_count():
    cat = _seeded()
    assert cat.total() >= 20


def test_bark_matches_situation():
    cat = _seeded()
    greets = cat.all_for_situation(BarkSituation.GREETING)
    assert len(greets) >= 4
    for b in greets:
        assert b.situation == BarkSituation.GREETING


def test_bark_matches_rep_band_filter():
    b = Bark(
        bark_id="hero_only", line="my lord!",
        situation=BarkSituation.GREETING,
        rep_bands=frozenset({
            ReputationBand.HERO_OF_THE_FACTION,
        }),
    )
    assert b.matches(
        situation=BarkSituation.GREETING,
        rep_band=ReputationBand.HERO_OF_THE_FACTION,
    )
    assert not b.matches(
        situation=BarkSituation.GREETING,
        rep_band=ReputationBand.NEUTRAL,
    )


def test_bark_matches_personality_tag():
    b = Bark(
        bark_id="berserker_only", line="GRRR",
        situation=BarkSituation.AGGRO_OPEN,
        personality_tags=frozenset({"berserker"}),
    )
    assert b.matches(
        situation=BarkSituation.AGGRO_OPEN,
        personality_tags=("berserker", "brawler"),
    )
    assert not b.matches(
        situation=BarkSituation.AGGRO_OPEN,
        personality_tags=("coward",),
    )


def test_bark_matches_hour_filter():
    b = Bark(
        bark_id="dawn", line="Hail morn",
        situation=BarkSituation.DAWN_PRAYER,
        hours=frozenset({5, 6}),
    )
    assert b.matches(
        situation=BarkSituation.DAWN_PRAYER, hour=5,
    )
    assert not b.matches(
        situation=BarkSituation.DAWN_PRAYER, hour=14,
    )


def test_bark_no_filter_matches_anything():
    b = Bark(
        bark_id="generic_idle", line="...",
        situation=BarkSituation.IDLE_MUTTER,
    )
    assert b.matches(situation=BarkSituation.IDLE_MUTTER)
    assert b.matches(
        situation=BarkSituation.IDLE_MUTTER,
        rep_band=ReputationBand.NEUTRAL,
        personality_tags=("anything",),
        hour=12,
    )


def test_selector_returns_none_for_unmatched_situation():
    cat = BarkCatalog()
    sel = BarkSelector(catalog=cat)
    res = sel.pick(situation=BarkSituation.GREETING)
    assert res is None


def test_selector_picks_neutral_greeting():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(1)
    bark = sel.pick(
        situation=BarkSituation.GREETING,
        rep_band=ReputationBand.NEUTRAL, rng=rng,
    )
    assert bark is not None
    assert bark.situation == BarkSituation.GREETING


def test_selector_prefers_hero_specific_for_hero_player():
    """Hero-specific barks are picked over the generic one when
    the player has the right rep band."""
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    # Run the picker many times — the hero-tagged one should
    # appear at least once
    rng = random.Random(7)
    seen = set()
    for _ in range(50):
        bark = sel.pick(
            situation=BarkSituation.GREETING,
            rep_band=ReputationBand.HERO_OF_THE_FACTION,
            rng=rng,
        )
        if bark is not None:
            seen.add(bark.bark_id)
    assert "greet_hero" in seen


def test_selector_filters_out_wrong_band_specific():
    """A hero-only bark should NEVER pick when the player is
    NEUTRAL."""
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(2)
    seen = set()
    for _ in range(50):
        bark = sel.pick(
            situation=BarkSituation.GREETING,
            rep_band=ReputationBand.NEUTRAL, rng=rng,
        )
        if bark is not None:
            seen.add(bark.bark_id)
    assert "greet_hero" not in seen


def test_selector_personality_tag_matching():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(3)
    seen = set()
    for _ in range(50):
        bark = sel.pick(
            situation=BarkSituation.AGGRO_OPEN,
            personality_tags=("berserker",), rng=rng,
        )
        if bark is not None:
            seen.add(bark.bark_id)
    assert "aggro_berserker" in seen


def test_selector_hour_filtering_dawn():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(4)
    bark = sel.pick(
        situation=BarkSituation.DAWN_PRAYER, hour=5, rng=rng,
    )
    assert bark is not None
    assert bark.bark_id == "dawn_prayer"


def test_selector_returns_none_when_hour_doesnt_match():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(5)
    bark = sel.pick(
        situation=BarkSituation.DAWN_PRAYER, hour=23, rng=rng,
    )
    assert bark is None


def test_shop_hawk_morning_vs_afternoon():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    morning = sel.pick(
        situation=BarkSituation.SHOP_HAWK, hour=9,
        rng=random.Random(0),
    )
    afternoon = sel.pick(
        situation=BarkSituation.SHOP_HAWK, hour=17,
        rng=random.Random(0),
    )
    assert morning is not None and afternoon is not None
    assert morning.bark_id != afternoon.bark_id


def test_patrol_halt_outlaw_specific():
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(6)
    seen = set()
    for _ in range(30):
        bark = sel.pick(
            situation=BarkSituation.PATROL_HALT,
            rep_band=ReputationBand.KILL_ON_SIGHT, rng=rng,
        )
        if bark is not None:
            seen.add(bark.bark_id)
    assert "halt_outlaw" in seen


def test_seeded_catalog_sanity():
    cat = _seeded()
    # Coverage: at least one bark per major situation
    for sit in (
        BarkSituation.GREETING,
        BarkSituation.AGGRO_OPEN,
        BarkSituation.LOW_HP,
        BarkSituation.FLEEING,
        BarkSituation.SHOP_HAWK,
        BarkSituation.PATROL_HALT,
        BarkSituation.MOURNING,
        BarkSituation.DAWN_PRAYER,
        BarkSituation.DUSK_LAMENT,
        BarkSituation.KILL_CONFIRMED,
        BarkSituation.WARNING_BEASTMEN,
        BarkSituation.IDLE_MUTTER,
    ):
        assert len(cat.all_for_situation(sit)) >= 1


def test_full_lifecycle_goblin_aggro_to_low_hp():
    """A goblin (schemer) aggros, drops to low hp, flees."""
    cat = _seeded()
    sel = BarkSelector(catalog=cat)
    rng = random.Random(11)
    aggro = sel.pick(
        situation=BarkSituation.AGGRO_OPEN,
        personality_tags=("schemer",), rng=rng,
    )
    low = sel.pick(
        situation=BarkSituation.LOW_HP,
        personality_tags=("schemer",), rng=rng,
    )
    flee = sel.pick(
        situation=BarkSituation.FLEEING,
        personality_tags=("schemer",), rng=rng,
    )
    # All three slots fill — even if generic fallback
    assert aggro is not None
    assert low is not None
    assert flee is not None
