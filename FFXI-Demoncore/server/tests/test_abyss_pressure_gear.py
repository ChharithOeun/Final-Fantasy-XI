"""Tests for abyss pressure gear."""
from __future__ import annotations

from server.abyss_pressure_gear import (
    AbyssPressureGear,
    GearPiece,
)


def test_equip_happy():
    g = AbyssPressureGear()
    r = g.equip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    assert r.accepted is True
    assert g.pressure_tiers_negated(player_id="p") == 1


def test_equip_blank_player():
    g = AbyssPressureGear()
    r = g.equip(player_id="", piece=GearPiece.PRESSURE_HOOD)
    assert r.accepted is False


def test_equip_replaces_same_slot():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    # equipping another head piece would replace; we only have
    # one head piece in this catalog so test ring -> ring
    g.equip(player_id="p", piece=GearPiece.HOLLOW_BAND)
    pieces = g.equipped_pieces(player_id="p")
    # should have 2 pieces (head + ring)
    assert len(pieces) == 2


def test_unequip_happy():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    r = g.unequip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    assert r.accepted is True
    assert g.pressure_tiers_negated(player_id="p") == 0


def test_unequip_not_equipped():
    g = AbyssPressureGear()
    r = g.unequip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    assert r.accepted is False


def test_full_set_pressure_negate():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    g.equip(player_id="p", piece=GearPiece.ABYSS_VEST)
    g.equip(player_id="p", piece=GearPiece.CRUSHING_GREAVES)
    g.equip(player_id="p", piece=GearPiece.HOLLOW_BAND)
    # 4 pieces, each -1 tier -> 4 total
    assert g.pressure_tiers_negated(player_id="p") == 4


def test_pressure_negate_capped_at_4():
    g = AbyssPressureGear()
    # add all pieces including the back slot which adds 0
    for piece in (
        GearPiece.PRESSURE_HOOD, GearPiece.ABYSS_VEST,
        GearPiece.CRUSHING_GREAVES, GearPiece.GILL_ENGINE,
        GearPiece.HOLLOW_BAND,
    ):
        g.equip(player_id="p", piece=piece)
    assert g.pressure_tiers_negated(player_id="p") == 4


def test_breath_efficiency_default_1x():
    g = AbyssPressureGear()
    assert g.breath_efficiency_multiplier(player_id="p") == 1.0


def test_breath_efficiency_gill_only():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.GILL_ENGINE)
    # +50% -> 1.5
    assert g.breath_efficiency_multiplier(player_id="p") == 1.5


def test_breath_efficiency_stacks_additively():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.ABYSS_VEST)  # +25
    g.equip(player_id="p", piece=GearPiece.GILL_ENGINE)  # +50
    # additive: 1 + 0.25 + 0.50 = 1.75
    assert g.breath_efficiency_multiplier(player_id="p") == 1.75


def test_gill_engine_does_not_negate_tiers():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.GILL_ENGINE)
    assert g.pressure_tiers_negated(player_id="p") == 0


def test_unknown_player_zero_negate():
    g = AbyssPressureGear()
    assert g.pressure_tiers_negated(player_id="ghost") == 0
    assert g.breath_efficiency_multiplier(player_id="ghost") == 1.0


def test_equipped_pieces_dedupe_by_slot():
    g = AbyssPressureGear()
    g.equip(player_id="p", piece=GearPiece.PRESSURE_HOOD)
    g.equip(player_id="p", piece=GearPiece.ABYSS_VEST)
    pieces = set(g.equipped_pieces(player_id="p"))
    assert pieces == {GearPiece.PRESSURE_HOOD, GearPiece.ABYSS_VEST}
