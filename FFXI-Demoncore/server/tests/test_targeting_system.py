"""Tests for targeting_system."""
from __future__ import annotations

import pytest

from server.targeting_system import (
    AOEPlacement,
    TargetCandidate,
    TargetFilter,
    TargeterState,
    TargetingMode,
    TargetingSystem,
)


def _cand(
    tid="m1",
    kind=TargetFilter.ENEMY,
    dist=10.0,
    screen=100.0,
    alive=True,
    loaded=True,
):
    return TargetCandidate(
        target_id=tid,
        filter_kind=kind,
        distance_m=dist,
        screen_distance_px=screen,
        is_alive=alive,
        is_loaded=loaded,
    )


# ---- enums ----

def test_targeting_mode_count_eight():
    assert len(list(TargetingMode)) == 8


def test_target_filter_count_six():
    assert len(list(TargetFilter)) == 6


def test_targeting_mode_has_aoe_ground_place():
    assert TargetingMode.AOE_GROUND_PLACE in list(TargetingMode)


def test_target_filter_has_nm_and_boss():
    kinds = list(TargetFilter)
    assert TargetFilter.NM in kinds
    assert TargetFilter.BOSS in kinds


# ---- register ----

def test_register_targeter():
    s = TargetingSystem()
    st = s.register_targeter("p1")
    assert st.player_id == "p1"
    assert s.targeter_count() == 1


def test_register_empty_id_raises():
    s = TargetingSystem()
    with pytest.raises(ValueError):
        s.register_targeter("")


def test_register_duplicate_raises():
    s = TargetingSystem()
    s.register_targeter("p1")
    with pytest.raises(ValueError):
        s.register_targeter("p1")


def test_state_of_unknown_raises():
    s = TargetingSystem()
    with pytest.raises(KeyError):
        s.state_of("p1")


# ---- mode ----

def test_set_mode_persists():
    s = TargetingSystem()
    s.register_targeter("p1")
    st = s.set_mode("p1", TargetingMode.TAB_TARGET_NEAREST)
    assert st.mode == TargetingMode.TAB_TARGET_NEAREST


def test_set_mode_lock_sets_locked_flag():
    s = TargetingSystem()
    s.register_targeter("p1")
    st = s.set_mode("p1", TargetingMode.TAB_TARGET_LOCK)
    assert st.locked is True


def test_set_mode_none_clears_lock():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.set_mode("p1", TargetingMode.TAB_TARGET_LOCK)
    st = s.set_mode("p1", TargetingMode.NONE)
    assert st.locked is False


# ---- tab ----

def test_tab_picks_closest_to_screen_center():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", screen=200),
        _cand("b", screen=50),
        _cand("c", screen=300),
    ]
    nxt = s.tab_target("p1", "", cands, 50.0)
    assert nxt == "b"


def test_tab_cycles_through_eligible():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", screen=10),
        _cand("b", screen=20),
        _cand("c", screen=30),
    ]
    n1 = s.tab_target("p1", "", cands, 50.0)
    n2 = s.tab_target("p1", n1, cands, 50.0)
    n3 = s.tab_target("p1", n2, cands, 50.0)
    n4 = s.tab_target("p1", n3, cands, 50.0)
    assert (n1, n2, n3, n4) == ("a", "b", "c", "a")


def test_tab_filters_by_radius():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", dist=5),
        _cand("b", dist=100),
    ]
    nxt = s.tab_target("p1", "", cands, 10.0)
    assert nxt == "a"


def test_tab_filters_by_filter_kind():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", kind=TargetFilter.FRIENDLY),
        _cand("b", kind=TargetFilter.ENEMY, screen=50),
    ]
    nxt = s.tab_target("p1", "", cands, 50.0)
    assert nxt == "b"


def test_tab_skips_dead_or_unloaded():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", alive=False),
        _cand("b", loaded=False),
        _cand("c", screen=100),
    ]
    nxt = s.tab_target("p1", "", cands, 50.0)
    assert nxt == "c"


def test_tab_no_eligible_returns_empty():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [_cand("a", dist=100)]
    nxt = s.tab_target("p1", "", cands, 10.0)
    assert nxt == ""


def test_tab_negative_radius_raises():
    s = TargetingSystem()
    s.register_targeter("p1")
    with pytest.raises(ValueError):
        s.tab_target("p1", "", [], -1.0)


def test_friendly_tab_only_friendlies():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [
        _cand("a", kind=TargetFilter.ENEMY),
        _cand("b", kind=TargetFilter.FRIENDLY, screen=50),
    ]
    nxt = s.friendly_tab("p1", "", cands, 50.0)
    assert nxt == "b"


# ---- lock ----

def test_lock_target_sets_locked():
    s = TargetingSystem()
    s.register_targeter("p1")
    st = s.lock_target("p1", "m1")
    assert st.current_target == "m1"
    assert st.locked is True
    assert s.is_locked("p1")


def test_release_lock_clears_flag():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.lock_target("p1", "m1")
    s.release_lock("p1")
    assert not s.is_locked("p1")


# ---- range ----

def test_out_of_range_true_when_far():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [_cand("m1", dist=20)]
    assert s.out_of_range("p1", "m1", cands, 10.0)


def test_out_of_range_false_when_close():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [_cand("m1", dist=5)]
    assert not s.out_of_range("p1", "m1", cands, 10.0)


