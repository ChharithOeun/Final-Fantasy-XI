"""Tests for torch_system."""
from __future__ import annotations

from server.torch_system import LightSourceKind, TorchSystem


def test_light_basic_torch():
    t = TorchSystem()
    ok = t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    assert ok is True
    assert t.is_lit(player_id="alice", now_seconds=10) is True


def test_blank_player_blocked():
    t = TorchSystem()
    out = t.light(
        player_id="", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    assert out is False


def test_already_lit_blocked():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    again = t.light(
        player_id="alice", kind=LightSourceKind.LANTERN,
        started_at=10,
    )
    assert again is False


def test_visible_radius():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.LANTERN,
        started_at=0,
    )
    assert t.visible_radius(
        player_id="alice", now_seconds=10,
    ) == 12


def test_visible_radius_when_unlit():
    t = TorchSystem()
    assert t.visible_radius(
        player_id="alice", now_seconds=10,
    ) == 0


def test_tick_consumes_fuel():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    fuel = t.tick(
        player_id="alice", dt_seconds=60,
        now_seconds=60,
    )
    # 300 base - 60 = 240
    assert fuel == 240


def test_tick_extinguishes_when_empty():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    fuel = t.tick(
        player_id="alice", dt_seconds=400,
        now_seconds=400,
    )
    assert fuel == 0
    assert t.is_lit(
        player_id="alice", now_seconds=400,
    ) is False


def test_wet_doubles_consumption():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    fuel = t.tick(
        player_id="alice", dt_seconds=60,
        now_seconds=60, wet=True,
    )
    # 300 - 120 = 180
    assert fuel == 180


def test_extinguish_returns_remaining_fuel():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    t.tick(
        player_id="alice", dt_seconds=100, now_seconds=100,
    )
    fuel = t.extinguish(player_id="alice", now_seconds=100)
    assert fuel == 200


def test_extinguish_when_unlit():
    t = TorchSystem()
    assert t.extinguish(
        player_id="alice", now_seconds=10,
    ) == 0


def test_infinite_fuel_for_brazier():
    t = TorchSystem()
    t.light(
        player_id="alice",
        kind=LightSourceKind.FOMOR_BRAZIER,
        started_at=0,
    )
    # tick a long time
    fuel = t.tick(
        player_id="alice", dt_seconds=10000,
        now_seconds=10000,
    )
    assert fuel == -1   # infinite
    assert t.is_lit(
        player_id="alice", now_seconds=10000,
    ) is True


def test_extinguish_infinite_returns_minus_one():
    t = TorchSystem()
    t.light(
        player_id="alice",
        kind=LightSourceKind.FOMOR_BRAZIER, started_at=0,
    )
    fuel = t.extinguish(player_id="alice", now_seconds=100)
    assert fuel == -1


def test_lantern_lasts_30_min():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.LANTERN,
        started_at=0,
    )
    fuel = t.tick(
        player_id="alice", dt_seconds=1800,
        now_seconds=1800,
    )
    assert fuel == 0


def test_define_custom_kind():
    t = TorchSystem()
    custom = LightSourceKind.BASIC_TORCH  # rebind via define
    ok = t.define_kind(
        kind=custom, max_fuel_seconds=600,
        radius_yalms=10,
    )
    assert ok is True
    t.light(
        player_id="alice", kind=custom, started_at=0,
    )
    assert t.visible_radius(
        player_id="alice", now_seconds=10,
    ) == 10


def test_define_zero_fuel_blocked():
    t = TorchSystem()
    out = t.define_kind(
        kind=LightSourceKind.LANTERN,
        max_fuel_seconds=0, radius_yalms=10,
    )
    assert out is False


def test_define_negative_radius_blocked():
    t = TorchSystem()
    out = t.define_kind(
        kind=LightSourceKind.LANTERN,
        max_fuel_seconds=600, radius_yalms=-1,
    )
    assert out is False


def test_per_player_independent():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.LANTERN,
        started_at=0,
    )
    t.light(
        player_id="bob", kind=LightSourceKind.OIL_LAMP,
        started_at=0,
    )
    assert t.visible_radius(
        player_id="alice", now_seconds=10,
    ) == 12
    assert t.visible_radius(
        player_id="bob", now_seconds=10,
    ) == 15
    assert t.total_active() == 2


def test_tick_when_unlit_returns_zero():
    t = TorchSystem()
    out = t.tick(
        player_id="ghost", dt_seconds=10, now_seconds=10,
    )
    assert out == 0


def test_relight_after_extinguish():
    t = TorchSystem()
    t.light(
        player_id="alice", kind=LightSourceKind.BASIC_TORCH,
        started_at=0,
    )
    t.extinguish(player_id="alice", now_seconds=100)
    again = t.light(
        player_id="alice", kind=LightSourceKind.LANTERN,
        started_at=200,
    )
    assert again is True


def test_five_light_kinds():
    assert len(list(LightSourceKind)) == 5
