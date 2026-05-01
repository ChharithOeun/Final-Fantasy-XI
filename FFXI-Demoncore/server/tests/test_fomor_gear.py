"""Tests for fomor gear progression: tier scaling + drop engine +
spawn pool + lineage + loss conditions.

Run:  python -m pytest server/tests/test_fomor_gear.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from fomor_gear import (
    BASE_DROP_RATE,
    DAILY_DROP_LIMIT,
    DropEngine,
    DropResult,
    EligibilityChecker,
    FomorSpawnCooldownTracker,
    FomorWardrobe,
    GearPiece,
    GearRequirements,
    GearTemplate,
    GearTier,
    HolderType,
    KillerSnapshot,
    LineageEvent,
    PER_FOMOR_COOLDOWN_SECONDS,
    SESSION_DR_RATES,
    SpawnPool,
    ZONE_LEVEL_BANDS,
    scaled_stats,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

def _hauberk_template() -> GearTemplate:
    return GearTemplate(
        base_id="hauberk",
        name="Hauberk",
        base_stats={"defense": 80, "hp": 35, "vit": 6},
        requirements=GearRequirements(min_level=60, job="WAR"),
    )


def _cobra_tunic_template() -> GearTemplate:
    return GearTemplate(
        base_id="cobra_tunic",
        name="Cobra Tunic",
        base_stats={"defense": 50, "str": 5, "attack": 8},
        requirements=GearRequirements(min_level=55, job="WAR"),
    )


def _crayon_template() -> GearTemplate:
    return GearTemplate(
        base_id="crayon",
        name="Crayon",
        base_stats={"int": 1},
        requirements=GearRequirements(min_level=1),
    )


def _make_piece(template: GearTemplate, gear_id: str = "g_001",
                 tier: GearTier = GearTier.VANILLA) -> GearPiece:
    return GearPiece(gear_id=gear_id, template=template, tier=tier)


def _alice_war(level: int = 75) -> KillerSnapshot:
    return KillerSnapshot(
        killer_id="alice", level=level, job="WAR",
        race="hume",
    )


# ----------------------------------------------------------------------
# Tier scaling
# ----------------------------------------------------------------------

def test_vanilla_stats_unmodified():
    p = _make_piece(_hauberk_template())
    s = scaled_stats(p)
    assert s["defense"] == 80
    assert s["hp"] == 35


def test_purple_iii_lifts_15_percent():
    p = _make_piece(_hauberk_template(), tier=GearTier.PURPLE_III)
    s = scaled_stats(p)
    assert s["defense"] == pytest.approx(80 * 1.15)
    assert s["hp"] == pytest.approx(35 * 1.15)
    assert s["vit"] == pytest.approx(6 * 1.15)


def test_purple_v_caps_at_25_percent():
    p = _make_piece(_hauberk_template(), tier=GearTier.PURPLE_V)
    s = scaled_stats(p)
    assert s["defense"] == pytest.approx(80 * 1.25)


def test_tier_label():
    assert GearTier.VANILLA.label() == ""
    assert GearTier.PURPLE_I.label() == "+I"
    assert GearTier.PURPLE_III.label() == "+III"
    assert GearTier.PURPLE_V.label() == "+V"


def test_next_tier_at_cap_stays_at_cap():
    p = _make_piece(_hauberk_template(), tier=GearTier.PURPLE_V)
    assert p.is_at_cap() is True
    assert p.next_tier() == GearTier.PURPLE_V


def test_next_tier_escalates():
    p = _make_piece(_hauberk_template(), tier=GearTier.PURPLE_II)
    assert p.next_tier() == GearTier.PURPLE_III


# ----------------------------------------------------------------------
# Eligibility
# ----------------------------------------------------------------------

def test_eligibility_accepts_war():
    p = _make_piece(_hauberk_template())
    alice = _alice_war(level=70)
    assert EligibilityChecker.can_equip(p, alice) is True


def test_eligibility_rejects_low_level():
    p = _make_piece(_hauberk_template())   # min_level 60
    alice = _alice_war(level=30)
    assert EligibilityChecker.can_equip(p, alice) is False


def test_eligibility_rejects_wrong_job():
    p = _make_piece(_hauberk_template())   # WAR
    bob = KillerSnapshot(killer_id="bob", level=70, job="BLM")
    assert EligibilityChecker.can_equip(p, bob) is False


def test_eligibility_accepts_via_subjob():
    """A WAR/MNK can equip a MNK piece via subjob."""
    template = GearTemplate(
        base_id="cyclas",
        name="Cyclas",
        base_stats={"defense": 30, "vit": 3},
        requirements=GearRequirements(min_level=20, job="MNK"),
    )
    p = _make_piece(template)
    war_mnk = KillerSnapshot(killer_id="x", level=40, job="WAR", sub_job="MNK")
    assert EligibilityChecker.can_equip(p, war_mnk) is True


# ----------------------------------------------------------------------
# Drop engine — basic
# ----------------------------------------------------------------------

def _always_succeed_engine() -> DropEngine:
    """Engine whose RNG always rolls 0.0 — every roll succeeds."""
    rng = random.Random()
    rng.random = lambda: 0.0   # type: ignore[assignment]
    return DropEngine(rng=rng)


def _always_fail_engine() -> DropEngine:
    rng = random.Random()
    rng.random = lambda: 0.99   # type: ignore[assignment]
    return DropEngine(rng=rng)


def test_successful_drop_escalates_tier_and_hands_to_killer():
    piece = _make_piece(_cobra_tunic_template(), gear_id="ct1",
                          tier=GearTier.VANILLA)
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    engine = _always_succeed_engine()

    result = engine.attempt_drops(
        killer=alice, fomor=fomor, fomor_spawn_id="sp_1", now=100,
    )
    assert len(result.pieces_dropped) == 1
    assert result.pieces_dropped[0].tier == GearTier.PURPLE_I
    assert result.pieces_dropped[0].current_holder == "alice"
    assert result.pieces_dropped[0].current_holder_type == HolderType.PLAYER
    assert piece not in fomor.pieces


def test_dropped_piece_records_lineage():
    piece = _make_piece(_cobra_tunic_template(), gear_id="ct1")
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    engine = _always_succeed_engine()

    engine.attempt_drops(killer=alice, fomor=fomor,
                          fomor_spawn_id="sp_1", now=100)
    assert len(piece.lineage_history) == 1
    event = piece.lineage_history[0]
    assert event.holder_id == "alice"
    assert event.event == "looted_from_fomor"


def test_failed_roll_returns_piece_to_world():
    """Per the doc: when the recursion roll misses, the piece returns
    from the fomor's wardrobe to the live world."""
    piece = _make_piece(_cobra_tunic_template(), gear_id="ct1")
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    engine = _always_fail_engine()

    result = engine.attempt_drops(killer=alice, fomor=fomor,
                                    fomor_spawn_id="sp_1", now=100)
    assert len(result.pieces_dropped) == 0
    assert len(result.pieces_failed_roll) == 1
    assert piece not in fomor.pieces
    # Lineage records the return-to-world
    assert any(e.event == "returned_to_world"
                 for e in piece.lineage_history)


