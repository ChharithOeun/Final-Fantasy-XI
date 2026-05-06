"""Tests for monument_placer."""
from __future__ import annotations

from server.monument_placer import (
    MonumentKind,
    MonumentPlacer,
)


def test_place_happy():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="ru_lude_gardens",
        position=(120.0, 5.0, -45.5),
        kind=MonumentKind.OBELISK,
        inscription="Here Iron Wing felled Vorrak",
        source_entry_id="hist_42",
        placed_at=1000,
    )
    assert mid == "mon_1"
    assert p.total_placed() == 1


def test_blank_zone_blocked():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="", position=(0, 0, 0),
        kind=MonumentKind.CAIRN,
        inscription="x", source_entry_id=None,
        placed_at=10,
    )
    assert mid == ""


def test_blank_inscription_blocked():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.CAIRN, inscription="",
        source_entry_id=None, placed_at=10,
    )
    assert mid == ""


def test_get_missing_returns_none():
    p = MonumentPlacer()
    assert p.get(monument_id="ghost") is None


def test_deface_happy():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.OBELISK,
        inscription="x", source_entry_id=None,
        placed_at=10,
    )
    assert p.deface(monument_id=mid, defaced_at=20) is True
    m = p.get(monument_id=mid)
    assert m is not None and m.defaced is True


def test_double_deface_blocked():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.OBELISK,
        inscription="x", source_entry_id=None,
        placed_at=10,
    )
    p.deface(monument_id=mid, defaced_at=20)
    again = p.deface(monument_id=mid, defaced_at=30)
    assert again is False


def test_vandalism_resistant_immune():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.STATUE,
        inscription="Eternal", source_entry_id=None,
        placed_at=10, vandalism_resistant=True,
    )
    out = p.deface(monument_id=mid, defaced_at=20)
    assert out is False
    m = p.get(monument_id=mid)
    assert m is not None and m.defaced is False


def test_repair_after_deface():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.OBELISK,
        inscription="x", source_entry_id=None,
        placed_at=10,
    )
    p.deface(monument_id=mid, defaced_at=20)
    ok = p.repair(monument_id=mid, repaired_at=50)
    assert ok is True
    m = p.get(monument_id=mid)
    assert m is not None
    assert m.defaced is False
    assert m.last_repaired_at == 50


def test_repair_pristine_blocked():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.OBELISK,
        inscription="x", source_entry_id=None,
        placed_at=10,
    )
    out = p.repair(monument_id=mid, repaired_at=50)
    assert out is False


def test_monuments_in_zone():
    p = MonumentPlacer()
    p.place_monument(
        zone_id="bastok_markets", position=(0, 0, 0),
        kind=MonumentKind.STATUE, inscription="A",
        source_entry_id=None, placed_at=10,
    )
    p.place_monument(
        zone_id="bastok_markets", position=(10, 0, 0),
        kind=MonumentKind.PLAQUE, inscription="B",
        source_entry_id=None, placed_at=20,
    )
    p.place_monument(
        zone_id="san_doria", position=(0, 0, 0),
        kind=MonumentKind.OBELISK, inscription="C",
        source_entry_id=None, placed_at=30,
    )
    bm = p.monuments_in_zone(zone_id="bastok_markets")
    assert len(bm) == 2


def test_monuments_for_event():
    p = MonumentPlacer()
    p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.STATUE, inscription="A",
        source_entry_id="hist_1", placed_at=10,
    )
    p.place_monument(
        zone_id="z", position=(10, 0, 0),
        kind=MonumentKind.PLAQUE, inscription="B",
        source_entry_id="hist_1", placed_at=20,
    )
    p.place_monument(
        zone_id="z", position=(0, 0, 10),
        kind=MonumentKind.PLAQUE, inscription="C",
        source_entry_id="hist_2", placed_at=30,
    )
    e1 = p.monuments_for_event(source_entry_id="hist_1")
    assert len(e1) == 2


def test_no_source_entry_no_event_index():
    p = MonumentPlacer()
    p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.PLAQUE, inscription="x",
        source_entry_id=None, placed_at=10,
    )
    out = p.monuments_for_event(source_entry_id="hist_1")
    assert out == ()


def test_six_monument_kinds():
    assert len(list(MonumentKind)) == 6


def test_position_preserved():
    p = MonumentPlacer()
    mid = p.place_monument(
        zone_id="z", position=(123.4, -56.7, 89.0),
        kind=MonumentKind.OBELISK, inscription="x",
        source_entry_id=None, placed_at=10,
    )
    m = p.get(monument_id=mid)
    assert m is not None
    assert m.position == (123.4, -56.7, 89.0)


def test_repair_unknown_blocked():
    p = MonumentPlacer()
    out = p.repair(monument_id="ghost", repaired_at=10)
    assert out is False


def test_inscription_preserved():
    p = MonumentPlacer()
    text = "On this spot, alliance Iron Wing slew Vorrak."
    mid = p.place_monument(
        zone_id="z", position=(0, 0, 0),
        kind=MonumentKind.OBELISK, inscription=text,
        source_entry_id=None, placed_at=10,
    )
    m = p.get(monument_id=mid)
    assert m is not None
    assert m.inscription == text


def test_deface_unknown_blocked():
    p = MonumentPlacer()
    out = p.deface(monument_id="ghost", defaced_at=10)
    assert out is False
