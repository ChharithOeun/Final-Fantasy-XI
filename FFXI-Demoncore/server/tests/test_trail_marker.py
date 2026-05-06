"""Tests for trail_marker."""
from __future__ import annotations

from server.trail_marker import MarkerKind, TrailMarkerRegistry


def test_place_happy():
    r = TrailMarkerRegistry()
    ok = r.place(
        marker_id="m1", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="east_wood",
        x=10.0, y=20.0, note="fork in path",
        placed_at=10,
    )
    assert ok is True
    m = r.get(marker_id="m1")
    assert m is not None
    assert m.note == "fork in path"


def test_place_blank_id_blocked():
    r = TrailMarkerRegistry()
    out = r.place(
        marker_id="", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="zone",
        x=0, y=0, note="", placed_at=0,
    )
    assert out is False


def test_place_blank_owner_blocked():
    r = TrailMarkerRegistry()
    out = r.place(
        marker_id="m", owner_id="",
        kind=MarkerKind.STONE_CAIRN, zone="zone",
        x=0, y=0, note="", placed_at=0,
    )
    assert out is False


def test_place_blank_zone_blocked():
    r = TrailMarkerRegistry()
    out = r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="",
        x=0, y=0, note="", placed_at=0,
    )
    assert out is False


def test_place_duplicate_blocked():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.WOOD_BLAZE, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    again = r.place(
        marker_id="m", owner_id="bob",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=1, y=1, note="", placed_at=10,
    )
    assert again is False


def test_erase_owner_ok():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.erase(marker_id="m", by_owner_id="alice")
    assert out is True
    assert r.get(marker_id="m") is None


def test_erase_non_owner_blocked():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.erase(marker_id="m", by_owner_id="bob")
    assert out is False
    assert r.get(marker_id="m") is not None


def test_erase_unknown():
    r = TrailMarkerRegistry()
    out = r.erase(marker_id="ghost", by_owner_id="alice")
    assert out is False


def test_clear_weather_no_damage():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(weather_kind="clear", dt_seconds=999)
    assert out == 0
    m = r.get(marker_id="m")
    assert m.durability == 60


def test_rain_destroys_chalk():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    # CHALK base 60, rain 5/sec → 13 sec destroys it
    out = r.weather_tick(weather_kind="rain", dt_seconds=13)
    assert out == 1
    assert r.get(marker_id="m") is None


def test_rain_doesnt_destroy_cairn():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(weather_kind="rain", dt_seconds=9999)
    assert out == 0
    assert r.get(marker_id="m") is not None


def test_blizzard_damages_cairn_eventually():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    # CAIRN 1000 hp, blizzard 1/sec → 1000 sec exact
    out = r.weather_tick(weather_kind="blizzard", dt_seconds=1000)
    assert out == 1


def test_unknown_weather_no_damage():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(weather_kind="aurora", dt_seconds=999)
    assert out == 0
    assert r.get(marker_id="m") is not None


def test_zero_dt_no_damage():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(weather_kind="rain", dt_seconds=0)
    assert out == 0


def test_weather_tick_zone_filter():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m1", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="east_wood",
        x=0, y=0, note="", placed_at=0,
    )
    r.place(
        marker_id="m2", owner_id="alice",
        kind=MarkerKind.CHALK_MARK, zone="south_marsh",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(
        weather_kind="rain", dt_seconds=20,
        zone="east_wood",
    )
    assert out == 1
    # south_marsh marker untouched
    assert r.get(marker_id="m2") is not None


def test_visible_in_zone_filters():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m1", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="east_wood",
        x=0, y=0, note="", placed_at=0,
    )
    r.place(
        marker_id="m2", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="south_marsh",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.visible_in_zone(zone="east_wood")
    assert len(out) == 1
    assert out[0].marker_id == "m1"


def test_visible_in_zone_empty():
    r = TrailMarkerRegistry()
    out = r.visible_in_zone(zone="ghost_zone")
    assert out == []


def test_nearest_returns_closest():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="far", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=100, y=100, note="", placed_at=0,
    )
    r.place(
        marker_id="near", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=2, y=2, note="", placed_at=0,
    )
    out = r.nearest(zone="z", x=0, y=0)
    assert out is not None
    assert out.marker_id == "near"


def test_nearest_skips_other_zones():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="other",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.nearest(zone="z", x=0, y=0)
    assert out is None


def test_nearest_empty():
    r = TrailMarkerRegistry()
    out = r.nearest(zone="z", x=0, y=0)
    assert out is None


def test_get_unknown():
    r = TrailMarkerRegistry()
    assert r.get(marker_id="ghost") is None


def test_total_markers():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="a", owner_id="alice",
        kind=MarkerKind.STONE_CAIRN, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    r.place(
        marker_id="b", owner_id="alice",
        kind=MarkerKind.WOOD_BLAZE, zone="z",
        x=1, y=1, note="", placed_at=0,
    )
    assert r.total_markers() == 2


def test_five_marker_kinds():
    assert len(list(MarkerKind)) == 5


def test_bone_totem_resists_rain():
    r = TrailMarkerRegistry()
    r.place(
        marker_id="m", owner_id="alice",
        kind=MarkerKind.BONE_TOTEM, zone="z",
        x=0, y=0, note="", placed_at=0,
    )
    out = r.weather_tick(weather_kind="rain", dt_seconds=9999)
    assert out == 0
