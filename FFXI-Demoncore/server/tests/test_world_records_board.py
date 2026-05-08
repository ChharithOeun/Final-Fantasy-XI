"""Tests for world_records_board."""
from __future__ import annotations

from server.world_records_board import (
    Category, Direction, WorldRecordsBoard,
)


def test_first_submission_accepted():
    w = WorldRecordsBoard()
    assert w.submit(
        category=Category.HIGHEST_GIL_DONATION,
        sub_key="", holder_id="bob",
        value=10000, day=10,
    ) is True


def test_blank_holder_blocked():
    w = WorldRecordsBoard()
    assert w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="",
        value=5, day=10,
    ) is False


def test_negative_value_blocked():
    w = WorldRecordsBoard()
    assert w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="bob",
        value=-1, day=10,
    ) is False


def test_higher_is_better_evicts():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.HIGHEST_GIL_DONATION,
        sub_key="", holder_id="bob",
        value=10000, day=10,
    )
    assert w.submit(
        category=Category.HIGHEST_GIL_DONATION,
        sub_key="", holder_id="cara",
        value=20000, day=11,
    ) is True
    cur = w.current(
        category=Category.HIGHEST_GIL_DONATION,
    )
    assert cur.holder_id == "cara"


def test_higher_lower_doesnt_evict():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.HIGHEST_GIL_DONATION,
        sub_key="", holder_id="bob",
        value=20000, day=10,
    )
    assert w.submit(
        category=Category.HIGHEST_GIL_DONATION,
        sub_key="", holder_id="cara",
        value=15000, day=11,
    ) is False


def test_lower_is_better_for_speed():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="bob",
        value=300, day=10,
    )
    assert w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="cara",
        value=250, day=11,
    ) is True


def test_slower_doesnt_evict():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="bob",
        value=300, day=10,
    )
    assert w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="cara",
        value=400, day=11,
    ) is False


def test_subkey_isolation():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="bob",
        value=300, day=10,
    )
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="tiamat", holder_id="cara",
        value=900, day=11,
    )
    assert w.current(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth",
    ).holder_id == "bob"
    assert w.current(
        category=Category.FASTEST_HNM_KILL,
        sub_key="tiamat",
    ).holder_id == "cara"


def test_current_unknown():
    w = WorldRecordsBoard()
    assert w.current(
        category=Category.MOST_SCARS,
    ) is None


def test_all_in_category():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="behemoth", holder_id="bob",
        value=300, day=10,
    )
    w.submit(
        category=Category.FASTEST_HNM_KILL,
        sub_key="tiamat", holder_id="cara",
        value=900, day=11,
    )
    out = w.all_in_category(
        category=Category.FASTEST_HNM_KILL,
    )
    assert len(out) == 2


def test_records_for_holder():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="bob",
        value=12, day=10,
    )
    w.submit(
        category=Category.MOST_MASTERWORKS,
        sub_key="", holder_id="bob",
        value=4, day=11,
    )
    w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="cara",
        value=14, day=12,
    )
    bob_records = w.records_for_holder(holder_id="bob")
    # Cara took the scars record; bob holds only masterworks
    assert len(bob_records) == 1
    assert (
        bob_records[0].category
        == Category.MOST_MASTERWORKS
    )


def test_total():
    w = WorldRecordsBoard()
    w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="bob",
        value=12, day=10,
    )
    w.submit(
        category=Category.MOST_MASTERWORKS,
        sub_key="", holder_id="bob",
        value=4, day=11,
    )
    assert w.total() == 2


def test_negative_day_blocked():
    w = WorldRecordsBoard()
    assert w.submit(
        category=Category.MOST_SCARS,
        sub_key="", holder_id="bob",
        value=5, day=-1,
    ) is False


def test_ten_categories():
    assert len(list(Category)) == 10


def test_two_directions():
    assert len(list(Direction)) == 2
