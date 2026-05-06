"""Tests for sahagin queen fight."""
from __future__ import annotations

from server.sahagin_queen_fight import (
    GUARD_PARTY_COMP,
    GUARD_SUMMON_INTERVAL_SECONDS,
    GuardRole,
    MAX_ACTIVE_AVATARS,
    OXYGEN_TANK_BONUS_SECONDS,
    OXYGEN_TANK_RADIUS_YALMS,
    SahaginQueenFight,
)


def test_start_happy():
    q = SahaginQueenFight()
    assert q.start(
        fight_id="f1", hp_max=1_000_000, now_seconds=0,
    ) is True


def test_start_blank():
    q = SahaginQueenFight()
    assert q.start(
        fight_id="", hp_max=1_000_000, now_seconds=0,
    ) is False


def test_start_zero_hp():
    q = SahaginQueenFight()
    assert q.start(fight_id="f1", hp_max=0, now_seconds=0) is False


def test_double_start_blocked():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    assert q.start(fight_id="f1", hp_max=200, now_seconds=10) is False


def test_dual_cast_returns_two_copies():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    out = q.dual_cast(
        fight_id="f1", spell_id="meteor", now_seconds=10,
    )
    assert out == ("meteor", "meteor")


def test_dual_cast_unknown_fight():
    q = SahaginQueenFight()
    out = q.dual_cast(
        fight_id="ghost", spell_id="meteor", now_seconds=0,
    )
    assert out == ("", "")


def test_summon_avatar_happy():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    assert q.summon_avatar(
        fight_id="f1", avatar_id="leviathan",
    ) is True
    assert q.active_avatar_count(fight_id="f1") == 1


def test_summon_avatar_max_3():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    for av in ["leviathan", "diabolos", "shiva"]:
        assert q.summon_avatar(fight_id="f1", avatar_id=av) is True
    assert q.active_avatar_count(fight_id="f1") == MAX_ACTIVE_AVATARS
    overflow = q.summon_avatar(
        fight_id="f1", avatar_id="ifrit",
    )
    assert overflow is False


def test_summon_avatar_dup_blocked():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    q.summon_avatar(fight_id="f1", avatar_id="leviathan")
    assert q.summon_avatar(
        fight_id="f1", avatar_id="leviathan",
    ) is False


def test_summon_avatar_blank_blocked():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    assert q.summon_avatar(fight_id="f1", avatar_id="") is False


def test_guard_summon_too_early():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = q.tick_guard_summons(fight_id="f1", now_seconds=60)
    assert out is not None
    assert out.summoned is False


def test_guard_summon_at_interval():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = q.tick_guard_summons(
        fight_id="f1", now_seconds=GUARD_SUMMON_INTERVAL_SECONDS,
    )
    assert out is not None
    assert out.summoned is True
    assert len(out.guard_ids) == 5
    assert tuple(out.roles) == GUARD_PARTY_COMP


def test_guard_party_comp_canonical():
    """1 tank + 1 healer + 1 support + 2 dps."""
    counts = {role: 0 for role in GuardRole}
    for r in GUARD_PARTY_COMP:
        counts[r] += 1
    assert counts[GuardRole.TANK] == 1
    assert counts[GuardRole.HEALER] == 1
    assert counts[GuardRole.SUPPORT] == 1
    assert counts[GuardRole.DPS] == 2


def test_royal_guard_killed_with_double_mb_drops_tank():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    summons = q.tick_guard_summons(
        fight_id="f1", now_seconds=GUARD_SUMMON_INTERVAL_SECONDS,
    )
    target_id = summons.guard_ids[0]
    drop = q.royal_guard_killed(
        fight_id="f1", guard_id=target_id,
        magic_burst_count=2,
        killing_blow_was_double_mb=True,
        now_seconds=GUARD_SUMMON_INTERVAL_SECONDS + 30,
    )
    assert drop is not None
    assert drop.dropped is True
    assert drop.radius_yalms == OXYGEN_TANK_RADIUS_YALMS
    assert drop.bonus_seconds == OXYGEN_TANK_BONUS_SECONDS


def test_royal_guard_killed_normal_kill_no_drop():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    summons = q.tick_guard_summons(
        fight_id="f1", now_seconds=GUARD_SUMMON_INTERVAL_SECONDS,
    )
    target_id = summons.guard_ids[0]
    drop = q.royal_guard_killed(
        fight_id="f1", guard_id=target_id,
        magic_burst_count=0,
        killing_blow_was_double_mb=False,
        now_seconds=GUARD_SUMMON_INTERVAL_SECONDS + 30,
    )
    assert drop is not None
    assert drop.dropped is False


def test_single_mb_kill_no_drop():
    """One MB on the killing blow isn't enough — must be DOUBLE MB."""
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    summons = q.tick_guard_summons(
        fight_id="f1", now_seconds=GUARD_SUMMON_INTERVAL_SECONDS,
    )
    target_id = summons.guard_ids[0]
    drop = q.royal_guard_killed(
        fight_id="f1", guard_id=target_id,
        magic_burst_count=1,
        killing_blow_was_double_mb=False,
        now_seconds=GUARD_SUMMON_INTERVAL_SECONDS + 30,
    )
    assert drop is not None
    assert drop.dropped is False


def test_unknown_guard_id():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    drop = q.royal_guard_killed(
        fight_id="f1", guard_id="ghost",
        magic_burst_count=2,
        killing_blow_was_double_mb=True,
        now_seconds=10,
    )
    assert drop is None


def test_damage_queen():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    q.damage_queen(fight_id="f1", amount=100_000, now_seconds=10)
    assert q.queen_hp(fight_id="f1") == 900_000


def test_damage_dead_queen_blocked():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    q.damage_queen(fight_id="f1", amount=200, now_seconds=10)
    ok = q.damage_queen(fight_id="f1", amount=50, now_seconds=20)
    assert ok is False


def test_summon_blocked_after_death():
    q = SahaginQueenFight()
    q.start(fight_id="f1", hp_max=100, now_seconds=0)
    q.damage_queen(fight_id="f1", amount=200, now_seconds=10)
    assert q.tick_guard_summons(
        fight_id="f1", now_seconds=GUARD_SUMMON_INTERVAL_SECONDS,
    ) is None


def test_unknown_fight_safe():
    q = SahaginQueenFight()
    assert q.queen_hp(fight_id="ghost") == 0
    assert q.active_avatar_count(fight_id="ghost") == 0
    assert q.tick_guard_summons(
        fight_id="ghost", now_seconds=0,
    ) is None
