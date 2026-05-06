"""Tests for sahagin king fight."""
from __future__ import annotations

from server.sahagin_king_fight import (
    FOMOR_PARTY_SIZE,
    FOMOR_SUMMON_INTERVAL_SECONDS,
    KingPhase,
    SahaginKingFight,
    SPIRIT_SURGE_HP_THRESHOLD,
)


def test_start_happy():
    k = SahaginKingFight()
    assert k.start(
        fight_id="f1", hp_max=1_000_000, now_seconds=0,
    ) is True


def test_start_blank():
    k = SahaginKingFight()
    assert k.start(
        fight_id="", hp_max=1_000_000, now_seconds=0,
    ) is False


def test_start_zero_hp():
    k = SahaginKingFight()
    assert k.start(fight_id="f1", hp_max=0, now_seconds=0) is False


def test_start_double_blocked():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=100, now_seconds=0)
    assert k.start(fight_id="f1", hp_max=200, now_seconds=10) is False


def test_initial_pets_alive():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    assert k.pet_alive_count(fight_id="f1") == 2


def test_summon_too_early_returns_empty():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.tick_summons(fight_id="f1", now_seconds=60)
    assert out == ()


def test_summon_at_interval():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.tick_summons(
        fight_id="f1", now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS,
    )
    assert len(out) == FOMOR_PARTY_SIZE


def test_summon_comp_scales_by_hp():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    early = k.tick_summons(
        fight_id="f1", now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS,
    )
    # damage king to <33%
    k.damage_king(
        fight_id="f1", amount=700_000,
        now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS + 10,
    )
    late = k.tick_summons(
        fight_id="f1",
        now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS * 2 + 10,
    )
    # comp should be different (warlord + darkblade in late)
    assert "warlord" in late
    assert "warlord" not in early


def test_damage_king_partial():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.damage_king(
        fight_id="f1", amount=100_000, now_seconds=10,
    )
    assert out.accepted is True
    assert out.king_hp_after == 900_000
    assert out.phase == KingPhase.PHASE_1


def test_damage_king_to_zero():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.damage_king(
        fight_id="f1", amount=2_000_000, now_seconds=10,
    )
    assert out.king_hp_after == 0
    assert out.phase == KingPhase.DEAD


def test_damage_dead_king_blocked():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    k.damage_king(
        fight_id="f1", amount=2_000_000, now_seconds=10,
    )
    out = k.damage_king(
        fight_id="f1", amount=10, now_seconds=20,
    )
    assert out.accepted is False


def test_damage_pet_first_pet():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.damage_pet(
        fight_id="f1", pet_idx=0, amount=999_999,
    )
    assert out.accepted is True
    assert out.pets_alive == 1
    assert out.phase == KingPhase.ENRAGED_LONE_PET


def test_damage_pet_invalid_idx():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    out = k.damage_pet(fight_id="f1", pet_idx=5, amount=100)
    assert out.accepted is False


def test_damage_dead_pet():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    k.damage_pet(fight_id="f1", pet_idx=0, amount=999_999)
    out = k.damage_pet(fight_id="f1", pet_idx=0, amount=10)
    assert out.accepted is False


def test_spirit_surge_at_low_hp():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    # damage to below 10% -> SPIRIT_SURGE
    out = k.damage_king(
        fight_id="f1", amount=950_000, now_seconds=10,
    )
    assert out.phase == KingPhase.SPIRIT_SURGE
    assert out.spirit_surge_pending is True


def test_spirit_surge_only_fires_once():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    k.damage_king(fight_id="f1", amount=950_000, now_seconds=10)
    out = k.damage_king(
        fight_id="f1", amount=10_000, now_seconds=20,
    )
    assert out.spirit_surge_pending is False


def test_summon_blocked_after_death():
    k = SahaginKingFight()
    k.start(fight_id="f1", hp_max=1_000_000, now_seconds=0)
    k.damage_king(
        fight_id="f1", amount=2_000_000,
        now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS - 10,
    )
    out = k.tick_summons(
        fight_id="f1", now_seconds=FOMOR_SUMMON_INTERVAL_SECONDS,
    )
    assert out == ()


def test_summon_threshold_check_canonical():
    assert FOMOR_SUMMON_INTERVAL_SECONDS == 180
    assert FOMOR_PARTY_SIZE == 6
    assert SPIRIT_SURGE_HP_THRESHOLD == 0.10


def test_unknown_fight_returns_safe():
    k = SahaginKingFight()
    assert k.king_hp(fight_id="ghost") == 0
    assert k.pet_alive_count(fight_id="ghost") == 0
    assert k.tick_summons(fight_id="ghost", now_seconds=0) == ()
