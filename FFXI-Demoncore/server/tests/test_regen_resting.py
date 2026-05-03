"""Tests for regen_resting."""
from __future__ import annotations

from server.regen_resting import (
    PER_TICK_CAP,
    RAMP_DURATION_SECONDS,
    TEMPO_MULTIPLIER,
    TICK_INTERVAL_SECONDS,
    RestingState,
    ZoneModifier,
)


def test_default_not_resting():
    s = RestingState(actor_id="alice", level=30)
    assert not s.is_resting


def test_start_resting():
    s = RestingState(actor_id="alice", level=30)
    assert s.start_resting(now_tick=1000)
    assert s.is_resting


def test_double_start_returns_false():
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=1000)
    assert not s.start_resting(now_tick=1100)


def test_stop_resting():
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=1000)
    assert s.stop_resting()
    assert not s.is_resting


def test_compute_tick_when_not_resting_returns_status_only():
    s = RestingState(actor_id="alice", level=30)
    hp, mp = s.compute_tick(
        now_tick=0,
        regen_status_bonus=5,
        refresh_status_bonus=2,
    )
    # Not resting -> only the status bonuses tick
    assert hp == 5
    assert mp == 2


def test_compute_tick_resting_baseline():
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=1000)
    hp, mp = s.compute_tick(
        now_tick=1000 + RAMP_DURATION_SECONDS,
    )
    assert hp > 0
    assert mp > 0


def test_compute_tick_ramps_up():
    s_early = RestingState(actor_id="alice", level=30)
    s_early.start_resting(now_tick=1000)
    early_hp, _ = s_early.compute_tick(now_tick=1001)

    s_late = RestingState(actor_id="alice", level=30)
    s_late.start_resting(now_tick=1000)
    late_hp, _ = s_late.compute_tick(
        now_tick=1000 + RAMP_DURATION_SECONDS,
    )
    assert late_hp >= early_hp


def test_zone_city_heals_faster():
    s_city = RestingState(actor_id="alice", level=30)
    s_city.start_resting(now_tick=1000)
    s_wild = RestingState(actor_id="bob", level=30)
    s_wild.start_resting(now_tick=1000)
    city_hp, _ = s_city.compute_tick(
        now_tick=1100, zone=ZoneModifier.CITY,
    )
    wild_hp, _ = s_wild.compute_tick(
        now_tick=1100, zone=ZoneModifier.WILDERNESS,
    )
    assert city_hp > wild_hp


def test_dungeon_heals_slower():
    s_d = RestingState(actor_id="alice", level=30)
    s_d.start_resting(now_tick=1000)
    s_w = RestingState(actor_id="bob", level=30)
    s_w.start_resting(now_tick=1000)
    d_hp, _ = s_d.compute_tick(
        now_tick=1100, zone=ZoneModifier.DUNGEON,
    )
    w_hp, _ = s_w.compute_tick(
        now_tick=1100, zone=ZoneModifier.WILDERNESS,
    )
    assert d_hp < w_hp


def test_food_bonus_applies():
    s_no = RestingState(actor_id="alice", level=30)
    s_no.start_resting(now_tick=1000)
    s_yes = RestingState(actor_id="bob", level=30)
    s_yes.start_resting(now_tick=1000)
    no_hp, _ = s_no.compute_tick(
        now_tick=1100, food_bonus_pct=0,
    )
    yes_hp, _ = s_yes.compute_tick(
        now_tick=1100, food_bonus_pct=50,
    )
    assert yes_hp > no_hp


def test_regen_status_adds_to_hp():
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=1000)
    no_buff_hp, _ = s.compute_tick(now_tick=1100)
    s2 = RestingState(actor_id="bob", level=30)
    s2.start_resting(now_tick=1000)
    buffed_hp, _ = s2.compute_tick(
        now_tick=1100, regen_status_bonus=20,
    )
    assert buffed_hp == no_buff_hp + 20


def test_refresh_status_adds_to_mp():
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=1000)
    _, no_buff_mp = s.compute_tick(now_tick=1100)
    s2 = RestingState(actor_id="bob", level=30)
    s2.start_resting(now_tick=1000)
    _, buffed_mp = s2.compute_tick(
        now_tick=1100, refresh_status_bonus=4,
    )
    assert buffed_mp == no_buff_mp + 4