def test_ineligible_pieces_skipped_not_failed():
    """Low-level killer of high-level fomor: their pieces aren't rolled,
    just skipped. They're still in the fomor's wardrobe afterward."""
    relic = _make_piece(_hauberk_template(), gear_id="h1")
    crayon = _make_piece(_crayon_template(), gear_id="c1")
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=90,
                           pieces=[relic, crayon])
    bob = KillerSnapshot(killer_id="bob", level=10, job="WAR")
    engine = _always_succeed_engine()

    result = engine.attempt_drops(killer=bob, fomor=fomor,
                                    fomor_spawn_id="sp_1", now=100)
    # Crayon is droppable; Hauberk requires lvl 60 → ineligible
    assert relic in result.pieces_skipped_ineligible
    assert relic in fomor.pieces        # still in wardrobe
    assert crayon in result.pieces_dropped
    assert crayon not in fomor.pieces


def test_per_piece_independent_rolls():
    """6 pieces, all eligible, RNG rolls 0 -> all 6 should drop."""
    pieces = [_make_piece(_crayon_template(), gear_id=f"p{i}")
                for i in range(6)]
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=20, pieces=list(pieces))
    alice = _alice_war(level=20)
    engine = _always_succeed_engine()

    result = engine.attempt_drops(killer=alice, fomor=fomor,
                                    fomor_spawn_id="sp_1", now=100)
    # Killed at the daily limit (3) — only 3 of 6 dropped before stop
    assert len(result.pieces_dropped) == DAILY_DROP_LIMIT
    # Remaining pieces stay in wardrobe (weren't rolled)
    assert len(fomor.pieces) == 6 - DAILY_DROP_LIMIT


