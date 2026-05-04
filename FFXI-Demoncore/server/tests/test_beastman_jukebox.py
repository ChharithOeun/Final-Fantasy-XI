"""Tests for the beastman jukebox."""
from __future__ import annotations

from server.beastman_jukebox import (
    BeastmanJukebox,
    TrackTint,
)


def test_register_track():
    j = BeastmanJukebox()
    t = j.register_track(
        track_id="oz_anthem",
        name="Oztroja Anthem",
        tint=TrackTint.YAGUDO,
    )
    assert t is not None
    assert j.total_tracks() == 1


def test_register_duplicate():
    j = BeastmanJukebox()
    j.register_track(
        track_id="x", name="X", tint=TrackTint.NEUTRAL,
    )
    res = j.register_track(
        track_id="x", name="X2", tint=TrackTint.YAGUDO,
    )
    assert res is None


def test_register_empty_id():
    j = BeastmanJukebox()
    res = j.register_track(
        track_id="", name="X", tint=TrackTint.NEUTRAL,
    )
    assert res is None


def test_register_empty_name():
    j = BeastmanJukebox()
    res = j.register_track(
        track_id="x", name="", tint=TrackTint.NEUTRAL,
    )
    assert res is None


def test_unlock_basic():
    j = BeastmanJukebox()
    j.register_track(
        track_id="oz_anthem", name="X", tint=TrackTint.YAGUDO,
    )
    assert j.unlock(player_id="kraw", track_id="oz_anthem")


def test_unlock_unknown_track():
    j = BeastmanJukebox()
    assert not j.unlock(player_id="kraw", track_id="ghost")


def test_unlock_double():
    j = BeastmanJukebox()
    j.register_track(
        track_id="oz_anthem", name="X", tint=TrackTint.YAGUDO,
    )
    j.unlock(player_id="kraw", track_id="oz_anthem")
    assert not j.unlock(player_id="kraw", track_id="oz_anthem")


def test_is_unlocked():
    j = BeastmanJukebox()
    j.register_track(
        track_id="oz_anthem", name="X", tint=TrackTint.YAGUDO,
    )
    j.unlock(player_id="kraw", track_id="oz_anthem")
    assert j.is_unlocked(
        player_id="kraw", track_id="oz_anthem",
    )
    assert not j.is_unlocked(
        player_id="ghost", track_id="oz_anthem",
    )


def test_set_active_basic():
    j = BeastmanJukebox()
    j.register_track(
        track_id="oz_anthem", name="Anthem", tint=TrackTint.YAGUDO,
    )
    j.unlock(player_id="kraw", track_id="oz_anthem")
    res = j.set_active(
        player_id="kraw", track_id="oz_anthem",
    )
    assert res.accepted


def test_set_active_locked():
    j = BeastmanJukebox()
    j.register_track(
        track_id="oz_anthem", name="X", tint=TrackTint.YAGUDO,
    )
    res = j.set_active(
        player_id="kraw", track_id="oz_anthem",
    )
    assert not res.accepted


def test_set_active_unknown_track():
    j = BeastmanJukebox()
    res = j.set_active(
        player_id="kraw", track_id="ghost",
    )
    assert not res.accepted


def test_set_active_replaces_previous():
    j = BeastmanJukebox()
    j.register_track(
        track_id="t1", name="T1", tint=TrackTint.YAGUDO,
    )
    j.register_track(
        track_id="t2", name="T2", tint=TrackTint.LAMIA,
    )
    j.unlock(player_id="kraw", track_id="t1")
    j.unlock(player_id="kraw", track_id="t2")
    j.set_active(player_id="kraw", track_id="t1")
    j.set_active(player_id="kraw", track_id="t2")
    active = j.active_for(player_id="kraw")
    assert active.track_id == "t2"


def test_active_for_default_none():
    j = BeastmanJukebox()
    assert j.active_for(player_id="ghost") is None


def test_unlocked_for_sorted():
    j = BeastmanJukebox()
    j.register_track(
        track_id="b", name="B", tint=TrackTint.YAGUDO,
    )
    j.register_track(
        track_id="a", name="A", tint=TrackTint.QUADAV,
    )
    j.unlock(player_id="kraw", track_id="b")
    j.unlock(player_id="kraw", track_id="a")
    rs = j.unlocked_for(player_id="kraw")
    assert rs[0].track_id == "a"
    assert rs[1].track_id == "b"


def test_unlocked_for_empty():
    j = BeastmanJukebox()
    assert j.unlocked_for(player_id="ghost") == ()


def test_per_player_isolation():
    j = BeastmanJukebox()
    j.register_track(
        track_id="t1", name="T1", tint=TrackTint.YAGUDO,
    )
    j.unlock(player_id="alice", track_id="t1")
    assert not j.is_unlocked(
        player_id="bob", track_id="t1",
    )


def test_track_tint_pulls_through():
    j = BeastmanJukebox()
    j.register_track(
        track_id="t1", name="T1", tint=TrackTint.ORC,
    )
    j.unlock(player_id="kraw", track_id="t1")
    j.set_active(player_id="kraw", track_id="t1")
    active = j.active_for(player_id="kraw")
    assert active.tint == TrackTint.ORC


def test_neutral_tracks():
    j = BeastmanJukebox()
    t = j.register_track(
        track_id="neutral_drone",
        name="Goblin Trade Drone",
        tint=TrackTint.NEUTRAL,
    )
    assert t.tint == TrackTint.NEUTRAL
