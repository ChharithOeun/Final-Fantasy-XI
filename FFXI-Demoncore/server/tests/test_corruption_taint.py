"""Tests for corruption taint."""
from __future__ import annotations

from server.corruption_taint import CorruptionTaint, TaintBand


def test_default_clean():
    c = CorruptionTaint()
    assert c.level(player_id="p") == 0
    assert c.band(player_id="p") == TaintBand.CLEAN


def test_add_happy():
    c = CorruptionTaint()
    r = c.add(player_id="p", amount=15, source="cult_step")
    assert r.accepted is True
    assert r.new_level == 15
    assert r.new_band == TaintBand.TINGED


def test_add_blank_player():
    c = CorruptionTaint()
    r = c.add(player_id="", amount=10, source="x")
    assert r.accepted is False


def test_add_blank_source():
    c = CorruptionTaint()
    r = c.add(player_id="p", amount=10, source="")
    assert r.accepted is False


def test_add_zero_amount():
    c = CorruptionTaint()
    r = c.add(player_id="p", amount=0, source="x")
    assert r.accepted is False


def test_add_caps_at_100():
    c = CorruptionTaint()
    c.add(player_id="p", amount=80, source="x")
    r = c.add(player_id="p", amount=50, source="x")
    assert r.accepted is True
    assert r.new_level == 100
    assert r.delta_applied == 20


def test_band_progression():
    c = CorruptionTaint()
    c.add(player_id="p", amount=5, source="x")
    assert c.band(player_id="p") == TaintBand.CLEAN
    c.add(player_id="p", amount=5, source="x")  # 10
    assert c.band(player_id="p") == TaintBand.TINGED
    c.add(player_id="p", amount=20, source="x")  # 30
    assert c.band(player_id="p") == TaintBand.SICKENED
    c.add(player_id="p", amount=30, source="x")  # 60
    assert c.band(player_id="p") == TaintBand.ABYSSAL
    c.add(player_id="p", amount=40, source="x")  # 100
    assert c.band(player_id="p") == TaintBand.HOLLOWED


def test_effects_at_sickened():
    c = CorruptionTaint()
    c.add(player_id="p", amount=40, source="x")
    e = c.effects(player_id="p")
    assert e.dark_damage_bonus_pct == 10
    assert e.surface_npc_trust_delta_pct == -15
    assert e.pressure_tiers_negated_bonus == 1
    assert e.surface_healers_refuse is False


def test_effects_at_abyssal():
    c = CorruptionTaint()
    c.add(player_id="p", amount=70, source="x")
    e = c.effects(player_id="p")
    assert e.surface_healers_refuse is True
    assert e.locked_to_cult is False


def test_effects_at_hollowed_locks_cult():
    c = CorruptionTaint()
    c.add(player_id="p", amount=100, source="x")
    e = c.effects(player_id="p")
    assert e.locked_to_cult is True


def test_is_hollowed():
    c = CorruptionTaint()
    c.add(player_id="p", amount=99, source="x")
    assert c.is_hollowed(player_id="p") is False
    c.add(player_id="p", amount=1, source="x")
    assert c.is_hollowed(player_id="p") is True


def test_add_after_hollowed_blocked():
    c = CorruptionTaint()
    c.add(player_id="p", amount=100, source="x")
    r = c.add(player_id="p", amount=10, source="x")
    assert r.accepted is False
    assert r.reason == "already hollowed"


def test_cleanse_lowers_level():
    c = CorruptionTaint()
    c.add(player_id="p", amount=50, source="x")
    r = c.cleanse(
        player_id="p", amount=15, source="silmaril_rite",
    )
    assert r.accepted is True
    assert r.new_level == 35
    assert r.delta_applied == -15


def test_cleanse_floor_zero():
    c = CorruptionTaint()
    c.add(player_id="p", amount=10, source="x")
    r = c.cleanse(
        player_id="p", amount=99, source="silmaril_rite",
    )
    assert r.new_level == 0
    assert r.new_band == TaintBand.CLEAN


def test_cleanse_blocked_at_hollowed_unless_redemption():
    c = CorruptionTaint()
    c.add(player_id="p", amount=100, source="x")
    bad = c.cleanse(
        player_id="p", amount=10, source="silmaril_rite",
    )
    assert bad.accepted is False
    good = c.cleanse(
        player_id="p", amount=10, source="cult_redemption_quest",
    )
    assert good.accepted is True
    assert good.new_level == 90


def test_cleanse_zero_amount_rejected():
    c = CorruptionTaint()
    r = c.cleanse(player_id="p", amount=0, source="x")
    assert r.accepted is False
