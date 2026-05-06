"""Tests for ration_pack."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload
from server.ration_pack import PackKind, RationPackRegistry


def _pack(r, pid="p1", **overrides):
    kwargs = dict(
        pack_id=pid, owner_id="alice",
        kind=PackKind.TRAVEL_RATION,
        source_payload=BuffPayload(
            str_bonus=10, vit_bonus=4, duration_seconds=600,
        ),
        packed_at=10,
    )
    kwargs.update(overrides)
    return r.pack_from_meal(**kwargs)


def test_pack_happy():
    r = RationPackRegistry()
    assert _pack(r) is True


def test_pack_blank_id():
    r = RationPackRegistry()
    assert _pack(r, pid="") is False


def test_pack_blank_owner():
    r = RationPackRegistry()
    assert _pack(r, owner_id="") is False


def test_pack_duplicate_blocked():
    r = RationPackRegistry()
    _pack(r)
    assert _pack(r) is False


def test_pack_diminishes_magnitude():
    r = RationPackRegistry()
    _pack(r, source_payload=BuffPayload(
        str_bonus=10, vit_bonus=4, duration_seconds=600,
    ))
    out = r.consume(pack_id="p1", consumer_id="alice")
    assert out is not None
    # 50% of 10 = 5
    assert out.str_bonus == 5
    # 50% of 4 = 2
    assert out.vit_bonus == 2
    # 50% of 600 = 300
    assert out.duration_seconds == 300


def test_consume_unknown():
    r = RationPackRegistry()
    out = r.consume(pack_id="ghost", consumer_id="alice")
    assert out is None


def test_consume_wrong_owner_blocked():
    r = RationPackRegistry()
    _pack(r)
    out = r.consume(pack_id="p1", consumer_id="bob")
    assert out is None
    assert r.total_packs() == 1


def test_consume_removes_pack():
    r = RationPackRegistry()
    _pack(r)
    r.consume(pack_id="p1", consumer_id="alice")
    assert r.total_packs() == 0


def test_age_all_no_op_under_shelf():
    r = RationPackRegistry()
    _pack(r)
    # 29 days
    out = r.age_all(dt_seconds=29 * 24 * 3600)
    assert out == 0
    assert r.available(pack_id="p1") is True


def test_age_all_spoils_at_shelf():
    r = RationPackRegistry()
    _pack(r)
    # 31 days
    out = r.age_all(dt_seconds=31 * 24 * 3600)
    assert out == 1
    assert r.available(pack_id="p1") is False


def test_consume_after_spoil_blocked():
    r = RationPackRegistry()
    _pack(r)
    r.age_all(dt_seconds=31 * 24 * 3600)
    out = r.consume(pack_id="p1", consumer_id="alice")
    assert out is None


def test_age_zero_dt():
    r = RationPackRegistry()
    _pack(r)
    assert r.age_all(dt_seconds=0) == 0


def test_available_unknown():
    r = RationPackRegistry()
    assert r.available(pack_id="ghost") is False


def test_three_pack_kinds():
    assert len(list(PackKind)) == 3


def test_total_packs():
    r = RationPackRegistry()
    _pack(r, pid="a")
    _pack(r, pid="b")
    assert r.total_packs() == 2


def test_shelf_is_30_days():
    r = RationPackRegistry()
    assert r.shelf_seconds() == 30 * 24 * 3600


def test_min_duration_floor():
    r = RationPackRegistry()
    _pack(r, source_payload=BuffPayload(duration_seconds=1))
    out = r.consume(pack_id="p1", consumer_id="alice")
    # 50% of 1 = 0, but floor at 1
    assert out.duration_seconds >= 1