# ----------------------------------------------------------------------
# Drop engine — anti-farming
# ----------------------------------------------------------------------

def test_daily_limit_blocks_further_drops_in_same_day():
    """After 3 successful drops, a 4th fomor kill yields no drops."""
    alice = _alice_war(level=60)
    alice.successful_drops_history = [10, 20, 30]   # 3 drops today
    piece = _make_piece(_cobra_tunic_template())
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    engine = _always_succeed_engine()

    result = engine.attempt_drops(killer=alice, fomor=fomor,
                                    fomor_spawn_id="sp_2", now=100)
    assert result.daily_limit_hit is True
    assert len(result.pieces_dropped) == 0
    assert piece in fomor.pieces   # nothing rolled


def test_daily_limit_resets_after_24h():
    """Old drop history (24+ hrs ago) doesn't count toward the limit."""
    alice = _alice_war(level=60)
    alice.successful_drops_history = [10, 20, 30]   # ancient
    piece = _make_piece(_cobra_tunic_template())
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    engine = _always_succeed_engine()

    # 25 hrs later — old history pruned
    result = engine.attempt_drops(killer=alice, fomor=fomor,
                                    fomor_spawn_id="sp_3", now=25 * 3600)
    assert result.daily_limit_hit is False
    assert len(result.pieces_dropped) == 1


def test_session_diminishing_returns():
    """First drop at 3%, second at 2%, third at 1.5%, ..."""
    assert _next_session_rate(0) == pytest.approx(0.030)
    assert _next_session_rate(1) == pytest.approx(0.020)
    assert _next_session_rate(2) == pytest.approx(0.015)
    assert _next_session_rate(3) == pytest.approx(0.010)
    assert _next_session_rate(4) == pytest.approx(0.005)
    assert _next_session_rate(5) == pytest.approx(0.0025)
    # Beyond table: stays at the floor
    assert _next_session_rate(20) == pytest.approx(0.0025)


def _next_session_rate(n: int) -> float:
    from fomor_gear.drop_engine import _session_rate
    return _session_rate(n)


def test_session_logout_resets_dr_counter():
    alice = _alice_war(level=60)
    alice.session_drop_count = 5
    DropEngine.notify_session_logout(alice)
    assert alice.session_drop_count == 0


# ----------------------------------------------------------------------
# Per-fomor cooldown
# ----------------------------------------------------------------------

def test_spawn_cooldown_blocks_drops_after_kill():
    """Killing fomor at sp_1 places that point on 1hr cooldown.
    A second kill at sp_1 within 1hr produces no drops."""
    cd = FomorSpawnCooldownTracker()
    cd.record_kill("sp_1", now=0)
    assert cd.is_on_cooldown("sp_1", now=1800) is True
    assert cd.is_on_cooldown("sp_1", now=PER_FOMOR_COOLDOWN_SECONDS + 1) is False


def test_drop_engine_blocks_during_cooldown():
    cd = FomorSpawnCooldownTracker()
    cd.record_kill("sp_1", now=0)
    rng = random.Random()
    rng.random = lambda: 0.0   # type: ignore
    engine = DropEngine(rng=rng, cooldown_tracker=cd)

    piece = _make_piece(_cobra_tunic_template())
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    result = engine.attempt_drops(killer=alice, fomor=fomor,
                                    fomor_spawn_id="sp_1", now=300)
    assert result.fomor_on_cooldown is True
    assert len(result.pieces_dropped) == 0


# ----------------------------------------------------------------------
# Loss conditions
# ----------------------------------------------------------------------

