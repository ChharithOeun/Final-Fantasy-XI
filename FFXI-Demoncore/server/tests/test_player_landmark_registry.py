"""Tests for player_landmark_registry."""
from __future__ import annotations

from server.player_landmark_registry import (
    PlayerLandmarkRegistrySystem,
    LandmarkState, LandmarkKind,
)


def _register(s: PlayerLandmarkRegistrySystem) -> str:
    return s.register(
        discoverer_id="alice",
        zone="ronfaure_west",
        name="Old Mossy Waystone",
        kind=LandmarkKind.WAYSTONE,
        x=120, y=340,
    )


def test_register_happy():
    s = PlayerLandmarkRegistrySystem()
    assert _register(s) is not None


def test_register_empty_zone_blocked():
    s = PlayerLandmarkRegistrySystem()
    assert s.register(
        discoverer_id="alice", zone="",
        name="x", kind=LandmarkKind.WAYSTONE,
        x=0, y=0,
    ) is None


def test_register_empty_name_blocked():
    s = PlayerLandmarkRegistrySystem()
    assert s.register(
        discoverer_id="alice", zone="z",
        name="", kind=LandmarkKind.WAYSTONE,
        x=0, y=0,
    ) is None


def test_confirm_happy():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    assert s.confirm(
        landmark_id=lid, witness_id="bob",
    ) is True


def test_confirm_discoverer_self_blocked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    assert s.confirm(
        landmark_id=lid, witness_id="alice",
    ) is False


def test_confirm_dup_blocked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    s.confirm(landmark_id=lid, witness_id="bob")
    assert s.confirm(
        landmark_id=lid, witness_id="bob",
    ) is False


def test_dispute_happy():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    assert s.dispute(
        landmark_id=lid, witness_id="cara",
    ) is True


def test_confirm_then_dispute_blocked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    s.confirm(landmark_id=lid, witness_id="bob")
    assert s.dispute(
        landmark_id=lid, witness_id="bob",
    ) is False


def test_three_confirms_verifies():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    for w in ("a", "b", "c"):
        s.confirm(landmark_id=lid, witness_id=w)
    assert s.landmark(
        landmark_id=lid,
    ).state == LandmarkState.VERIFIED


def test_three_disputes_disputes():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    for w in ("a", "b", "c"):
        s.dispute(landmark_id=lid, witness_id=w)
    assert s.landmark(
        landmark_id=lid,
    ).state == LandmarkState.DISPUTED


def test_mixed_majority_confirms():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    # 4 confirms vs 1 dispute = VERIFIED
    for w in ("a", "b", "c", "d"):
        s.confirm(landmark_id=lid, witness_id=w)
    s.dispute(landmark_id=lid, witness_id="e")
    assert s.landmark(
        landmark_id=lid,
    ).state == LandmarkState.VERIFIED


def test_one_confirm_unverified():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    s.confirm(landmark_id=lid, witness_id="a")
    assert s.landmark(
        landmark_id=lid,
    ).state == LandmarkState.UNVERIFIED


def test_confirmation_count_tracked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    s.confirm(landmark_id=lid, witness_id="a")
    s.confirm(landmark_id=lid, witness_id="b")
    assert s.landmark(
        landmark_id=lid,
    ).confirmations == 2


def test_dispute_count_tracked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    s.dispute(landmark_id=lid, witness_id="a")
    assert s.landmark(
        landmark_id=lid,
    ).disputes == 1


def test_re_register_clears_disputes():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    for w in ("a", "b", "c"):
        s.dispute(landmark_id=lid, witness_id=w)
    assert s.re_register(
        landmark_id=lid, discoverer_id="alice",
        x=200, y=400,
    ) is True
    spec = s.landmark(landmark_id=lid)
    assert spec.disputes == 0
    assert spec.x == 200


def test_re_register_wrong_discoverer_blocked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    for w in ("a", "b", "c"):
        s.dispute(landmark_id=lid, witness_id=w)
    assert s.re_register(
        landmark_id=lid, discoverer_id="bob",
        x=0, y=0,
    ) is False


def test_re_register_unverified_blocked():
    s = PlayerLandmarkRegistrySystem()
    lid = _register(s)
    assert s.re_register(
        landmark_id=lid, discoverer_id="alice",
        x=0, y=0,
    ) is False


def test_landmarks_in_zone():
    s = PlayerLandmarkRegistrySystem()
    s.register(
        discoverer_id="a", zone="ronfaure_west",
        name="L1", kind=LandmarkKind.WAYSTONE,
        x=0, y=0,
    )
    s.register(
        discoverer_id="a", zone="ronfaure_west",
        name="L2", kind=LandmarkKind.SHRINE,
        x=0, y=0,
    )
    s.register(
        discoverer_id="a", zone="zulkheim",
        name="L3", kind=LandmarkKind.WAYSTONE,
        x=0, y=0,
    )
    assert len(s.landmarks_in_zone(
        zone="ronfaure_west",
    )) == 2


def test_verified_in_zone_filters():
    s = PlayerLandmarkRegistrySystem()
    lid = s.register(
        discoverer_id="a", zone="ronfaure_west",
        name="L1", kind=LandmarkKind.WAYSTONE,
        x=0, y=0,
    )
    s.register(
        discoverer_id="a", zone="ronfaure_west",
        name="L2", kind=LandmarkKind.SHRINE,
        x=0, y=0,
    )
    for w in ("b", "c", "d"):
        s.confirm(landmark_id=lid, witness_id=w)
    assert len(s.verified_in_zone(
        zone="ronfaure_west",
    )) == 1


def test_unknown_landmark():
    s = PlayerLandmarkRegistrySystem()
    assert s.landmark(landmark_id="ghost") is None


def test_state_count():
    assert len(list(LandmarkState)) == 3


def test_kind_count():
    assert len(list(LandmarkKind)) == 7
