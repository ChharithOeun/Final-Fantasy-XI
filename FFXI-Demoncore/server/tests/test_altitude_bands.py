"""Tests for altitude bands."""
from __future__ import annotations

from server.altitude_bands import (
    ADJACENT_BAND_FADE,
    AerialMinimap,
    AltitudeBand,
    BAND_ALTITUDE_M,
    SAME_BAND_OPACITY,
)


def test_register_happy():
    m = AerialMinimap()
    assert m.register(
        entity_id="airship1", band=AltitudeBand.MID,
        x=10, y=20, kind="airship",
    ) is True


def test_register_blank():
    m = AerialMinimap()
    assert m.register(
        entity_id="", band=AltitudeBand.MID,
        x=0, y=0, kind="airship",
    ) is False


def test_visible_same_band():
    m = AerialMinimap()
    m.register(
        entity_id="e1", band=AltitudeBand.MID,
        x=0, y=0, kind="airship",
    )
    out = m.visible_to(player_band=AltitudeBand.MID)
    assert len(out) == 1
    assert out[0].fade_factor == SAME_BAND_OPACITY


def test_visible_adjacent_faded():
    m = AerialMinimap()
    m.register(
        entity_id="e1", band=AltitudeBand.LOW,
        x=0, y=0, kind="skiff",
    )
    out = m.visible_to(player_band=AltitudeBand.MID)
    assert len(out) == 1
    assert out[0].fade_factor == ADJACENT_BAND_FADE


def test_visible_far_hidden():
    m = AerialMinimap()
    m.register(
        entity_id="dragon", band=AltitudeBand.STRATOSPHERE,
        x=0, y=0, kind="wyvern",
    )
    out = m.visible_to(player_band=AltitudeBand.LOW)
    assert len(out) == 0


def test_ground_to_low_adjacent():
    m = AerialMinimap()
    m.register(
        entity_id="cart", band=AltitudeBand.GROUND,
        x=0, y=0, kind="caravan",
    )
    out = m.visible_to(player_band=AltitudeBand.LOW)
    assert len(out) == 1
    assert out[0].fade_factor == ADJACENT_BAND_FADE


def test_update_position():
    m = AerialMinimap()
    m.register(
        entity_id="e1", band=AltitudeBand.LOW,
        x=0, y=0, kind="skiff",
    )
    ok = m.update_position(
        entity_id="e1", band=AltitudeBand.HIGH,
        x=99, y=88,
    )
    assert ok is True
    assert m.altitude_of(entity_id="e1") == AltitudeBand.HIGH


def test_update_unknown_returns_false():
    m = AerialMinimap()
    assert m.update_position(
        entity_id="ghost", band=AltitudeBand.MID, x=0, y=0,
    ) is False


def test_remove():
    m = AerialMinimap()
    m.register(
        entity_id="e1", band=AltitudeBand.MID,
        x=0, y=0, kind="airship",
    )
    assert m.remove(entity_id="e1") is True
    assert m.altitude_of(entity_id="e1") is None


def test_remove_unknown():
    m = AerialMinimap()
    assert m.remove(entity_id="ghost") is False


def test_altitude_of_unknown():
    m = AerialMinimap()
    assert m.altitude_of(entity_id="ghost") is None


def test_band_altitudes_canonical():
    assert BAND_ALTITUDE_M[0] == 0.0
    assert BAND_ALTITUDE_M[4] == 8000.0


def test_visibility_mixed_bands():
    m = AerialMinimap()
    m.register(
        entity_id="same", band=AltitudeBand.MID, x=0, y=0, kind="airship",
    )
    m.register(
        entity_id="adj_up", band=AltitudeBand.HIGH, x=0, y=0, kind="zeppelin",
    )
    m.register(
        entity_id="adj_dn", band=AltitudeBand.LOW, x=0, y=0, kind="skiff",
    )
    m.register(
        entity_id="far", band=AltitudeBand.STRATOSPHERE,
        x=0, y=0, kind="wyvern",
    )
    out = m.visible_to(player_band=AltitudeBand.MID)
    ids = {c.entity_id for c in out}
    assert "same" in ids
    assert "adj_up" in ids
    assert "adj_dn" in ids
    assert "far" not in ids
