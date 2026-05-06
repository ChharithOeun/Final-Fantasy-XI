"""Tests for boss_ability_tells."""
from __future__ import annotations

from server.boss_ability_tells import (
    BossAbilityTells,
    TellKind,
)


def test_register_happy():
    t = BossAbilityTells()
    ok = t.register_ability(
        boss_id="vorrak", ability_id="spirit_surge",
        tells=[TellKind.WEAPON_GLOW, TellKind.GUSTING_WIND],
        lead_time_seconds=3.0,
        anchor_label="boss right arm",
    )
    assert ok is True


def test_blank_boss_blocked():
    t = BossAbilityTells()
    ok = t.register_ability(
        boss_id="", ability_id="x",
        tells=[TellKind.DUST_FALLING], lead_time_seconds=2.0,
    )
    assert ok is False


def test_blank_ability_blocked():
    t = BossAbilityTells()
    ok = t.register_ability(
        boss_id="vorrak", ability_id="",
        tells=[TellKind.DUST_FALLING], lead_time_seconds=2.0,
    )
    assert ok is False


def test_zero_lead_time_blocked():
    t = BossAbilityTells()
    ok = t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.DUST_FALLING], lead_time_seconds=0,
    )
    assert ok is False


def test_no_tells_blocked():
    t = BossAbilityTells()
    ok = t.register_ability(
        boss_id="vorrak", ability_id="x", tells=[],
        lead_time_seconds=2.0,
    )
    assert ok is False


def test_dup_blocked():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.DUST_FALLING], lead_time_seconds=2.0,
    )
    ok = t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.WATER_RIPPLE], lead_time_seconds=3.0,
    )
    assert ok is False


def test_on_wind_up_emits_events():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="spirit_surge",
        tells=[TellKind.WEAPON_GLOW, TellKind.GUSTING_WIND],
        lead_time_seconds=3.0,
        anchor_label="boss right arm",
    )
    out = t.on_ability_wind_up(
        boss_id="vorrak", ability_id="spirit_surge",
        now_seconds=10.0,
    )
    assert len(out) == 2
    assert out[0].fires_at == 10.0
    assert out[0].ability_lands_at == 13.0
    assert out[0].anchor_label == "boss right arm"


def test_unknown_ability_no_events():
    t = BossAbilityTells()
    out = t.on_ability_wind_up(
        boss_id="ghost", ability_id="x", now_seconds=10.0,
    )
    assert out == ()


def test_get_returns_full_record():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="mirahna", ability_id="meteor_dual",
        tells=[TellKind.SHADOW_LENGTHENS, TellKind.AIR_DISTORTS],
        lead_time_seconds=4.0,
        anchor_label="ceiling above boss",
    )
    a = t.get(boss_id="mirahna", ability_id="meteor_dual")
    assert a is not None
    assert a.lead_time_seconds == 4.0
    assert TellKind.SHADOW_LENGTHENS in a.tells


def test_all_for_boss():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.DUST_FALLING], lead_time_seconds=2.0,
    )
    t.register_ability(
        boss_id="vorrak", ability_id="y",
        tells=[TellKind.WATER_RIPPLE], lead_time_seconds=3.0,
    )
    t.register_ability(
        boss_id="mirahna", ability_id="z",
        tells=[TellKind.AIR_DISTORTS], lead_time_seconds=2.0,
    )
    out = t.all_for_boss(boss_id="vorrak")
    assert len(out) == 2


def test_ability_tells_returns_tells():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.DUST_FALLING, TellKind.EARTH_CRACK],
        lead_time_seconds=2.0,
    )
    tells = t.ability_tells(boss_id="vorrak", ability_id="x")
    assert TellKind.DUST_FALLING in tells
    assert TellKind.EARTH_CRACK in tells


def test_8_tell_kinds():
    """8 canonical tell kinds defined."""
    assert len(list(TellKind)) == 8


def test_unknown_get_returns_none():
    t = BossAbilityTells()
    assert t.get(boss_id="ghost", ability_id="x") is None


def test_unknown_ability_tells_returns_empty():
    t = BossAbilityTells()
    assert t.ability_tells(
        boss_id="ghost", ability_id="x",
    ) == ()


def test_lead_time_floats_supported():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="x",
        tells=[TellKind.DUST_FALLING],
        lead_time_seconds=1.5,
    )
    out = t.on_ability_wind_up(
        boss_id="vorrak", ability_id="x", now_seconds=10.0,
    )
    assert out[0].ability_lands_at == 11.5


def test_multiple_tells_same_anchor():
    t = BossAbilityTells()
    t.register_ability(
        boss_id="vorrak", ability_id="quake",
        tells=[
            TellKind.EARTH_CRACK,
            TellKind.DUST_FALLING,
            TellKind.GUSTING_WIND,
        ],
        lead_time_seconds=3.0,
        anchor_label="arena floor",
    )
    out = t.on_ability_wind_up(
        boss_id="vorrak", ability_id="quake", now_seconds=20.0,
    )
    assert all(e.anchor_label == "arena floor" for e in out)
    assert len(out) == 3
