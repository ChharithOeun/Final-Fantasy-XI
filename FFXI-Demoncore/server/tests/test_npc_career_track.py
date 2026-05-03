"""Tests for NPC career track."""
from __future__ import annotations

from server.npc_career_track import (
    CareerPath,
    DEFAULT_RANK_XP_STEP,
    DEFAULT_DEMOTION_FLOOR,
    MAX_RANK,
    NPCCareerTrack,
)


def test_register_npc_creates_profile():
    track = NPCCareerTrack()
    prof = track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    assert prof is not None
    assert prof.rank_index == 0
    rank = track.current_rank("cid")
    assert rank is not None
    assert rank.label == "apprentice"


def test_double_register_rejected():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    second = track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    assert second is None


def test_grant_xp_accumulates():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    track.grant_xp(npc_id="cid", amount=400)
    track.grant_xp(npc_id="cid", amount=300)
    assert track.profile("cid").xp_in_current_rank == 700


def test_grant_xp_unknown_returns_none():
    track = NPCCareerTrack()
    assert track.grant_xp(npc_id="ghost", amount=100) is None


def test_promotion_at_threshold():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    track.grant_xp(
        npc_id="cid", amount=DEFAULT_RANK_XP_STEP,
    )
    change = track.check_promotion(npc_id="cid")
    assert change is not None
    assert change.promotion
    assert change.old_rank.label == "apprentice"
    assert change.new_rank.label == "journeyman"


def test_promotion_below_threshold_returns_none():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    track.grant_xp(
        npc_id="cid", amount=DEFAULT_RANK_XP_STEP - 1,
    )
    assert track.check_promotion(npc_id="cid") is None


def test_promotion_at_max_rank_returns_none():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
        starting_rank=MAX_RANK,
    )
    track.grant_xp(
        npc_id="cid", amount=DEFAULT_RANK_XP_STEP * 5,
    )
    assert track.check_promotion(npc_id="cid") is None


def test_promotion_increments_counter():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.SMITH_LADDER,
    )
    track.grant_xp(
        npc_id="cid", amount=DEFAULT_RANK_XP_STEP,
    )
    track.check_promotion(npc_id="cid")
    assert track.profile("cid").times_promoted == 1


def test_penalize_drives_demotion():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
        starting_rank=5,    # captain
    )
    track.penalize(
        npc_id="cid", amount=abs(DEFAULT_DEMOTION_FLOOR) + 1,
    )
    change = track.check_demotion(npc_id="cid")
    assert change is not None
    assert not change.promotion
    assert change.old_rank.label == "captain"
    assert change.new_rank.label == "lieutenant"


def test_demotion_at_zero_rank_returns_none():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
    )
    track.penalize(
        npc_id="cid", amount=10000,
    )
    assert track.check_demotion(npc_id="cid") is None


def test_demotion_above_floor_returns_none():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
        starting_rank=3,
    )
    track.penalize(npc_id="cid", amount=100)
    assert track.check_demotion(npc_id="cid") is None


def test_demotion_resets_xp_pool():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
        starting_rank=3,
    )
    track.penalize(
        npc_id="cid", amount=abs(DEFAULT_DEMOTION_FLOOR) + 1,
    )
    track.check_demotion(npc_id="cid")
    assert track.profile("cid").xp_in_current_rank == 0
    assert track.profile("cid").times_demoted == 1


def test_change_path_resets():
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.KNIGHT_LADDER,
        starting_rank=4,
    )
    assert track.change_path(
        npc_id="cid", new_path=CareerPath.SCHOLAR_LADDER,
    )
    rank = track.current_rank("cid")
    assert rank.path == CareerPath.SCHOLAR_LADDER
    assert rank.label == "novice"


def test_change_path_unknown_returns_false():
    track = NPCCareerTrack()
    assert not track.change_path(
        npc_id="ghost", new_path=CareerPath.MERCHANT_LADDER,
    )


def test_starting_rank_bounded():
    track = NPCCareerTrack()
    prof = track.register_npc(
        npc_id="cid", path=CareerPath.PRIEST_LADDER,
        starting_rank=999,
    )
    assert prof.rank_index == MAX_RANK


def test_full_career_arc():
    """One NPC promoted three times then demoted."""
    track = NPCCareerTrack()
    track.register_npc(
        npc_id="cid", path=CareerPath.MERCHANT_LADDER,
    )
    for _ in range(3):
        track.grant_xp(
            npc_id="cid", amount=DEFAULT_RANK_XP_STEP,
        )
        c = track.check_promotion(npc_id="cid")
        assert c is not None
    assert track.profile("cid").rank_index == 3
    track.penalize(
        npc_id="cid",
        amount=abs(DEFAULT_DEMOTION_FLOOR) + 1,
    )
    c = track.check_demotion(npc_id="cid")
    assert c is not None
    assert track.profile("cid").rank_index == 2
    assert track.profile("cid").times_promoted == 3
    assert track.profile("cid").times_demoted == 1
