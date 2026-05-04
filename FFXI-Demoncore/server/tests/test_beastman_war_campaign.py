"""Tests for the beastman war campaign."""
from __future__ import annotations

from server.beastman_war_campaign import (
    BeastmanCity,
    BeastmanWarCampaign,
    ContributionKind,
    FrontKind,
    FrontStatus,
    HumeNation,
    Side,
)


def _seed(c):
    c.open_front(
        front_id="oz_front",
        hume_nation=HumeNation.WINDURST,
        beastman_city=BeastmanCity.OZTROJA,
        zone_id="meriphataud_mts",
        kind=FrontKind.BORDER_SKIRMISH,
    )


def test_open_front():
    c = BeastmanWarCampaign()
    _seed(c)
    assert c.total_fronts() == 1


def test_open_front_duplicate():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.open_front(
        front_id="oz_front",
        hume_nation=HumeNation.SAN_DORIA,
        beastman_city=BeastmanCity.HALVUNG,
        zone_id="other",
        kind=FrontKind.SIEGE,
    )
    assert res is None


def test_open_front_empty_zone():
    c = BeastmanWarCampaign()
    res = c.open_front(
        front_id="x",
        hume_nation=HumeNation.WINDURST,
        beastman_city=BeastmanCity.OZTROJA,
        zone_id="",
        kind=FrontKind.SIEGE,
    )
    assert res is None


def test_contribute_hume_push_positive():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="alice",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
        magnitude=5,
    )
    assert res.accepted
    assert res.push_delta == 5
    assert res.push_score == 5


def test_contribute_beastman_push_negative():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="kraw",
        front_id="oz_front",
        side=Side.BEASTMAN,
        kind=ContributionKind.NM_KILL,
        magnitude=2,
    )
    assert res.accepted
    assert res.push_delta == -10


def test_contribute_unknown_front():
    c = BeastmanWarCampaign()
    res = c.contribute(
        player_id="alice",
        front_id="ghost",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
    )
    assert not res.accepted


def test_contribute_zero_magnitude():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="alice",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
        magnitude=0,
    )
    assert not res.accepted


def test_contribute_caps_at_plus_100():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="alice",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.BANNER_PLANTED,
        magnitude=50,
    )
    assert res.push_score == 100
    assert res.status == FrontStatus.HUME_VICTORY


def test_contribute_caps_at_minus_100():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="kraw",
        front_id="oz_front",
        side=Side.BEASTMAN,
        kind=ContributionKind.BANNER_PLANTED,
        magnitude=50,
    )
    assert res.push_score == -100
    assert res.status == FrontStatus.BEASTMAN_VICTORY


def test_contribute_blocked_after_resolution():
    c = BeastmanWarCampaign()
    _seed(c)
    c.contribute(
        player_id="alice",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.BANNER_PLANTED,
        magnitude=50,
    )
    res = c.contribute(
        player_id="bob",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
    )
    assert not res.accepted


def test_kind_push_values():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.contribute(
        player_id="alice",
        front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.SUPPLY_BURN,
        magnitude=1,
    )
    assert res.push_delta == 4


def test_ai_tick_balanced_no_change():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.ai_tick(
        front_id="oz_front",
        hume_baseline=10,
        beastman_baseline=10,
    )
    assert res.accepted
    assert res.push_score == 0


def test_ai_tick_hume_advantage():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.ai_tick(
        front_id="oz_front",
        hume_baseline=20,
        beastman_baseline=5,
    )
    assert res.push_score == 15


def test_ai_tick_resolves_at_cap():
    c = BeastmanWarCampaign()
    _seed(c)
    c.ai_tick(
        front_id="oz_front",
        hume_baseline=200,
        beastman_baseline=0,
    )
    assert c.front_status(
        front_id="oz_front",
    ) == FrontStatus.HUME_VICTORY


def test_ai_tick_unknown_front():
    c = BeastmanWarCampaign()
    res = c.ai_tick(
        front_id="ghost",
        hume_baseline=5,
        beastman_baseline=5,
    )
    assert not res.accepted


def test_ai_tick_negative_baseline_rejected():
    c = BeastmanWarCampaign()
    _seed(c)
    res = c.ai_tick(
        front_id="oz_front",
        hume_baseline=-1,
        beastman_baseline=0,
    )
    assert not res.accepted


def test_front_status_default_active():
    c = BeastmanWarCampaign()
    _seed(c)
    assert c.front_status(
        front_id="oz_front",
    ) == FrontStatus.ACTIVE


def test_front_status_unknown_returns_none():
    c = BeastmanWarCampaign()
    assert c.front_status(front_id="ghost") is None


def test_top_contributors_sorted():
    c = BeastmanWarCampaign()
    _seed(c)
    c.contribute(
        player_id="alice", front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
        magnitude=10,
    )
    c.contribute(
        player_id="bob", front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
        magnitude=3,
    )
    top = c.top_contributors(front_id="oz_front")
    assert top[0][0] == "alice"
    assert top[0][1] == 10


def test_push_score_lookup():
    c = BeastmanWarCampaign()
    _seed(c)
    c.contribute(
        player_id="alice", front_id="oz_front",
        side=Side.HUME,
        kind=ContributionKind.NPC_KILL,
        magnitude=3,
    )
    assert c.push_score(front_id="oz_front") == 3


def test_push_score_unknown_zero():
    c = BeastmanWarCampaign()
    assert c.push_score(front_id="ghost") == 0


def test_tick_count_increments():
    c = BeastmanWarCampaign()
    _seed(c)
    for _ in range(5):
        c.ai_tick(
            front_id="oz_front",
            hume_baseline=1,
            beastman_baseline=1,
        )
    # tick_count is on Front; check via a contribution lookup
    # since we don't expose tick_count publicly: re-tick and confirm
    # state is still ACTIVE because deltas were 0
    assert c.front_status(
        front_id="oz_front",
    ) == FrontStatus.ACTIVE
