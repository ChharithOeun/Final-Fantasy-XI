"""Tests for player_pottery."""
from __future__ import annotations

from server.player_pottery import (
    PlayerPotterySystem, PotteryStage, GlazeKind,
)


def _kiln(s: PlayerPotterySystem, cap: int = 5) -> str:
    s.register_kiln(kiln_id="bastok_kiln", capacity=cap)
    return "bastok_kiln"


def _throw(
    s: PlayerPotterySystem, skill: int = 80,
) -> str:
    return s.throw_vessel(
        potter_id="naji", title="Tea Bowl",
        potter_skill=skill,
    )


def test_register_kiln_happy():
    s = PlayerPotterySystem()
    assert s.register_kiln(
        kiln_id="k1", capacity=10,
    ) is True


def test_register_kiln_duplicate_blocked():
    s = PlayerPotterySystem()
    s.register_kiln(kiln_id="k1", capacity=10)
    assert s.register_kiln(
        kiln_id="k1", capacity=5,
    ) is False


def test_register_kiln_invalid_capacity():
    s = PlayerPotterySystem()
    assert s.register_kiln(
        kiln_id="k1", capacity=0,
    ) is False
    assert s.register_kiln(
        kiln_id="k2", capacity=100,
    ) is False


def test_throw_vessel_happy():
    s = PlayerPotterySystem()
    vid = _throw(s)
    assert vid is not None


def test_throw_invalid_skill():
    s = PlayerPotterySystem()
    assert s.throw_vessel(
        potter_id="x", title="t", potter_skill=0,
    ) is None


def test_throw_empty_title():
    s = PlayerPotterySystem()
    assert s.throw_vessel(
        potter_id="x", title="", potter_skill=50,
    ) is None


def test_dry_happy():
    s = PlayerPotterySystem()
    vid = _throw(s)
    assert s.dry(vessel_id=vid) is True
    assert s.vessel(
        vessel_id=vid,
    ).stage == PotteryStage.SHAPED


def test_dry_double_blocked():
    s = PlayerPotterySystem()
    vid = _throw(s)
    s.dry(vessel_id=vid)
    assert s.dry(vessel_id=vid) is False


def test_queue_for_bisque_happy():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s)
    s.dry(vessel_id=vid)
    assert s.queue_for_bisque(
        vessel_id=vid, kiln_id=kid,
    ) is True


def test_queue_before_dry_blocked():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s)
    assert s.queue_for_bisque(
        vessel_id=vid, kiln_id=kid,
    ) is False


def test_kiln_capacity_cap():
    s = PlayerPotterySystem()
    kid = _kiln(s, cap=2)
    v1 = _throw(s)
    v2 = _throw(s)
    v3 = _throw(s)
    s.dry(vessel_id=v1)
    s.dry(vessel_id=v2)
    s.dry(vessel_id=v3)
    s.queue_for_bisque(vessel_id=v1, kiln_id=kid)
    s.queue_for_bisque(vessel_id=v2, kiln_id=kid)
    assert s.queue_for_bisque(
        vessel_id=v3, kiln_id=kid,
    ) is False


def test_fire_bisque_happy():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    n = s.fire_bisque(kiln_id=kid, seed=99)
    assert n == 1
    assert s.vessel(
        vessel_id=vid,
    ).stage == PotteryStage.BISQUE_FIRED


def test_fire_bisque_low_skill_can_crack():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=1)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    # risk = 20 - 0 = 20, seed 0 -> roll 0 -> crack
    s.fire_bisque(kiln_id=kid, seed=0)
    assert s.vessel(
        vessel_id=vid,
    ).stage == PotteryStage.CRACKED


def test_fire_bisque_empty_blocked():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    assert s.fire_bisque(kiln_id=kid, seed=0) is None


def test_apply_glaze_happy():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    s.fire_bisque(kiln_id=kid, seed=99)
    assert s.apply_glaze(
        vessel_id=vid, glaze=GlazeKind.CELADON,
    ) is True


def test_apply_glaze_before_bisque_blocked():
    s = PlayerPotterySystem()
    vid = _throw(s)
    s.dry(vessel_id=vid)
    assert s.apply_glaze(
        vessel_id=vid, glaze=GlazeKind.CELADON,
    ) is False


def test_glaze_adds_quality():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    s.fire_bisque(kiln_id=kid, seed=99)
    before = s.vessel(vessel_id=vid).quality_score
    s.apply_glaze(
        vessel_id=vid, glaze=GlazeKind.RAKU,
    )
    after = s.vessel(vessel_id=vid).quality_score
    assert after - before == 40


def test_full_pipeline_to_complete():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    s.fire_bisque(kiln_id=kid, seed=99)
    s.apply_glaze(
        vessel_id=vid, glaze=GlazeKind.CELADON,
    )
    s.queue_for_glaze_fire(
        vessel_id=vid, kiln_id=kid,
    )
    n = s.fire_glaze(kiln_id=kid, seed=99)
    assert n == 1
    assert s.vessel(
        vessel_id=vid,
    ).stage == PotteryStage.COMPLETE


def test_queue_for_glaze_fire_before_glaze_blocked():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    s.fire_bisque(kiln_id=kid, seed=99)
    assert s.queue_for_glaze_fire(
        vessel_id=vid, kiln_id=kid,
    ) is False


def test_kiln_queued_clears_after_fire():
    s = PlayerPotterySystem()
    kid = _kiln(s)
    vid = _throw(s, skill=100)
    s.dry(vessel_id=vid)
    s.queue_for_bisque(vessel_id=vid, kiln_id=kid)
    assert len(s.kiln_queued(kiln_id=kid)) == 1
    s.fire_bisque(kiln_id=kid, seed=99)
    assert len(s.kiln_queued(kiln_id=kid)) == 0


def test_unknown_vessel():
    s = PlayerPotterySystem()
    assert s.vessel(vessel_id="ghost") is None


def test_unknown_kiln():
    s = PlayerPotterySystem()
    assert s.kiln_queued(kiln_id="ghost") == []


def test_enum_counts():
    assert len(list(PotteryStage)) == 6
    assert len(list(GlazeKind)) == 5
