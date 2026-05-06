"""Tests for sahagin royals."""
from __future__ import annotations

from server.sahagin_royals import (
    DUAL_KILL_WINDOW_SECONDS,
    KingdomState,
    Royal,
    RoyalState,
    SahaginRoyals,
)


def _seed(s: SahaginRoyals):
    s.set_royal(
        royal=Royal.KING, hp_max=100_000,
        name="Vorrak the Drowner", now_seconds=0,
    )
    s.set_royal(
        royal=Royal.QUEEN, hp_max=100_000,
        name="Mirahna the Tide-Hag", now_seconds=0,
    )


def test_set_royal_happy():
    s = SahaginRoyals()
    assert s.set_royal(
        royal=Royal.KING, hp_max=100_000, name="X", now_seconds=0,
    ) is True


def test_set_royal_blank_name():
    s = SahaginRoyals()
    assert s.set_royal(
        royal=Royal.KING, hp_max=100_000, name="", now_seconds=0,
    ) is False


def test_set_royal_zero_hp():
    s = SahaginRoyals()
    assert s.set_royal(
        royal=Royal.KING, hp_max=0, name="X", now_seconds=0,
    ) is False


def test_set_royal_double_blocked():
    s = SahaginRoyals()
    s.set_royal(royal=Royal.KING, hp_max=100, name="X", now_seconds=0)
    assert s.set_royal(
        royal=Royal.KING, hp_max=200, name="Y", now_seconds=10,
    ) is False


def test_default_state_absent():
    s = SahaginRoyals()
    assert s.royal_state(royal=Royal.KING) == RoyalState.ABSENT


def test_after_set_state_alive():
    s = SahaginRoyals()
    _seed(s)
    assert s.royal_state(royal=Royal.KING) == RoyalState.ALIVE


def test_damage_partial_keeps_alive():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=10_000,
        attacker_id="p1", now_seconds=10,
    )
    assert out.accepted is True
    assert out.royal_dead is False
    assert out.royal_state == RoyalState.ALIVE


def test_damage_to_wounded():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=60_000,
        attacker_id="p1", now_seconds=10,
    )
    assert out.royal_state == RoyalState.WOUNDED


def test_damage_to_enraged():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=80_000,
        attacker_id="p1", now_seconds=10,
    )
    assert out.royal_state == RoyalState.ENRAGED


def test_damage_to_zero_kills():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=10,
    )
    assert out.royal_dead is True
    assert out.royal_state == RoyalState.DEAD


def test_damage_dead_blocked():
    s = SahaginRoyals()
    _seed(s)
    s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=10,
    )
    out = s.damage_royal(
        royal=Royal.KING, amount=10,
        attacker_id="p1", now_seconds=20,
    )
    assert out.accepted is False


def test_damage_unset_royal_blocked():
    s = SahaginRoyals()
    out = s.damage_royal(
        royal=Royal.KING, amount=100,
        attacker_id="p1", now_seconds=0,
    )
    assert out.accepted is False


def test_damage_zero_blocked():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=0,
        attacker_id="p1", now_seconds=0,
    )
    assert out.accepted is False


def test_kingdom_healthy_when_both_alive():
    s = SahaginRoyals()
    _seed(s)
    assert s.kingdom_state(now_seconds=0) == KingdomState.HEALTHY


def test_kingdom_civil_war_one_dead():
    s = SahaginRoyals()
    _seed(s)
    s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=100,
    )
    assert s.kingdom_state(
        now_seconds=200,
    ) == KingdomState.CIVIL_WAR


def test_kingdom_shattered_dual_kill_window():
    s = SahaginRoyals()
    _seed(s)
    s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=100,
    )
    s.damage_royal(
        royal=Royal.QUEEN, amount=200_000,
        attacker_id="p1", now_seconds=100 + 30,  # within window
    )
    assert s.kingdom_state(
        now_seconds=200,
    ) == KingdomState.SHATTERED
    assert s.both_dead_in_window() is True


def test_kingdom_civil_war_when_dual_kill_outside_window():
    s = SahaginRoyals()
    _seed(s)
    s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=100,
    )
    # second kill way outside window
    s.damage_royal(
        royal=Royal.QUEEN, amount=200_000,
        attacker_id="p1",
        now_seconds=100 + DUAL_KILL_WINDOW_SECONDS + 1000,
    )
    # both dead but kingdom is in CIVIL_WAR (not shattered)
    assert s.kingdom_state(
        now_seconds=10_000,
    ) == KingdomState.CIVIL_WAR
    assert s.both_dead_in_window() is False


def test_widow_enrage_flag_when_one_dead():
    s = SahaginRoyals()
    _seed(s)
    s.damage_royal(
        royal=Royal.KING, amount=200_000,
        attacker_id="p1", now_seconds=100,
    )
    # damage queen now — widow_enrage should fire
    out = s.damage_royal(
        royal=Royal.QUEEN, amount=10_000,
        attacker_id="p1", now_seconds=110,
    )
    assert out.widow_enrage_active is True


def test_widow_enrage_off_when_both_alive():
    s = SahaginRoyals()
    _seed(s)
    out = s.damage_royal(
        royal=Royal.KING, amount=10_000,
        attacker_id="p1", now_seconds=10,
    )
    assert out.widow_enrage_active is False
