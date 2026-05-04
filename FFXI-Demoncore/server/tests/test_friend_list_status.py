"""Tests for the friend list status."""
from __future__ import annotations

from server.friend_list_status import (
    FriendListStatus,
    PresenceState,
)


def test_add_friend():
    f = FriendListStatus()
    assert f.add_friend(
        viewer_id="alice", friend_id="bob",
    )
    assert f.is_friend(
        viewer_id="alice", friend_id="bob",
    )


def test_add_self_rejected():
    f = FriendListStatus()
    assert not f.add_friend(
        viewer_id="alice", friend_id="alice",
    )


def test_double_add_rejected():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    assert not f.add_friend(
        viewer_id="alice", friend_id="bob",
    )


def test_remove_friend():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    assert f.remove_friend(
        viewer_id="alice", friend_id="bob",
    )
    assert not f.is_friend(
        viewer_id="alice", friend_id="bob",
    )


def test_remove_unknown_friend():
    f = FriendListStatus()
    assert not f.remove_friend(
        viewer_id="alice", friend_id="bob",
    )


def test_update_presence():
    f = FriendListStatus()
    f.update_presence(
        player_id="bob", state=PresenceState.ONLINE,
        zone_id="bastok", main_job="WAR",
        main_level=75, sub_job="NIN", sub_level=37,
        now_seconds=100.0,
    )
    f.add_friend(viewer_id="alice", friend_id="bob")
    statuses = f.friends_for(viewer_id="alice")
    assert statuses[0].state == PresenceState.ONLINE
    assert statuses[0].zone_id == "bastok"
    assert statuses[0].job_string == "WAR75/NIN37"


def test_friends_for_offline_friends():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    statuses = f.friends_for(viewer_id="alice")
    # bob has no presence — defaults to OFFLINE
    assert statuses[0].state == PresenceState.OFFLINE
    assert statuses[0].job_string == ""


def test_friends_for_sort_order():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="online_friend")
    f.add_friend(viewer_id="alice", friend_id="offline_friend")
    f.add_friend(viewer_id="alice", friend_id="afk_friend")
    f.update_presence(
        player_id="online_friend",
        state=PresenceState.ONLINE,
    )
    f.update_presence(
        player_id="afk_friend",
        state=PresenceState.AFK,
    )
    f.update_presence(
        player_id="offline_friend",
        state=PresenceState.OFFLINE,
    )
    statuses = f.friends_for(viewer_id="alice")
    states = [s.state for s in statuses]
    assert states == [
        PresenceState.ONLINE,
        PresenceState.AFK,
        PresenceState.OFFLINE,
    ]


def test_summary_for():
    f = FriendListStatus()
    for fid, state in (
        ("a", PresenceState.ONLINE),
        ("b", PresenceState.ONLINE),
        ("c", PresenceState.AFK),
        ("d", PresenceState.OFFLINE),
    ):
        f.add_friend(viewer_id="alice", friend_id=fid)
        f.update_presence(player_id=fid, state=state)
    summary = f.summary_for(viewer_id="alice")
    assert summary["total"] == 4
    assert summary["online"] == 2
    assert summary["afk"] == 1
    assert summary["offline"] == 1


def test_in_fight_state_propagates():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    f.update_presence(
        player_id="bob",
        state=PresenceState.IN_FIGHT,
    )
    statuses = f.friends_for(viewer_id="alice")
    assert statuses[0].state == PresenceState.IN_FIGHT


def test_in_fight_sorts_after_online():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    f.add_friend(viewer_id="alice", friend_id="carol")
    f.update_presence(
        player_id="bob",
        state=PresenceState.IN_FIGHT,
    )
    f.update_presence(
        player_id="carol",
        state=PresenceState.ONLINE,
    )
    statuses = f.friends_for(viewer_id="alice")
    assert statuses[0].friend_id == "carol"
    assert statuses[1].friend_id == "bob"


def test_main_job_only_no_subjob():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    f.update_presence(
        player_id="bob",
        state=PresenceState.ONLINE,
        main_job="BLM", main_level=99,
    )
    statuses = f.friends_for(viewer_id="alice")
    assert statuses[0].job_string == "BLM99"


def test_zone_persists_across_updates():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    f.update_presence(
        player_id="bob",
        state=PresenceState.ONLINE,
        zone_id="jeuno",
    )
    # Update without zone — keeps prior
    f.update_presence(
        player_id="bob", state=PresenceState.AFK,
    )
    statuses = f.friends_for(viewer_id="alice")
    assert statuses[0].zone_id == "jeuno"


def test_per_viewer_isolation():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    statuses_b = f.friends_for(viewer_id="bob")
    assert statuses_b == ()


def test_total_friend_pairs():
    f = FriendListStatus()
    f.add_friend(viewer_id="alice", friend_id="bob")
    f.add_friend(viewer_id="alice", friend_id="carol")
    f.add_friend(viewer_id="bob", friend_id="dave")
    assert f.total_friend_pairs() == 3