def test_fomor_vs_fomor_destroys_all_gear():
    p1 = _make_piece(_cobra_tunic_template(), gear_id="ct1")
    p2 = _make_piece(_hauberk_template(), gear_id="h1")
    fomor = FomorWardrobe(fomor_id="victim", fomor_level=60,
                            pieces=[p1, p2])

    destroyed = fomor.destroy_all(now=200, killer_fomor_id="killer_fomor")
    assert len(destroyed) == 2
    assert fomor.pieces == []
    for p in destroyed:
        assert p.current_holder_type == HolderType.DESTROYED
        assert any(e.event == "destroyed_fomor_vs_fomor"
                     for e in p.lineage_history)


# ----------------------------------------------------------------------
# Spawn pool
# ----------------------------------------------------------------------

def test_zones_for_fresh_fomor_match_band_only():
    pool = SpawnPool()
    zones = pool.zones_for_level(35)
    # Should hit the 25-42 + 35-55 bands
    assert "pashhow_marshlands" in zones
    assert "crawlers_nest" in zones
    # Should NOT hit starter or apex
    assert "ronfaure_east" not in zones
    assert "sky_ruaun" not in zones


def test_leveled_up_fomor_unlocks_lower_bands():
    pool = SpawnPool()
    zones = pool.zones_for_level(50, leveled_up=True)
    # leveled-up fomor at lvl 50 can spawn anywhere whose min ≤ 50
    assert "ronfaure_east" in zones
    assert "pashhow_marshlands" in zones
    assert "crawlers_nest" in zones
    # 65+ bands not unlocked yet
    assert "castle_zvahl_baileys" not in zones
    assert "sky_ruaun" not in zones


def test_apex_zones_only_for_high_level():
    pool = SpawnPool()
    zones_low = pool.zones_for_level(30)
    assert "sky_ruaun" not in zones_low
    zones_high = pool.zones_for_level(99, leveled_up=True)
    assert "sky_ruaun" in zones_high
    assert "dynamis_jeuno" in zones_high


def test_zone_eligibility():
    pool = SpawnPool()
    assert pool.is_zone_eligible("pashhow_marshlands", 30) is True
    assert pool.is_zone_eligible("pashhow_marshlands", 50) is False
    assert pool.is_zone_eligible("pashhow_marshlands", 50,
                                   leveled_up=True) is True
    assert pool.is_zone_eligible("nonexistent_zone", 30) is False


# ----------------------------------------------------------------------
# Lineage chain across full recursion
# ----------------------------------------------------------------------

def test_full_recursion_builds_history():
    """Vanilla -> +I -> +II via two consecutive fomor-kill events.
    Exercise: lineage records both jumps."""
    piece = _make_piece(_cobra_tunic_template(), gear_id="ct1",
                          tier=GearTier.VANILLA)

    # First fomor wears it
    f1 = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    engine = _always_succeed_engine()
    engine.attempt_drops(killer=alice, fomor=f1,
                          fomor_spawn_id="sp_1", now=100)
    assert piece.tier == GearTier.PURPLE_I

    # alice dies, becomes fomor wearing the +I piece
    f2 = FomorWardrobe(fomor_id="f_alice", fomor_level=60, pieces=[piece])
    bob = KillerSnapshot(killer_id="bob", level=60, job="WAR")
    engine2 = _always_succeed_engine()
    engine2.attempt_drops(killer=bob, fomor=f2,
                            fomor_spawn_id="sp_2", now=200)
    assert piece.tier == GearTier.PURPLE_II
    assert piece.current_holder == "bob"

    # Lineage shows both events
    events = [e.event for e in piece.lineage_history]
    assert events.count("looted_from_fomor") == 2


def test_recursion_caps_at_v():
    """A piece already at +V stays at +V on subsequent drops."""
    piece = _make_piece(_cobra_tunic_template(), gear_id="ct1",
                          tier=GearTier.PURPLE_V)
    fomor = FomorWardrobe(fomor_id="f1", fomor_level=60, pieces=[piece])
    alice = _alice_war(level=60)
    engine = _always_succeed_engine()
    engine.attempt_drops(killer=alice, fomor=fomor,
                          fomor_spawn_id="sp_1", now=100)
    assert piece.tier == GearTier.PURPLE_V
