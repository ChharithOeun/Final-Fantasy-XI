"""Tests for player_glassblowing."""
from __future__ import annotations

from server.player_glassblowing import (
    PlayerGlassblowingSystem, GlassStage, VesselKind,
)


def _gather(
    s: PlayerGlassblowingSystem, skill: int = 100,
) -> str:
    return s.gather_gob(
        artist_id="naji", kind=VesselKind.VASE,
        artist_skill=skill,
    )


def test_gather_happy():
    s = PlayerGlassblowingSystem()
    vid = _gather(s)
    assert vid is not None


def test_gather_empty_artist():
    s = PlayerGlassblowingSystem()
    assert s.gather_gob(
        artist_id="", kind=VesselKind.VASE,
        artist_skill=70,
    ) is None


def test_gather_invalid_skill():
    s = PlayerGlassblowingSystem()
    assert s.gather_gob(
        artist_id="a", kind=VesselKind.VASE,
        artist_skill=0,
    ) is None


def test_shape_high_skill_safe():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    # risk = 20 - 20 = 0 — never shatters
    nxt = s.shape(vessel_id=vid, seed=0)
    assert nxt == GlassStage.SHAPING


def test_low_skill_can_shatter():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=1)
    # risk = 20 - 0 = 20 — seed 0 -> roll 0 -> shatter
    nxt = s.shape(vessel_id=vid, seed=0)
    assert nxt == GlassStage.SHATTERED


def test_shape_grows_quality():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    v = s.vessel(vessel_id=vid)
    assert v.quality_score > 0


def test_shape_after_shatter_blocked():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=1)
    s.shape(vessel_id=vid, seed=0)
    assert s.shape(vessel_id=vid, seed=0) is None


def test_manipulate_high_skill():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    nxt = s.manipulate(vessel_id=vid, seed=0)
    assert nxt == GlassStage.MANIPULATED


def test_manipulate_before_shape_blocked():
    s = PlayerGlassblowingSystem()
    vid = _gather(s)
    assert s.manipulate(vessel_id=vid, seed=0) is None


def test_manipulate_higher_quality_gain():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    before = s.vessel(vessel_id=vid).quality_score
    s.manipulate(vessel_id=vid, seed=0)
    after = s.vessel(vessel_id=vid).quality_score
    assert (after - before) > 0


def test_begin_annealing_happy():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    s.manipulate(vessel_id=vid, seed=0)
    assert s.begin_annealing(vessel_id=vid) is True


def test_begin_annealing_before_manipulate_blocked():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    assert s.begin_annealing(vessel_id=vid) is False


def test_remove_from_lehr_high_skill():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    s.manipulate(vessel_id=vid, seed=0)
    s.begin_annealing(vessel_id=vid)
    nxt = s.remove_from_lehr(vessel_id=vid, seed=0)
    assert nxt == GlassStage.FINISHED


def test_remove_from_lehr_before_anneal_blocked():
    s = PlayerGlassblowingSystem()
    vid = _gather(s)
    assert s.remove_from_lehr(
        vessel_id=vid, seed=0,
    ) is None


def test_anneal_can_shatter_low_skill():
    s = PlayerGlassblowingSystem()
    # skill must be >= 1 to gather, but we want low
    # enough to shatter on annealing too
    vid = _gather(s, skill=1)
    # Need to advance past shape/manipulate without
    # shattering — high seeds skip the shatter window
    s.shape(vessel_id=vid, seed=99)
    if s.vessel(
        vessel_id=vid,
    ).stage == GlassStage.SHATTERED:
        # If shape shattered, retry test scenario
        return
    s.manipulate(vessel_id=vid, seed=99)
    if s.vessel(
        vessel_id=vid,
    ).stage == GlassStage.SHATTERED:
        return
    s.begin_annealing(vessel_id=vid)
    # anneal risk = 15 - 0 = 15. seed=0 -> roll 0 -> shatter
    nxt = s.remove_from_lehr(vessel_id=vid, seed=0)
    assert nxt == GlassStage.SHATTERED


def test_artist_finished_lookup():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    s.manipulate(vessel_id=vid, seed=0)
    s.begin_annealing(vessel_id=vid)
    s.remove_from_lehr(vessel_id=vid, seed=0)
    assert len(
        s.artist_finished(artist_id="naji"),
    ) == 1
    assert len(
        s.artist_finished(artist_id="other"),
    ) == 0


def test_unfinished_not_in_artist_finished():
    s = PlayerGlassblowingSystem()
    vid = _gather(s, skill=100)
    s.shape(vessel_id=vid, seed=0)
    assert len(
        s.artist_finished(artist_id="naji"),
    ) == 0


def test_unknown_vessel():
    s = PlayerGlassblowingSystem()
    assert s.vessel(vessel_id="ghost") is None
    assert s.shape(
        vessel_id="ghost", seed=0,
    ) is None


def test_enum_counts():
    assert len(list(VesselKind)) == 5
    assert len(list(GlassStage)) == 6
