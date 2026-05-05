"""Tests for underwater minimap."""
from __future__ import annotations

from server.underwater_minimap import (
    ADJACENT_BAND_FADE,
    DepthBand,
    SAME_BAND_OPACITY,
    UnderwaterMinimap,
)


def test_register_happy():
    m = UnderwaterMinimap()
    ok = m.register(
        entity_id="sub1", band=DepthBand.MID,
        x=10.0, y=20.0, kind="sub",
    )
    assert ok is True


def test_register_blank_id():
    m = UnderwaterMinimap()
    ok = m.register(
        entity_id="", band=DepthBand.MID,
        x=0, y=0, kind="sub",
    )
    assert ok is False


def test_visible_same_band_full_opacity():
    m = UnderwaterMinimap()
    m.register(
        entity_id="e1", band=DepthBand.MID,
        x=10, y=20, kind="sub",
    )
    out = m.visible_to(player_band=DepthBand.MID)
    assert len(out) == 1
    assert out[0].fade_factor == SAME_BAND_OPACITY


def test_visible_adjacent_band_faded():
    m = UnderwaterMinimap()
    m.register(
        entity_id="e1", band=DepthBand.SHALLOW,
        x=10, y=20, kind="sub",
    )
    out = m.visible_to(player_band=DepthBand.MID)
    assert len(out) == 1
    assert out[0].fade_factor == ADJACENT_BAND_FADE


def test_visible_far_band_hidden():
    m = UnderwaterMinimap()
    m.register(
        entity_id="e1", band=DepthBand.ABYSSAL,
        x=10, y=20, kind="kraken",
    )
    out = m.visible_to(player_band=DepthBand.SHALLOW)
    assert len(out) == 0


def test_visible_mixed_bands_all_resolve():
    m = UnderwaterMinimap()
    m.register(
        entity_id="same", band=DepthBand.MID,
        x=0, y=0, kind="sub",
    )
    m.register(
        entity_id="adj_up", band=DepthBand.SHALLOW,
        x=0, y=0, kind="sub",
    )
    m.register(
        entity_id="adj_dn", band=DepthBand.DEEP,
        x=0, y=0, kind="sub",
    )
    m.register(
        entity_id="far", band=DepthBand.ABYSSAL,
        x=0, y=0, kind="kraken",
    )
    out = m.visible_to(player_band=DepthBand.MID)
    ids = {c.entity_id for c in out}
    assert "same" in ids
    assert "adj_up" in ids
    assert "adj_dn" in ids
    assert "far" not in ids


def test_update_position():
    m = UnderwaterMinimap()
    m.register(
        entity_id="e1", band=DepthBand.SHALLOW,
        x=0, y=0, kind="sub",
    )
    ok = m.update_position(
        entity_id="e1", band=DepthBand.MID,
        x=99, y=88,
    )
    assert ok is True
    assert m.depth_of(entity_id="e1") == DepthBand.MID


def test_update_unknown_returns_false():
    m = UnderwaterMinimap()
    ok = m.update_position(
        entity_id="ghost", band=DepthBand.MID, x=0, y=0,
    )
    assert ok is False


def test_remove():
    m = UnderwaterMinimap()
    m.register(
        entity_id="e1", band=DepthBand.MID,
        x=0, y=0, kind="sub",
    )
    ok = m.remove(entity_id="e1")
    assert ok is True
    assert m.depth_of(entity_id="e1") is None


def test_remove_unknown():
    m = UnderwaterMinimap()
    assert m.remove(entity_id="ghost") is False


def test_depth_of_unknown_is_none():
    m = UnderwaterMinimap()
    assert m.depth_of(entity_id="ghost") is None


def test_surface_to_shallow_adjacent():
    m = UnderwaterMinimap()
    m.register(
        entity_id="surface_ship", band=DepthBand.SURFACE,
        x=0, y=0, kind="ship",
    )
    out = m.visible_to(player_band=DepthBand.SHALLOW)
    assert len(out) == 1
    assert out[0].fade_factor == ADJACENT_BAND_FADE


def test_abyssal_visible_only_from_deep():
    m = UnderwaterMinimap()
    m.register(
        entity_id="abyss_thing", band=DepthBand.ABYSSAL,
        x=0, y=0, kind="kraken",
    )
    # from DEEP -> visible faded
    out = m.visible_to(player_band=DepthBand.DEEP)
    assert len(out) == 1
    # from MID -> hidden
    out = m.visible_to(player_band=DepthBand.MID)
    assert len(out) == 0