def test_higher_level_heals_more():
    s_low = RestingState(actor_id="alice", level=10)
    s_low.start_resting(now_tick=1000)
    s_high = RestingState(actor_id="bob", level=99)
    s_high.start_resting(now_tick=1000)
    low_hp, _ = s_low.compute_tick(now_tick=1100)
    high_hp, _ = s_high.compute_tick(now_tick=1100)
    assert high_hp >= low_hp


def test_tempo_multiplier_is_3x():
    """Demoncore explicitly bumps the resting rate."""
    assert TEMPO_MULTIPLIER == 3.0


def test_tick_interval_halved_from_retail():
    """Retail = 4s, Demoncore = 2s."""
    assert TICK_INTERVAL_SECONDS == 2


def test_ramp_is_short_enough():
    """Retail = 20s, Demoncore should ramp inside one heal cycle."""
    assert RAMP_DURATION_SECONDS <= 10


def test_post_ramp_baseline_is_3x_retail():
    """At level 30 wilderness, retail base would be 14 HP/tick.
    Demoncore should be ~3x that (with the wilderness +25% on top)."""
    s = RestingState(actor_id="alice", level=30)
    s.start_resting(now_tick=0)
    hp, _ = s.compute_tick(
        now_tick=RAMP_DURATION_SECONDS,
        zone=ZoneModifier.WILDERNESS,
    )
    # Retail level-30 base: 14. Demoncore: 14 * 3 = 42 * 1.25 (zone)
    # = ~52. Allow generous tolerance for rounding.
    assert hp >= 42


def test_dungeon_no_longer_punishing():
    """Dungeon multiplier raised from 0.75 -> 1.0; rest rate
    matches wilderness baseline minus the wilderness floor bump."""
    s = RestingState(actor_id="alice", level=50)
    s.start_resting(now_tick=0)
    hp, _ = s.compute_tick(
        now_tick=RAMP_DURATION_SECONDS,
        zone=ZoneModifier.DUNGEON,
    )
    # Should still produce a meaningful heal — at least 30 HP/tick
    assert hp >= 30


def test_city_double_baseline():
    """City multiplier 2.0 - rests heal twice as fast as a 1.0
    multiplier zone."""
    s_city = RestingState(actor_id="alice", level=50)
    s_city.start_resting(now_tick=0)
    s_dungeon = RestingState(actor_id="bob", level=50)
    s_dungeon.start_resting(now_tick=0)
    city_hp, _ = s_city.compute_tick(
        now_tick=RAMP_DURATION_SECONDS, zone=ZoneModifier.CITY,
    )
    dungeon_hp, _ = s_dungeon.compute_tick(
        now_tick=RAMP_DURATION_SECONDS, zone=ZoneModifier.DUNGEON,
    )
    assert city_hp >= dungeon_hp * 2 * 0.95   # ~2x within rounding


def test_per_tick_cap_holds():
    s = RestingState(actor_id="alice", level=99)
    s.start_resting(now_tick=0)
    hp, _ = s.compute_tick(
        now_tick=RAMP_DURATION_SECONDS,
        zone=ZoneModifier.CITY,
        food_bonus_pct=99,
    )
    # Even level-99 city food-buffed shouldn't rocket past a sane
    # ceiling. Cap is 75 base * 2.0 city * 1.99 food = ~298. Good.
    # But the BASE per tick is capped at PER_TICK_CAP=75 before
    # zone/food multipliers; verify that floor exists.
    base_only = RestingState(actor_id="naked", level=99)
    base_only.start_resting(now_tick=0)
    pure_base, _ = base_only.compute_tick(
        now_tick=RAMP_DURATION_SECONDS,
        zone=ZoneModifier.WILDERNESS,
    )
    # Level 99 raw = 12 + 89/10 = 20; * 3 tempo = 60. Cap=75. Fine.
    # Wilderness 1.25 -> 75. Should be no higher.
    assert pure_base <= int(PER_TICK_CAP * 1.25 + 1)


def test_full_lifecycle_rest_session():
    s = RestingState(actor_id="alice", level=50)
    s.start_resting(now_tick=10000)
    total_hp = 0
    for offset in (5, 10, 15, 20, 30, 60, 90):
        hp, _ = s.compute_tick(
            now_tick=10000 + offset,
            zone=ZoneModifier.CITY,
        )
        total_hp += hp
    assert total_hp > 0
    s.stop_resting()
    assert not s.is_resting
