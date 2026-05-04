"""Tests for the DPS meter."""
from __future__ import annotations

from server.dps_meter import (
    DEFAULT_WINDOW_SECONDS,
    DPSMeter,
    EventKind,
)


def test_record_and_snapshot():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=300, at_seconds=0.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.damage_out == 300
    assert snap.dps == 30.0


def test_record_zero_rejected():
    m = DPSMeter()
    assert not m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=0, at_seconds=0.0,
    )


def test_record_negative_rejected():
    m = DPSMeter()
    assert not m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=-50, at_seconds=0.0,
    )


def test_window_excludes_old_events():
    m = DPSMeter(default_window=10.0)
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=1000, at_seconds=0.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=100.0,
    )
    # 1000 dmg at t=0, window covers t=90..100
    assert snap.damage_out == 0


def test_window_includes_inside_events():
    m = DPSMeter(default_window=30.0)
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=600, at_seconds=10.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=20.0,
    )
    assert snap.damage_out == 600
    assert snap.dps == 20.0


def test_heal_only_events():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.HEAL_OUT,
        amount=400, at_seconds=0.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.hps == 40.0
    assert snap.damage_out == 0


def test_damage_taken_dtps():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_TAKEN,
        amount=200, at_seconds=0.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.dtps == 20.0


def test_threat_combines_dmg_and_heal():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=100, at_seconds=0.0,
    )
    m.record(
        player_id="alice", kind=EventKind.HEAL_OUT,
        amount=50, at_seconds=0.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    # (100 + 50) / 10 = 15
    assert snap.threat == 15.0


def test_no_events_yields_zero():
    m = DPSMeter()
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.dps == 0.0


def test_zero_window_falls_back_to_default():
    m = DPSMeter(default_window=20.0)
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=0.0,
    )
    assert snap.window_seconds == 20.0


def test_party_rollup_sums_all_members():
    m = DPSMeter(default_window=10.0)
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=200, at_seconds=0.0,
    )
    m.record(
        player_id="bob", kind=EventKind.DAMAGE_OUT,
        amount=300, at_seconds=0.0,
    )
    rollup = m.party_rollup(
        member_ids=("alice", "bob"),
        now_seconds=10.0,
    )
    assert rollup.total_dps == 50.0
    assert len(rollup.members) == 2


def test_party_rollup_includes_zero_member():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=300, at_seconds=0.0,
    )
    rollup = m.party_rollup(
        member_ids=("alice", "bob"),
        now_seconds=10.0,
        window_seconds=10.0,
    )
    bob = next(
        s for s in rollup.members
        if s.player_id == "bob"
    )
    assert bob.dps == 0.0


def test_reset_player_clears_history():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=100, at_seconds=0.0,
    )
    assert m.reset(player_id="alice")
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.damage_out == 0


def test_reset_unknown_returns_false():
    m = DPSMeter()
    assert not m.reset(player_id="ghost")


def test_reset_all_clears_everyone():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=100, at_seconds=0.0,
    )
    m.record(
        player_id="bob", kind=EventKind.DAMAGE_OUT,
        amount=200, at_seconds=0.0,
    )
    n = m.reset_all()
    assert n == 2
    assert m.total_players_tracked() == 0


def test_future_events_excluded():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=500, at_seconds=100.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.damage_out == 0


def test_max_events_cap():
    """Ring buffer drops oldest events past max_events cap."""
    m = DPSMeter(max_events=3)
    for i in range(5):
        m.record(
            player_id="alice", kind=EventKind.DAMAGE_OUT,
            amount=10, at_seconds=float(i),
        )
    buf = m._events["alice"]
    assert len(buf) == 3


def test_default_window_constant():
    assert DEFAULT_WINDOW_SECONDS == 30.0


def test_sample_count_reported():
    m = DPSMeter()
    m.record(
        player_id="alice", kind=EventKind.DAMAGE_OUT,
        amount=10, at_seconds=0.0,
    )
    m.record(
        player_id="alice", kind=EventKind.HEAL_OUT,
        amount=5, at_seconds=1.0,
    )
    snap = m.snapshot_for(
        player_id="alice", now_seconds=10.0,
        window_seconds=10.0,
    )
    assert snap.sample_count == 2
