"""Tests for cartographer_guild."""
from __future__ import annotations

from server.cartographer_guild import CartographerGuild, GuildRank


def test_submit_happy():
    g = CartographerGuild()
    out = g.submit_map(
        player_id="alice", zone_id="ronfaure",
        quality_pct=80, submitted_at=10,
    )
    assert out.accepted is True
    assert out.payout > 0


def test_quality_below_50_rejected():
    g = CartographerGuild()
    out = g.submit_map(
        player_id="alice", zone_id="z",
        quality_pct=40, submitted_at=10,
    )
    assert out.accepted is False
    assert "50%" in out.reason


def test_blank_player_rejected():
    g = CartographerGuild()
    out = g.submit_map(
        player_id="", zone_id="z",
        quality_pct=80, submitted_at=10,
    )
    assert out.accepted is False


def test_blank_zone_rejected():
    g = CartographerGuild()
    out = g.submit_map(
        player_id="a", zone_id="",
        quality_pct=80, submitted_at=10,
    )
    assert out.accepted is False


def test_duplicate_zone_rejected():
    g = CartographerGuild()
    g.submit_map(
        player_id="alice", zone_id="z",
        quality_pct=80, submitted_at=10,
    )
    out = g.submit_map(
        player_id="alice", zone_id="z",
        quality_pct=90, submitted_at=20,
    )
    assert out.accepted is False
    assert "already" in out.reason


def test_apprentice_starting_rank():
    g = CartographerGuild()
    assert g.rank_for(player_id="ghost") == GuildRank.APPRENTICE


def test_journeyman_at_3():
    g = CartographerGuild()
    for i in range(3):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    assert g.rank_for(player_id="alice") == GuildRank.JOURNEYMAN


def test_expert_at_10():
    g = CartographerGuild()
    for i in range(10):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    assert g.rank_for(player_id="alice") == GuildRank.EXPERT


def test_master_at_25():
    g = CartographerGuild()
    for i in range(25):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    assert g.rank_for(player_id="alice") == GuildRank.MASTER


def test_grandmaster_at_50():
    g = CartographerGuild()
    for i in range(50):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    assert g.rank_for(player_id="alice") == GuildRank.GRANDMASTER


def test_promotion_flag_set_on_threshold():
    g = CartographerGuild()
    for i in range(2):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    out = g.submit_map(
        player_id="alice", zone_id="z3",
        quality_pct=80, submitted_at=3,
    )
    assert out.promoted is True
    assert out.new_rank == GuildRank.JOURNEYMAN


def test_no_promotion_mid_rank():
    g = CartographerGuild()
    g.submit_map(
        player_id="alice", zone_id="z1",
        quality_pct=80, submitted_at=1,
    )
    out = g.submit_map(
        player_id="alice", zone_id="z2",
        quality_pct=80, submitted_at=2,
    )
    assert out.promoted is False


def test_payout_scales_with_quality():
    g = CartographerGuild()
    out_low = g.submit_map(
        player_id="alice", zone_id="z1",
        quality_pct=50, submitted_at=10,
    )
    out_high = g.submit_map(
        player_id="alice", zone_id="z2",
        quality_pct=100, submitted_at=20,
    )
    assert out_high.payout > out_low.payout


def test_expert_payout_bonus():
    g = CartographerGuild()
    # rank up to expert first
    for i in range(10):
        g.submit_map(
            player_id="alice", zone_id=f"a{i}",
            quality_pct=100, submitted_at=i,
        )
    # the next submission should get expert bonus
    out = g.submit_map(
        player_id="alice", zone_id="bonus",
        quality_pct=100, submitted_at=100,
    )
    assert out.payout > 1000  # 100% quality + 10% bonus = 1100


def test_master_payout_bonus():
    g = CartographerGuild()
    for i in range(25):
        g.submit_map(
            player_id="alice", zone_id=f"a{i}",
            quality_pct=100, submitted_at=i,
        )
    out = g.submit_map(
        player_id="alice", zone_id="bonus",
        quality_pct=100, submitted_at=100,
    )
    # master = 20% bonus on a 1000-base = 1200
    assert out.payout == 1200


def test_total_paid_accumulates():
    g = CartographerGuild()
    g.submit_map(
        player_id="alice", zone_id="z1",
        quality_pct=100, submitted_at=10,
    )
    g.submit_map(
        player_id="alice", zone_id="z2",
        quality_pct=100, submitted_at=20,
    )
    assert g.total_paid_to(player_id="alice") == 2000


def test_submission_count():
    g = CartographerGuild()
    for i in range(7):
        g.submit_map(
            player_id="alice", zone_id=f"z{i}",
            quality_pct=80, submitted_at=i,
        )
    assert g.submission_count(player_id="alice") == 7


def test_five_guild_ranks():
    assert len(list(GuildRank)) == 5


def test_rejected_submission_no_payout():
    g = CartographerGuild()
    out = g.submit_map(
        player_id="alice", zone_id="z",
        quality_pct=20, submitted_at=10,
    )
    assert out.payout == 0
    assert g.total_paid_to(player_id="alice") == 0
