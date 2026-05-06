"""Tests for target_cycle."""
from __future__ import annotations

from server.target_cycle import TargetCycler


def _setup():
    c = TargetCycler()
    c.set_party_roster(
        player_id="alice",
        party=["alice", "bob", "cara", "dirk", "eve"],
    )
    c.set_nearby_hostiles(
        player_id="alice",
        ordered=["goblin", "orc", "yagudo", "tonberry"],
    )
    return c


def test_party_roster_happy():
    c = _setup()
    out = c.target_party_slot(player_id="alice", slot=2)
    assert out == "bob"
    assert c.current(player_id="alice") == "bob"


def test_party_roster_blank_player_blocked():
    c = TargetCycler()
    out = c.set_party_roster(player_id="", party=["alice"])
    assert out is False


def test_party_roster_too_large_blocked():
    c = TargetCycler()
    out = c.set_party_roster(
        player_id="alice",
        party=["a", "b", "c", "d", "e", "f", "g"],   # 7 > 6
    )
    assert out is False


def test_party_slot_out_of_range():
    c = _setup()
    out = c.target_party_slot(player_id="alice", slot=99)
    assert out is None


def test_party_slot_zero_invalid():
    c = _setup()
    out = c.target_party_slot(player_id="alice", slot=0)
    assert out is None


def test_target_nearest_hostile():
    c = _setup()
    out = c.target_nearest_hostile(player_id="alice")
    assert out == "goblin"   # first in ordered list


def test_target_nearest_no_hostiles():
    c = TargetCycler()
    c.set_party_roster(player_id="alice", party=["alice"])
    out = c.target_nearest_hostile(player_id="alice")
    assert out is None


def test_target_nearest_unknown_player():
    c = TargetCycler()
    out = c.target_nearest_hostile(player_id="ghost")
    assert out is None


def test_cycle_hostile_forward():
    c = _setup()
    c.target_nearest_hostile(player_id="alice")
    a = c.cycle_hostile(player_id="alice", direction=1)
    b = c.cycle_hostile(player_id="alice", direction=1)
    assert a == "orc"
    assert b == "yagudo"


def test_cycle_hostile_backward():
    c = _setup()
    c.target_nearest_hostile(player_id="alice")
    out = c.cycle_hostile(player_id="alice", direction=-1)
    # 0 - 1 mod 4 → index 3 → tonberry
    assert out == "tonberry"


def test_cycle_hostile_wraps():
    c = _setup()
    c.target_nearest_hostile(player_id="alice")
    for _ in range(4):
        c.cycle_hostile(player_id="alice", direction=1)
    # back to start
    assert c.current(player_id="alice") == "goblin"


def test_cycle_hostile_no_list_returns_none():
    c = TargetCycler()
    c.set_party_roster(player_id="alice", party=["alice"])
    out = c.cycle_hostile(player_id="alice", direction=1)
    assert out is None


def test_recall_previous_swaps():
    c = _setup()
    c.target_party_slot(player_id="alice", slot=2)   # bob
    c.target_nearest_hostile(player_id="alice")      # goblin
    out = c.recall_previous(player_id="alice")
    assert out == "bob"
    # previous now holds the goblin
    assert c.current(player_id="alice") == "bob"


def test_recall_previous_no_history():
    c = _setup()
    out = c.recall_previous(player_id="alice")
    assert out is None


def test_recall_previous_unknown_player():
    c = TargetCycler()
    out = c.recall_previous(player_id="ghost")
    assert out is None


def test_clear_target():
    c = _setup()
    c.target_nearest_hostile(player_id="alice")
    out = c.clear(player_id="alice")
    assert out is True
    assert c.current(player_id="alice") == ""


def test_clear_no_current_target():
    c = _setup()
    out = c.clear(player_id="alice")
    assert out is False


def test_clear_unknown_player():
    c = TargetCycler()
    out = c.clear(player_id="ghost")
    assert out is False


def test_current_unknown_player_empty():
    c = TargetCycler()
    assert c.current(player_id="ghost") == ""


def test_setting_new_hostiles_resets_cursor():
    c = _setup()
    c.cycle_hostile(player_id="alice", direction=1)
    c.cycle_hostile(player_id="alice", direction=1)
    # reset with fresh list
    c.set_nearby_hostiles(
        player_id="alice", ordered=["new_mob"],
    )
    out = c.cycle_hostile(player_id="alice", direction=1)
    assert out == "new_mob"


def test_total_tracked_grows():
    c = _setup()
    c.set_party_roster(player_id="bob", party=["bob"])
    assert c.total_tracked() == 2
