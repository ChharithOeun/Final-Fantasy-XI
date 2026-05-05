"""Tests for drowned pact ritual."""
from __future__ import annotations

from server.drowned_pact_ritual import (
    DarkAbility,
    DrownedPactRitual,
    RitualStage,
)


def test_begin_happy():
    r = DrownedPactRitual()
    res = r.begin(
        player_id="p", has_pledge=True, now_seconds=0,
    )
    assert res.accepted is True
    assert res.new_stage == RitualStage.IMMERSION


def test_begin_no_pledge():
    r = DrownedPactRitual()
    res = r.begin(
        player_id="p", has_pledge=False, now_seconds=0,
    )
    assert res.accepted is False
    assert res.reason == "no pledge"


def test_begin_blank_player():
    r = DrownedPactRitual()
    res = r.begin(
        player_id="", has_pledge=True, now_seconds=0,
    )
    assert res.accepted is False


def test_begin_blocks_in_progress():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    res = r.begin(player_id="p", has_pledge=True, now_seconds=10)
    assert res.accepted is False
    assert res.reason == "ritual in progress"


def test_full_chain_grants_abilities():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=10)   # CONFESSION
    r.advance(player_id="p", now_seconds=20)   # DROWNING
    res = r.advance(player_id="p", now_seconds=30)  # PERFORMED
    assert res.new_stage == RitualStage.PERFORMED
    assert DarkAbility.ABYSS_BREATH in res.abilities_granted
    assert DarkAbility.KRAKEN_HUNGER in res.abilities_granted
    assert DarkAbility.TIDAL_STRIDE in res.abilities_granted


def test_has_ability_after_performed():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=10)
    r.advance(player_id="p", now_seconds=20)
    r.advance(player_id="p", now_seconds=30)
    assert r.has_ability(
        player_id="p", ability=DarkAbility.ABYSS_BREATH,
    ) is True


def test_advance_without_begin():
    r = DrownedPactRitual()
    res = r.advance(player_id="p", now_seconds=0)
    assert res.accepted is False


def test_corruption_climbs_on_advance():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    # IMMERSION -> CONFESSION; gain from IMMERSION step (0)
    s1 = r.advance(player_id="p", now_seconds=1)
    # CONFESSION -> DROWNING; gain from CONFESSION step (5)
    s2 = r.advance(player_id="p", now_seconds=2)
    # DROWNING -> PERFORMED; gain from DROWNING step (10)
    s3 = r.advance(player_id="p", now_seconds=3)
    assert s1.corruption_gained == 0
    assert s2.corruption_gained == 5
    assert s3.corruption_gained == 10


def test_abort_at_immersion():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    res = r.abort(player_id="p", now_seconds=10)
    assert res.accepted is True
    assert res.new_stage == RitualStage.ABORTED
    assert res.corruption_refund == 15


def test_abort_at_confession():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=1)
    res = r.abort(player_id="p", now_seconds=10)
    assert res.accepted is True


def test_abort_at_drowning_blocked():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=1)
    r.advance(player_id="p", now_seconds=2)
    res = r.abort(player_id="p", now_seconds=10)
    assert res.accepted is False
    assert res.reason == "too late to abort"


def test_abort_after_performed_blocked():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=1)
    r.advance(player_id="p", now_seconds=2)
    r.advance(player_id="p", now_seconds=3)  # PERFORMED
    res = r.abort(player_id="p", now_seconds=10)
    assert res.accepted is False


def test_begin_after_performed_blocked():
    r = DrownedPactRitual()
    r.begin(player_id="p", has_pledge=True, now_seconds=0)
    r.advance(player_id="p", now_seconds=1)
    r.advance(player_id="p", now_seconds=2)
    r.advance(player_id="p", now_seconds=3)
    res = r.begin(
        player_id="p", has_pledge=True, now_seconds=100,
    )
    assert res.accepted is False
    assert res.reason == "already performed"


def test_has_ability_default_false():
    r = DrownedPactRitual()
    assert r.has_ability(
        player_id="p", ability=DarkAbility.ABYSS_BREATH,
    ) is False
