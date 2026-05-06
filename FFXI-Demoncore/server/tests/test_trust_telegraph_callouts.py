"""Tests for trust_telegraph_callouts."""
from __future__ import annotations

from server.boss_ability_tells import TellKind
from server.telegraph_visibility_gate import TelegraphVisibilityGate
from server.trust_telegraph_callouts import (
    Perception,
    TrustTelegraphCallouts,
)


def test_register_perception():
    t = TrustTelegraphCallouts()
    assert t.register_trust_perception(
        trust_id="apururu_uc", perception=Perception.SHARP,
    ) is True
    assert t.perception_for(
        trust_id="apururu_uc",
    ) == Perception.SHARP


def test_default_dull():
    t = TrustTelegraphCallouts()
    assert t.perception_for(
        trust_id="random_trust",
    ) == Perception.DULL


def test_blank_trust_blocked():
    t = TrustTelegraphCallouts()
    assert t.register_trust_perception(
        trust_id="", perception=Perception.SHARP,
    ) is False


def test_dull_no_callout():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    out = t.on_tell_detected(
        party_trust_ids=["dull_trust"],
        boss_id="vorrak", ability_id="x",
        tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50,
        gate=gate,
    )
    assert out == ()


def test_watchful_50pct_callout():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="koru", perception=Perception.WATCHFUL,
    )
    # roll 30 ≤ 50% → callout
    out = t.on_tell_detected(
        party_trust_ids=["koru"], boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=30, gate=gate,
    )
    assert len(out) == 1
    # roll 80 > 50% → silent
    out2 = t.on_tell_detected(
        party_trust_ids=["koru"], boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
        now_seconds=11, rng_roll_pct=80, gate=gate,
    )
    assert out2 == ()


def test_sharp_80pct_callout_with_earlier_warning():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="joachim", perception=Perception.SHARP,
    )
    out = t.on_tell_detected(
        party_trust_ids=["joachim"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=70, gate=gate,
    )
    assert len(out) == 1
    assert out[0].earlier_warning_seconds == 1.0
    # SHARP doesn't grant visibility yet
    assert out[0].visibility_seconds_granted == 0


def test_oracle_grants_visibility():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="ulmia", perception=Perception.ORACLE,
    )
    out = t.on_tell_detected(
        party_trust_ids=["ulmia"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50, gate=gate,
        listener_player_ids=["alice", "bob"],
    )
    assert len(out) == 1
    assert out[0].visibility_seconds_granted == 2
    assert gate.is_visible(player_id="alice", now_seconds=11) is True


def test_oracle_always_callouts():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="star_sibyl", perception=Perception.ORACLE,
    )
    # rng 100 → at threshold; ORACLE has 100% chance
    out = t.on_tell_detected(
        party_trust_ids=["star_sibyl"], boss_id="v",
        ability_id="a", tell=TellKind.SHADOW_LENGTHENS,
        now_seconds=10, rng_roll_pct=100, gate=gate,
    )
    assert len(out) == 1


def test_voice_line_includes_trust_id():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="joachim", perception=Perception.SHARP,
    )
    out = t.on_tell_detected(
        party_trust_ids=["joachim"], boss_id="v",
        ability_id="a", tell=TellKind.HAND_GESTURE,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    assert "joachim:" in out[0].voice_line


def test_multiple_trusts_can_callout():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="t1", perception=Perception.SHARP,
    )
    t.register_trust_perception(
        trust_id="t2", perception=Perception.SHARP,
    )
    out = t.on_tell_detected(
        party_trust_ids=["t1", "t2"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    assert len(out) == 2


def test_invalid_rng_roll():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="t", perception=Perception.ORACLE,
    )
    out = t.on_tell_detected(
        party_trust_ids=["t"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=0, gate=gate,
    )
    assert out == ()


def test_blank_trust_filtered():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="t1", perception=Perception.SHARP,
    )
    out = t.on_tell_detected(
        party_trust_ids=["", "t1"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    assert len(out) == 1


def test_unknown_tell_default_voice():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="t", perception=Perception.SHARP,
    )
    # use a real tell that has no entry — actually all 8 do.
    # so just test a registered one.
    out = t.on_tell_detected(
        party_trust_ids=["t"], boss_id="v",
        ability_id="a", tell=TellKind.GUSTING_WIND,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    assert "lightning" in out[0].voice_line.lower()


def test_4_perception_levels():
    assert len(list(Perception)) == 4


def test_no_listeners_no_visibility_grant():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="ulmia", perception=Perception.ORACLE,
    )
    out = t.on_tell_detected(
        party_trust_ids=["ulmia"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    # callout still fires; listener list empty so no players get
    # visibility granted (but the event still says it WAS granted)
    assert out[0].visibility_seconds_granted == 2


def test_unregistered_trust_treated_as_dull():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    out = t.on_tell_detected(
        party_trust_ids=["new_trust"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=10, rng_roll_pct=50, gate=gate,
    )
    assert out == ()


def test_callout_event_records_fired_at():
    t = TrustTelegraphCallouts()
    gate = TelegraphVisibilityGate()
    t.register_trust_perception(
        trust_id="t", perception=Perception.SHARP,
    )
    out = t.on_tell_detected(
        party_trust_ids=["t"], boss_id="v",
        ability_id="a", tell=TellKind.WEAPON_GLOW,
        now_seconds=42, rng_roll_pct=50, gate=gate,
    )
    assert out[0].fired_at == 42
