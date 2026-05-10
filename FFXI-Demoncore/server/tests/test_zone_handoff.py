"""Tests for zone_handoff."""
from __future__ import annotations

import pytest

from server.zone_handoff import (
    HandoffDecision,
    HandoffOutcome,
    PursuingNpc,
    ZoneBoundary,
    ZoneHandoffSystem,
    is_within_handoff_window,
    prefetch_eta_s,
)


def _bnd(
    bid: str = "bnd_a_b",
    a: str = "bastok_markets",
    b: str = "bastok_mines",
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
    half: float = 5.0,
    prefetch: float = 200.0,
    velocity: float = 18.0,
) -> ZoneBoundary:
    return ZoneBoundary(
        boundary_id=bid,
        zone_a_id=a,
        zone_b_id=b,
        transition_volume_min=(cx - half, cy - half, cz - half),
        transition_volume_max=(cx + half, cy + half, cz + half),
        prefetch_distance_m=prefetch,
        predicted_player_velocity_kmh=velocity,
    )


# ---- ZoneBoundary ----

def test_zone_boundary_dataclass_frozen():
    b = _bnd()
    with pytest.raises(Exception):
        b.zone_a_id = "x"  # type: ignore


def test_zone_boundary_default_prefetch_200m():
    b = ZoneBoundary(
        boundary_id="b", zone_a_id="a", zone_b_id="b",
        transition_volume_min=(0, 0, 0),
        transition_volume_max=(1, 1, 1),
    )
    assert b.prefetch_distance_m == 200.0


# ---- register_boundary ----

def test_register_boundary_adds():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd())
    assert sys.get_boundary("bnd_a_b").zone_a_id \
        == "bastok_markets"


def test_register_boundary_empty_id_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(ValueError):
        sys.register_boundary(_bnd(bid=""))


def test_register_boundary_same_zones_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(ValueError):
        sys.register_boundary(_bnd(a="z", b="z"))


def test_register_boundary_negative_prefetch_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(ValueError):
        sys.register_boundary(_bnd(prefetch=-1.0))


def test_register_boundary_inverted_volume_raises():
    sys = ZoneHandoffSystem()
    bad = ZoneBoundary(
        boundary_id="b", zone_a_id="a", zone_b_id="c",
        transition_volume_min=(10, 10, 10),
        transition_volume_max=(0, 0, 0),
    )
    with pytest.raises(ValueError):
        sys.register_boundary(bad)


def test_get_boundary_unknown_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(KeyError):
        sys.get_boundary("nope")


def test_all_boundaries_returns_all():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1"))
    sys.register_boundary(_bnd("b2", a="x", b="y"))
    assert len(sys.all_boundaries()) == 2


def test_boundaries_for_zone_filters():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1"))
    sys.register_boundary(_bnd("b2", a="other", b="zzz"))
    matched = sys.boundaries_for_zone("bastok_markets")
    assert len(matched) == 1
    assert matched[0].boundary_id == "b1"


# ---- is_within_handoff_window ----

def test_within_window_inside_volume():
    b = _bnd(cx=0, half=5.0)
    assert is_within_handoff_window((0.0, 0.0, 0.0), b)


def test_within_window_inside_prefetch_ring():
    b = _bnd(cx=0, half=5.0, prefetch=200.0)
    # 100 m from center -> within prefetch
    assert is_within_handoff_window((100.0, 0.0, 0.0), b)


def test_outside_window_when_too_far():
    b = _bnd(cx=0, half=5.0, prefetch=200.0)
    assert not is_within_handoff_window(
        (500.0, 0.0, 0.0), b,
    )


# ---- prefetch_eta_s ----

def test_prefetch_eta_zero_inside_volume():
    b = _bnd(cx=0, half=5.0)
    assert prefetch_eta_s((0.0, 0.0, 0.0), 18.0, b) == 0.0


def test_prefetch_eta_inf_when_velocity_zero():
    b = _bnd(cx=0, half=5.0)
    assert prefetch_eta_s(
        (100.0, 0.0, 0.0), 0.0, b,
    ) == float("inf")


def test_prefetch_eta_finite_when_moving():
    b = _bnd(cx=0, half=5.0)
    eta = prefetch_eta_s((100.0, 0.0, 0.0), 18.0, b)
    # 100 m at 5 m/s = 20 s
    assert eta == pytest.approx(20.0, rel=1e-3)


# ---- handoff_for ----

def test_handoff_for_no_action_when_far_outside():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", cx=10000.0))
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    assert len(decisions) == 1
    assert decisions[0].outcome == HandoffOutcome.NO_ACTION


