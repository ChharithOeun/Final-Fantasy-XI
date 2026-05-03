"""Tests for lore fragment collection."""
from __future__ import annotations

import pytest

from server.lore_fragments import (
    Fragment,
    LoreFragmentRegistry,
    LoreScope,
    LoreSet,
    LoreSetReward,
)


def _set(
    set_id: str = "twin_princes",
    pages: int = 3,
) -> LoreSet:
    return LoreSet(
        set_id=set_id, label="Twin Princes' Diary",
        scope=LoreScope.REGIONAL,
        total_pages=pages,
        faction_id="san_doria",
        reward=LoreSetReward(
            title_id="title_chronicler_twin_princes",
            signature_item_id="diary_replica",
            faction_rep_bonus=50,
        ),
    )


def _frag(
    fragment_id: str, set_id: str = "twin_princes",
    page: int = 1,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id, set_id=set_id,
        page_number=page,
        title=f"Page {page}",
    )


def test_register_set():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    assert reg.lore_set("twin_princes") is not None
    assert reg.total_sets() == 1


def test_register_fragment_for_unknown_set_rejected():
    reg = LoreFragmentRegistry()
    with pytest.raises(ValueError):
        reg.register_fragment(_frag("p1"))


def test_register_fragment_for_known_set():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_fragment(_frag("p1"))
    assert reg.fragment("p1") is not None


def test_fragments_in_set_filters():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_set(_set(set_id="other", pages=2))
    reg.register_fragment(_frag("p1", set_id="twin_princes"))
    reg.register_fragment(_frag("p2", set_id="twin_princes"))
    reg.register_fragment(_frag("o1", set_id="other"))
    twin_frags = reg.fragments_in_set("twin_princes")
    assert len(twin_frags) == 2


def test_discover_unknown_fragment_rejected():
    reg = LoreFragmentRegistry()
    res = reg.discover(
        player_id="alice", fragment_id="ghost",
    )
    assert not res.accepted


def test_discover_first_time_grants_honor():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_fragment(_frag("p1"))
    res = reg.discover(
        player_id="alice", fragment_id="p1",
        now_seconds=100.0,
    )
    assert res.accepted
    assert res.is_first_time
    assert res.honor_gained == 5


def test_discover_again_does_not_double_pay():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_fragment(_frag("p1"))
    reg.discover(
        player_id="alice", fragment_id="p1",
    )
    second = reg.discover(
        player_id="alice", fragment_id="p1",
    )
    assert second.accepted
    assert not second.is_first_time
    assert second.honor_gained == 0


def test_completing_set_flags_completion():
    reg = LoreFragmentRegistry()
    reg.register_set(_set(pages=3))
    for i in range(1, 4):
        reg.register_fragment(_frag(f"p{i}", page=i))
    # Discover all three
    last = None
    for i in range(1, 4):
        last = reg.discover(
            player_id="alice", fragment_id=f"p{i}",
        )
    assert last.set_completed
    completion = reg.check_set_completion(
        player_id="alice", set_id="twin_princes",
    )
    assert completion.is_complete
    assert completion.reward is not None


def test_partial_set_not_complete():
    reg = LoreFragmentRegistry()
    reg.register_set(_set(pages=3))
    for i in range(1, 4):
        reg.register_fragment(_frag(f"p{i}", page=i))
    # Only 2 out of 3
    reg.discover(player_id="alice", fragment_id="p1")
    reg.discover(player_id="alice", fragment_id="p2")
    completion = reg.check_set_completion(
        player_id="alice", set_id="twin_princes",
    )
    assert not completion.is_complete
    assert completion.pages_owned == 2
    assert completion.pages_total == 3


def test_check_set_completion_unknown_set():
    reg = LoreFragmentRegistry()
    res = reg.check_set_completion(
        player_id="alice", set_id="ghost",
    )
    assert not res.is_complete
    assert res.pages_total == 0


def test_player_collection_returns_owned():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_fragment(_frag("p1"))
    reg.register_fragment(_frag("p2", page=2))
    reg.discover(player_id="alice", fragment_id="p1")
    coll = reg.player_collection("alice")
    assert "p1" in coll
    assert "p2" not in coll


def test_completed_sets_lists_completions():
    reg = LoreFragmentRegistry()
    reg.register_set(_set(pages=2))
    reg.register_fragment(_frag("p1"))
    reg.register_fragment(_frag("p2", page=2))
    reg.discover(player_id="alice", fragment_id="p1")
    reg.discover(player_id="alice", fragment_id="p2")
    completed = reg.completed_sets("alice")
    assert "twin_princes" in completed


def test_isolated_player_collections():
    reg = LoreFragmentRegistry()
    reg.register_set(_set())
    reg.register_fragment(_frag("p1"))
    reg.discover(player_id="alice", fragment_id="p1")
    assert "p1" in reg.player_collection("alice")
    assert reg.player_collection("bob") == ()


def test_full_lifecycle_alice_completes_set():
    """Alice discovers fragments one by one, gets honor each
    time, and ultimately unlocks the set reward."""
    reg = LoreFragmentRegistry()
    reg.register_set(_set(pages=3))
    for i in range(1, 4):
        reg.register_fragment(_frag(f"p{i}", page=i))
    total_honor = 0
    for i in range(1, 4):
        res = reg.discover(
            player_id="alice", fragment_id=f"p{i}",
        )
        total_honor += res.honor_gained
    assert total_honor == 15  # 3 fragments * 5 honor each
    completion = reg.check_set_completion(
        player_id="alice", set_id="twin_princes",
    )
    assert completion.is_complete
    assert (
        completion.reward.title_id
        == "title_chronicler_twin_princes"
    )
    assert "twin_princes" in reg.completed_sets("alice")
