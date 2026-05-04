"""Tests for beastman missions."""
from __future__ import annotations

from server.beastman_missions import (
    BeastmanMissions,
    CityRank,
)


def _seed(b: BeastmanMissions):
    b.register_mission(
        mission_id="oz_1_1",
        city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=CityRank.ACOLYTE,
        label="Acolyte's Veil",
    )
    b.register_mission(
        mission_id="oz_2_1",
        city_id="oztroja",
        rank_required=CityRank.ACOLYTE,
        rewards_rank=CityRank.CHAMPION,
        label="Bishop's Trial",
    )
    b.register_mission(
        mission_id="oz_3_1",
        city_id="oztroja",
        rank_required=CityRank.CHAMPION,
        rewards_rank=CityRank.CAPTAIN,
        label="The Hollow Crown",
    )


def test_register_mission():
    b = BeastmanMissions()
    _seed(b)
    assert b.total_missions() == 3


def test_register_double_id_rejected():
    b = BeastmanMissions()
    _seed(b)
    res = b.register_mission(
        mission_id="oz_1_1",
        city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=CityRank.ACOLYTE,
        label="x",
    )
    assert res is None


def test_register_empty_id_rejected():
    b = BeastmanMissions()
    res = b.register_mission(
        mission_id="", city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=CityRank.ACOLYTE,
        label="x",
    )
    assert res is None


def test_register_empty_label_rejected():
    b = BeastmanMissions()
    res = b.register_mission(
        mission_id="x", city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=CityRank.ACOLYTE,
        label="",
    )
    assert res is None


def test_register_reward_below_required_rejected():
    b = BeastmanMissions()
    res = b.register_mission(
        mission_id="x", city_id="oztroja",
        rank_required=CityRank.CHAMPION,
        rewards_rank=CityRank.ACOLYTE,
        label="x",
    )
    assert res is None


def test_register_reward_equal_required_rejected():
    b = BeastmanMissions()
    res = b.register_mission(
        mission_id="x", city_id="oztroja",
        rank_required=CityRank.CHAMPION,
        rewards_rank=CityRank.CHAMPION,
        label="x",
    )
    assert res is None


def test_register_reward_none_allowed():
    b = BeastmanMissions()
    res = b.register_mission(
        mission_id="side_q",
        city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=None,
        label="Side Errand",
    )
    assert res is not None


def test_default_rank_is_newcomer():
    b = BeastmanMissions()
    assert b.rank_in(
        player_id="alice", city_id="oztroja",
    ) == CityRank.NEWCOMER


def test_start_mission_at_required_rank():
    b = BeastmanMissions()
    _seed(b)
    res = b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert res.accepted


def test_start_unknown_mission():
    b = BeastmanMissions()
    res = b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="ghost",
    )
    assert not res.accepted


def test_start_wrong_city_rejected():
    b = BeastmanMissions()
    _seed(b)
    res = b.start_mission(
        player_id="alice", city_id="palborough",
        mission_id="oz_1_1",
    )
    assert not res.accepted


def test_start_below_rank_rejected():
    b = BeastmanMissions()
    _seed(b)
    res = b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_2_1",
    )
    assert not res.accepted


def test_double_start_rejected():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    res = b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert not res.accepted


def test_complete_promotes_rank():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    res = b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert res.accepted
    assert res.new_rank == CityRank.ACOLYTE
    assert b.rank_in(
        player_id="alice", city_id="oztroja",
    ) == CityRank.ACOLYTE


def test_complete_no_reward_rank_unchanged():
    b = BeastmanMissions()
    b.register_mission(
        mission_id="errand", city_id="oztroja",
        rank_required=CityRank.NEWCOMER,
        rewards_rank=None,
        label="Errand",
    )
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="errand",
    )
    res = b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="errand",
    )
    assert res.accepted
    assert res.new_rank is None


def test_complete_already_done_rejected():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    res = b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert not res.accepted
    assert "already completed" in res.reason


def test_complete_wrong_active_rejected():
    b = BeastmanMissions()
    _seed(b)
    res = b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert not res.accepted


def test_per_city_isolation():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    # Different city — still NEWCOMER
    assert b.rank_in(
        player_id="alice", city_id="palborough",
    ) == CityRank.NEWCOMER


def test_full_chain_to_captain():
    b = BeastmanMissions()
    _seed(b)
    for mid in ("oz_1_1", "oz_2_1", "oz_3_1"):
        b.start_mission(
            player_id="alice", city_id="oztroja",
            mission_id=mid,
        )
        b.complete_mission(
            player_id="alice", city_id="oztroja",
            mission_id=mid,
        )
    assert b.rank_in(
        player_id="alice", city_id="oztroja",
    ) == CityRank.CAPTAIN


def test_completed_for_lookup():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    b.complete_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert b.completed_for(
        player_id="alice", city_id="oztroja",
    ) == ("oz_1_1",)


def test_in_progress_for():
    b = BeastmanMissions()
    _seed(b)
    b.start_mission(
        player_id="alice", city_id="oztroja",
        mission_id="oz_1_1",
    )
    assert b.in_progress_for(
        player_id="alice", city_id="oztroja",
    ) == "oz_1_1"
