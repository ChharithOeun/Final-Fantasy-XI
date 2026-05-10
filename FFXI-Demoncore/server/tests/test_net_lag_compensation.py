"""Tests for net_lag_compensation."""
from __future__ import annotations

import pytest

from server.net_lag_compensation import (
    CheatSignal,
    ClaimResult,
    HISTORY_WINDOW_MS,
    HitClaim,
    MAX_MOVE_SPEED_MS,
    MAX_PING_MS,
    NetLagCompensationSystem,
    POSITION_TOLERANCE_CM,
    WeaponKind,
    weapon_min_interval_s,
    weapon_range_m,
)


def _claim(
    claimer="att",
    target="tgt",
    weapon=WeaponKind.SWORD,
    client_ms=1000,
    target_pos=(1.0, 0.0, 0.0),
    attacker_pos=(0.0, 0.0, 0.0),
    server_ms=1050,
    los=True,
):
    return HitClaim(
        claimer_player_id=claimer,
        target_entity_id=target,
        weapon_kind=weapon,
        claimed_at_client_ms=client_ms,
        claimed_target_pos_xyz=target_pos,
        claimed_attacker_pos_xyz=attacker_pos,
        server_received_ms=server_ms,
        has_line_of_sight=los,
    )


# ---- enum coverage ----

def test_weapon_kind_count():
    assert len(list(WeaponKind)) == 11


def test_weapon_has_bow():
    assert WeaponKind.BOW in list(WeaponKind)


def test_weapon_range_bow_long():
    assert weapon_range_m(WeaponKind.BOW) == 25.0


def test_weapon_range_h2h_short():
    assert weapon_range_m(WeaponKind.HAND_TO_HAND) == 2.0


def test_cheat_signal_count():
    # 8 documented signals.
    assert len(list(CheatSignal)) == 8


def test_cheat_signal_has_teleport():
    assert CheatSignal.TELEPORT_HACK in list(CheatSignal)


def test_weapon_min_interval_great_sword_slow():
    assert weapon_min_interval_s(WeaponKind.GREAT_SWORD) == 2.5


# ---- constants ----

def test_history_window_default():
    assert HISTORY_WINDOW_MS == 1000


def test_position_tolerance_default():
    assert POSITION_TOLERANCE_CM == 30.0


def test_max_ping_default():
    assert MAX_PING_MS == 500


def test_max_move_speed_default():
    assert MAX_MOVE_SPEED_MS == 15.0


# ---- register / prune ----

def test_register_history():
    s = NetLagCompensationSystem()
    s.register_history("p1", 1000, (0, 0, 0))
    assert s.history_size("p1") == 1


def test_register_empty_id_raises():
    s = NetLagCompensationSystem()
    with pytest.raises(ValueError):
        s.register_history("", 1000, (0, 0, 0))


def test_register_negative_ts_raises():
    s = NetLagCompensationSystem()
    with pytest.raises(ValueError):
        s.register_history("p1", -1, (0, 0, 0))


def test_prune_history_drops_old():
    s = NetLagCompensationSystem()
    s.register_history("p1", 0, (0, 0, 0))
    s.register_history("p1", 500, (0, 0, 0))
    s.register_history("p1", 2000, (0, 0, 0))
    removed = s.prune_history(2500)
    # cutoff=1500; 0 + 500 dropped.
    assert removed == 2


def test_rewound_position_missing_returns_none():
    s = NetLagCompensationSystem()
    assert s.rewound_position("nope", 1000) is None


def test_rewound_position_before_history_returns_none():
    s = NetLagCompensationSystem()
    s.register_history("p1", 2000, (5, 0, 0))
    assert s.rewound_position("p1", 1000) is None


def test_rewound_position_interpolates():
    s = NetLagCompensationSystem()
    s.register_history("p1", 1000, (0, 0, 0))
    s.register_history("p1", 1100, (10, 0, 0))
    pos = s.rewound_position("p1", 1050)
    assert pos is not None
    assert abs(pos[0] - 5.0) < 1e-6


# ---- can_attacker_reach ----

def test_can_attacker_reach_in_range():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    assert s.can_attacker_reach(
        "att", (2.5, 0, 0), WeaponKind.SWORD, 50,
    )


def test_can_attacker_reach_out_of_range():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    assert not s.can_attacker_reach(
        "att", (50, 0, 0), WeaponKind.SWORD, 50,
    )


def test_can_attacker_reach_unknown_attacker():
    s = NetLagCompensationSystem()
    assert not s.can_attacker_reach(
        "ghost", (1, 0, 0), WeaponKind.SWORD, 50,
    )


# ---- submit_claim (happy path) ----

def test_submit_claim_accepts_clean_hit():
    s = NetLagCompensationSystem()
    s.register_history("att", 950, (0, 0, 0))
    s.register_history("tgt", 950, (1, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(1, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
    ))
    assert r.accepted
    assert r.reason == "ok"


def test_submit_claim_returns_rewound_pos():
    s = NetLagCompensationSystem()
    s.register_history("att", 950, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim())
    assert r.rewound_target_pos_xyz == (1, 0, 0)


# ---- ping ----

def test_submit_claim_high_ping_rejected():
    s = NetLagCompensationSystem()
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim(
        client_ms=1000,
        server_ms=2000,  # 1000ms ping > 500ms cap.
    ))
    assert not r.accepted
    assert CheatSignal.PING_TOO_HIGH in r.cheat_signals