def test_out_of_range_dead_target():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [_cand("m1", dist=5, alive=False)]
    assert s.out_of_range("p1", "m1", cands, 10.0)


def test_out_of_range_unloaded_target():
    s = TargetingSystem()
    s.register_targeter("p1")
    cands = [_cand("m1", dist=5, loaded=False)]
    assert s.out_of_range("p1", "m1", cands, 10.0)


def test_out_of_range_unknown_target():
    s = TargetingSystem()
    s.register_targeter("p1")
    assert s.out_of_range("p1", "ghost", [], 10.0)


# ---- AOE ----

def test_place_aoe_in_range_valid():
    s = TargetingSystem()
    s.register_targeter("p1")
    p = s.place_aoe(
        "p1", (3.0, 0.0, 4.0), 10.0,
        player_pos=(0.0, 0.0, 0.0),
        valid_surfaces_predicate=lambda pos: True,
    )
    assert p.is_valid
    assert p.reason == "ok"


def test_place_aoe_out_of_range():
    s = TargetingSystem()
    s.register_targeter("p1")
    p = s.place_aoe(
        "p1", (30.0, 0.0, 40.0), 10.0,
        player_pos=(0.0, 0.0, 0.0),
        valid_surfaces_predicate=lambda pos: True,
    )
    assert not p.is_valid
    assert p.reason == "out_of_range"


def test_place_aoe_invalid_surface():
    s = TargetingSystem()
    s.register_targeter("p1")
    p = s.place_aoe(
        "p1", (3.0, 0.0, 4.0), 10.0,
        player_pos=(0.0, 0.0, 0.0),
        valid_surfaces_predicate=lambda pos: False,
    )
    assert not p.is_valid
    assert p.reason == "invalid_surface"


def test_place_aoe_negative_range_raises():
    s = TargetingSystem()
    s.register_targeter("p1")
    with pytest.raises(ValueError):
        s.place_aoe(
            "p1", (0.0, 0.0, 0.0), -1.0,
            player_pos=(0.0, 0.0, 0.0),
            valid_surfaces_predicate=lambda pos: True,
        )


# ---- cone ----

def test_cone_includes_in_front():
    s = TargetingSystem()
    cands = [_cand("a"), _cand("b")]
    positions = {
        "a": (0.0, 0.0, 5.0),
        "b": (5.0, 0.0, 0.0),
    }
    out = s.cone_targets(
        player_pos=(0.0, 0.0, 0.0),
        player_facing_deg=0.0,  # facing +Z
        arc_deg=60.0,
        max_range_m=10.0,
        candidates=cands,
        candidate_positions=positions,
    )
    assert "a" in out
    assert "b" not in out


def test_cone_excludes_out_of_range():
    s = TargetingSystem()
    cands = [_cand("a")]
    positions = {"a": (0.0, 0.0, 50.0)}
    out = s.cone_targets(
        player_pos=(0.0, 0.0, 0.0),
        player_facing_deg=0.0,
        arc_deg=120.0,
        max_range_m=10.0,
        candidates=cands,
        candidate_positions=positions,
    )
    assert out == ()


def test_cone_invalid_arc_raises():
    s = TargetingSystem()
    with pytest.raises(ValueError):
        s.cone_targets(
            player_pos=(0.0, 0.0, 0.0),
            player_facing_deg=0.0,
            arc_deg=400.0,
            max_range_m=10.0,
            candidates=[],
            candidate_positions={},
        )


def test_cone_skips_dead():
    s = TargetingSystem()
    cands = [_cand("a", alive=False)]
    positions = {"a": (0.0, 0.0, 5.0)}
    out = s.cone_targets(
        player_pos=(0.0, 0.0, 0.0),
        player_facing_deg=0.0,
        arc_deg=180.0,
        max_range_m=10.0,
        candidates=cands,
        candidate_positions=positions,
    )
    assert out == ()


# ---- sub-target ----

def test_set_sub_target_persists():
    s = TargetingSystem()
    s.register_targeter("p1")
    st = s.set_sub_target("p1", "m2")
    assert st.sub_target == "m2"


def test_clear_sub_target():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.set_sub_target("p1", "m2")
    st = s.clear_sub_target("p1")
    assert st.sub_target == ""


def test_clear_target_resets_all():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.lock_target("p1", "m1")
    s.set_sub_target("p1", "m2")
    st = s.clear_target("p1")
    assert st.current_target == ""
    assert st.sub_target == ""
    assert st.locked is False


# ---- target-of-target ----

def test_target_of_target_lookup():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.update_target_of_target("m1", "tank")
    assert s.target_of_target("p1", "m1") == "tank"


def test_target_of_target_missing_returns_empty():
    s = TargetingSystem()
    s.register_targeter("p1")
    assert s.target_of_target("p1", "m1") == ""


def test_target_of_target_overwrite():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.update_target_of_target("m1", "tank")
    s.update_target_of_target("m1", "healer")
    assert s.target_of_target("p1", "m1") == "healer"


def test_lock_persists_through_set_mode_change():
    s = TargetingSystem()
    s.register_targeter("p1")
    s.lock_target("p1", "boss")
    s.set_mode("p1", TargetingMode.AOE_GROUND_PLACE)
    # set_mode to a non-NONE non-LOCK doesn't auto-clear.
    assert s.is_locked("p1")