def test_handoff_for_prefetch_inside_window():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", cx=100.0, prefetch=200.0))
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    assert decisions[0].outcome == HandoffOutcome.PREFETCH
    assert decisions[0].target_zone_id == "bastok_mines"


def test_handoff_for_cross_when_in_volume():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", cx=0.0, half=5.0))
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    assert decisions[0].outcome == HandoffOutcome.CROSS
    assert decisions[0].target_zone_id == "bastok_mines"


def test_handoff_for_hitch_when_prefetch_failed():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", cx=0.0, half=5.0))
    sys.set_prefetch_outcome("b1", success=False)
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    assert decisions[0].outcome == HandoffOutcome.HITCH
    assert decisions[0].hitch_ms == 200


def test_handoff_for_target_zone_b_when_starting_in_a():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", a="z_a", b="z_b"))
    d = sys.handoff_for((0.0, 0.0, 0.0), 18.0, "z_a")
    assert d[0].target_zone_id == "z_b"


def test_handoff_for_target_zone_a_when_starting_in_b():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", a="z_a", b="z_b"))
    d = sys.handoff_for((0.0, 0.0, 0.0), 18.0, "z_b")
    assert d[0].target_zone_id == "z_a"


def test_handoff_for_skips_unrelated_boundaries():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", a="bastok_markets", b="bastok_mines"))
    sys.register_boundary(_bnd("b2", a="zzz", b="qqq"))
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    # Only b1 touches bastok_markets.
    assert len(decisions) == 1
    assert decisions[0].boundary_id == "b1"


def test_handoff_for_multiple_boundaries_sorted():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("z2", a="bastok_markets", b="x"))
    sys.register_boundary(_bnd("a1", a="bastok_markets", b="y"))
    decisions = sys.handoff_for(
        (0.0, 0.0, 0.0), 18.0, "bastok_markets",
    )
    ids = [d.boundary_id for d in decisions]
    assert ids == sorted(ids)


def test_has_prefetched_flag_set_after_prefetch():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1", cx=100.0, prefetch=200.0))
    sys.handoff_for((0.0, 0.0, 0.0), 18.0, "bastok_markets")
    assert sys.has_prefetched("b1", "bastok_mines")


def test_has_prefetched_false_initially():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1"))
    assert not sys.has_prefetched("b1", "bastok_mines")


# ---- pursuing NPCs ----

def test_register_pursuing_npc_appends():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1"))
    npc = PursuingNpc(
        npc_id="fomor_1", session_id="s1", family="fomor",
        current_zone_id="bastok_markets",
        target_player_id="player_42",
    )
    sys.register_pursuing_npc("b1", npc)
    pursuing = sys.pursuing_npcs_to_handoff("b1")
    assert len(pursuing) == 1
    assert pursuing[0].npc_id == "fomor_1"


def test_pursuing_empty_for_new_boundary():
    sys = ZoneHandoffSystem()
    sys.register_boundary(_bnd("b1"))
    assert sys.pursuing_npcs_to_handoff("b1") == ()


def test_register_pursuing_npc_unknown_boundary_raises():
    sys = ZoneHandoffSystem()
    npc = PursuingNpc(
        npc_id="x", session_id="s", family="fomor",
        current_zone_id="z", target_player_id="p",
    )
    with pytest.raises(KeyError):
        sys.register_pursuing_npc("nope", npc)


def test_pursuing_npc_dataclass_frozen():
    npc = PursuingNpc(
        npc_id="x", session_id="s", family="fomor",
        current_zone_id="z", target_player_id="p",
    )
    with pytest.raises(Exception):
        npc.session_id = "z"  # type: ignore


# ---- HandoffDecision ----

def test_handoff_decision_dataclass_frozen():
    d = HandoffDecision(
        boundary_id="b", outcome=HandoffOutcome.NO_ACTION,
        target_zone_id="z", eta_seconds=10.0,
    )
    with pytest.raises(Exception):
        d.eta_seconds = 5.0  # type: ignore


def test_handoff_outcome_enum_complete():
    names = {o.value for o in HandoffOutcome}
    assert names == {"no_action", "prefetch", "cross", "hitch"}


def test_set_prefetch_outcome_unknown_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(KeyError):
        sys.set_prefetch_outcome("nope", True)


def test_pursuing_unknown_boundary_raises():
    sys = ZoneHandoffSystem()
    with pytest.raises(KeyError):
        sys.pursuing_npcs_to_handoff("nope")