def test_submit_claim_negative_ping_rejected():
    s = NetLagCompensationSystem()
    s.register_history("tgt", 1000, (1, 0, 0))
    # Client-time newer than server-receive — impossible.
    r = s.submit_claim(_claim(
        client_ms=2000,
        server_ms=1900,
    ))
    assert not r.accepted
    assert CheatSignal.PING_TOO_HIGH in r.cheat_signals


# ---- rewind past history ----

def test_submit_claim_no_history():
    s = NetLagCompensationSystem()
    r = s.submit_claim(_claim())
    assert not r.accepted
    assert CheatSignal.REWIND_PAST_HISTORY in r.cheat_signals


# ---- position mismatch ----

def test_submit_claim_position_mismatch():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (5, 0, 0))
    # Client claims target was at (1,0,0); server has (5,0,0).
    r = s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(1, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
    ))
    assert CheatSignal.POSITION_MISMATCH in r.cheat_signals
    assert not r.accepted


# ---- teleport hack ----

def test_submit_claim_teleport_detected():
    s = NetLagCompensationSystem()
    # Attacker at origin 50ms ago.
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    # Claims to be 200m away now — impossible in 50ms.
    r = s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(1, 0, 0),
        attacker_pos=(200, 0, 0),
        server_ms=1050,
    ))
    assert CheatSignal.TELEPORT_HACK in r.cheat_signals


# ---- impossible reach ----

def test_submit_claim_out_of_range():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (10, 0, 0))
    # Sword range = 3m, but distance to target is 10m.
    r = s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(10, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
    ))
    assert CheatSignal.IMPOSSIBLE_REACH in r.cheat_signals
    assert not r.accepted


def test_oor_repeated_streak_flag():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (50, 0, 0))
    # 3 consecutive way-out-of-range hits.
    last = None
    for i in range(3):
        last = s.submit_claim(_claim(
            client_ms=1000 + i * 2000,
            target_pos=(50, 0, 0),
            attacker_pos=(0, 0, 0),
            server_ms=1050 + i * 2000,
        ))
        s.register_history(
            "att", 1050 + i * 2000, (0, 0, 0),
        )
        s.register_history(
            "tgt", 1050 + i * 2000, (50, 0, 0),
        )
    assert last is not None
    assert CheatSignal.OUT_OF_RANGE_REPEATED in last.cheat_signals


# ---- rapid fire ----

def test_rapid_fire_flag():
    s = NetLagCompensationSystem()
    s.register_history("att", 0, (0, 0, 0))
    s.register_history("tgt", 0, (1, 0, 0))
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(1, 0, 0),
        server_ms=1050,
    ))
    # Sword min interval = 1.0s; fire again after 100ms.
    s.register_history("att", 1100, (0, 0, 0))
    s.register_history("tgt", 1100, (1, 0, 0))
    r = s.submit_claim(_claim(
        client_ms=1100,
        target_pos=(1, 0, 0),
        server_ms=1150,
    ))
    assert CheatSignal.RAPID_FIRE_BEYOND_RATE in r.cheat_signals


# ---- LoS ----

def test_broken_los_blocks():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(1, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
        los=False,
    ))
    assert CheatSignal.BROKEN_LOS in r.cheat_signals
    assert not r.accepted


# ---- cheat log ----

def test_detect_cheats_aggregates():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (10, 0, 0))
    s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(10, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
    ))
    cheats = s.detect_cheats_for("att")
    assert CheatSignal.IMPOSSIBLE_REACH in cheats


def test_detect_cheats_empty_for_clean():
    s = NetLagCompensationSystem()
    s.register_history("att", 950, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    s.submit_claim(_claim())
    assert s.detect_cheats_for("att") == ()


def test_clear_cheat_log():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (10, 0, 0))
    s.submit_claim(_claim(
        client_ms=1000,
        target_pos=(10, 0, 0),
        attacker_pos=(0, 0, 0),
        server_ms=1050,
    ))
    s.clear_cheat_log("att")
    assert s.detect_cheats_for("att") == ()


# ---- effective range surfaced ----

def test_result_includes_effective_range():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim())
    # Sword range 3.0 + 1.0 tolerance.
    assert r.effective_range_m == 4.0


def test_result_includes_measured_distance():
    s = NetLagCompensationSystem()
    s.register_history("att", 1000, (0, 0, 0))
    s.register_history("tgt", 1000, (1, 0, 0))
    r = s.submit_claim(_claim(
        attacker_pos=(0, 0, 0), target_pos=(1, 0, 0),
    ))
    # rewound is (1,0,0) — distance 1.0.
    assert abs(r.measured_distance_m - 1.0) < 1e-6
