"""Tests for the beastman gear progression."""
from __future__ import annotations

from server.beastman_gear_progression import (
    BeastmanGearProgression,
    GearSlotCategory,
    GearTier,
)
from server.beastman_playable_races import BeastmanRace


def _seed_yagudo_starter(p: BeastmanGearProgression):
    return p.register_piece(
        piece_id="yag_starter_robe",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="Acolyte Vestment",
        canon_equivalent_item_id="cleric_robe",
    )


def test_register_piece():
    p = BeastmanGearProgression()
    piece = _seed_yagudo_starter(p)
    assert piece is not None
    assert piece.level_gate == 1


def test_register_double_id_rejected():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    res = p.register_piece(
        piece_id="yag_starter_robe",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="x", canon_equivalent_item_id="y",
    )
    assert res is None


def test_register_empty_label_rejected():
    p = BeastmanGearProgression()
    res = p.register_piece(
        piece_id="x",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="",
        canon_equivalent_item_id="y",
    )
    assert res is None


def test_register_empty_canon_eq_rejected():
    p = BeastmanGearProgression()
    res = p.register_piece(
        piece_id="x",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="",
    )
    assert res is None


def test_progression_for_sorts_by_tier():
    p = BeastmanGearProgression()
    p.register_piece(
        piece_id="late",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.RELIC_TIER,
        slot=GearSlotCategory.BODY,
        label="late",
        canon_equivalent_item_id="rl",
    )
    p.register_piece(
        piece_id="early",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="early",
        canon_equivalent_item_id="ce",
    )
    rows = p.progression_for(race=BeastmanRace.YAGUDO)
    assert rows[0].piece_id == "early"
    assert rows[-1].piece_id == "late"


def test_unlock_starter_tier():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    res = p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe",
        player_level=1,
    )
    assert res.accepted


def test_unlock_unknown_piece():
    p = BeastmanGearProgression()
    res = p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="ghost", player_level=99,
    )
    assert not res.accepted
    assert "no such piece" in res.reason


def test_unlock_race_mismatch():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    res = p.unlock(
        player_id="alice", race=BeastmanRace.ORC,
        piece_id="yag_starter_robe",
        player_level=99,
    )
    assert not res.accepted
    assert "race mismatch" in res.reason


def test_unlock_below_level_gate():
    p = BeastmanGearProgression()
    p.register_piece(
        piece_id="exp",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.EXPERT,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.register_piece(
        piece_id="nov",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.NOVICE,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.register_piece(
        piece_id="jou",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.JOURNEYMAN,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.register_piece(
        piece_id="sta",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="sta", player_level=99,
    )
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="nov", player_level=99,
    )
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="jou", player_level=99,
    )
    res = p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="exp", player_level=10,
    )
    assert not res.accepted
    assert "level <" in res.reason


def test_unlock_skipping_tier_rejected():
    p = BeastmanGearProgression()
    p.register_piece(
        piece_id="sta",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.register_piece(
        piece_id="exp",
        race=BeastmanRace.YAGUDO,
        tier=GearTier.EXPERT,
        slot=GearSlotCategory.BODY,
        label="x",
        canon_equivalent_item_id="y",
    )
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="sta", player_level=99,
    )
    res = p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="exp", player_level=99,
    )
    assert not res.accepted
    assert "prior tier" in res.reason


def test_unlock_already_unlocked_rejected():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe",
        player_level=1,
    )
    res = p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe",
        player_level=1,
    )
    assert not res.accepted


def test_unlocked_for_player():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe",
        player_level=1,
    )
    unlocked = p.unlocked_for(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert "yag_starter_robe" in unlocked


def test_next_tier_for_new_player():
    p = BeastmanGearProgression()
    nt = p.next_tier_for_player(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert nt == GearTier.STARTER


def test_next_tier_after_unlock():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe",
        player_level=1,
    )
    nt = p.next_tier_for_player(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert nt == GearTier.NOVICE


def test_next_tier_at_top_returns_none():
    p = BeastmanGearProgression()
    # Register all tiers in one slot
    tiers_in_order = list(GearTier)
    prev_id = None
    for i, t in enumerate(tiers_in_order):
        pid = f"piece_{i}"
        p.register_piece(
            piece_id=pid,
            race=BeastmanRace.YAGUDO,
            tier=t,
            slot=GearSlotCategory.BODY,
            label="x",
            canon_equivalent_item_id="y",
        )
        p.unlock(
            player_id="alice",
            race=BeastmanRace.YAGUDO,
            piece_id=pid, player_level=999,
        )
        prev_id = pid
    nt = p.next_tier_for_player(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert nt is None


def test_per_race_isolation():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    p.register_piece(
        piece_id="orc_starter",
        race=BeastmanRace.ORC,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.WEAPON,
        label="Iron Cleaver",
        canon_equivalent_item_id="iron_cleaver",
    )
    p.unlock(
        player_id="alice", race=BeastmanRace.YAGUDO,
        piece_id="yag_starter_robe", player_level=1,
    )
    nt_orc = p.next_tier_for_player(
        player_id="alice", race=BeastmanRace.ORC,
    )
    assert nt_orc == GearTier.STARTER


def test_canon_equivalent_propagates():
    p = BeastmanGearProgression()
    piece = _seed_yagudo_starter(p)
    assert piece.canon_equivalent_item_id == "cleric_robe"


def test_total_pieces():
    p = BeastmanGearProgression()
    _seed_yagudo_starter(p)
    p.register_piece(
        piece_id="orc_starter",
        race=BeastmanRace.ORC,
        tier=GearTier.STARTER,
        slot=GearSlotCategory.WEAPON,
        label="x",
        canon_equivalent_item_id="y",
    )
    assert p.total_pieces() == 2
