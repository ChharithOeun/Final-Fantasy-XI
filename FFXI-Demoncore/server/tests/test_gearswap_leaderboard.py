"""Tests for gearswap_leaderboard."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_leaderboard import (
    BoardKind, GearswapLeaderboard,
)
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import GearswapRating, Thumb


def _seed():
    p = GearswapPublisher()
    for aid, name in [
        ("chharith", "Chharith"),
        ("rival", "Rival"),
        ("infamous", "Infamous"),
    ]:
        p.set_mentor_status(
            author_id=aid, is_mentor=True, display_name=name,
        )

    pid_a = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- a",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    pid_b = p.publish(
        author_id="rival", job="RDM",
        addon_id="rdm_rival", lua_source="-- b",
        reputation_snapshot=20, hours_played_on_job=300,
        published_at=2000,
    )
    pid_c = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith", lua_source="-- c",
        reputation_snapshot=80, hours_played_on_job=300,
        published_at=1500,
    )
    pid_d = p.publish(
        author_id="infamous", job="DRG",
        addon_id="drg_infamous", lua_source="-- d",
        reputation_snapshot=-50, hours_played_on_job=400,
        published_at=3000,
    )
    a = GearswapAdopt(_publisher=p)
    r = GearswapRating()
    # adopters: Chharith RDM=3, Rival RDM=1, Chharith BLM=2,
    # Infamous DRG=5
    for player in ["b", "c", "d"]:
        a.adopt(
            player_id=player, publish_id=pid_a,
            mode=AdoptMode.USE_AS_IS, adopted_at=2500,
        )
    a.adopt(
        player_id="b", publish_id=pid_b,
        mode=AdoptMode.USE_AS_IS, adopted_at=2500,
    )
    for player in ["x", "y"]:
        a.adopt(
            player_id=player, publish_id=pid_c,
            mode=AdoptMode.USE_AS_IS, adopted_at=2500,
        )
    for player in ["q", "w", "e", "r", "t"]:
        a.adopt(
            player_id=player, publish_id=pid_d,
            mode=AdoptMode.USE_AS_IS, adopted_at=2500,
        )
    # net thumbs: Chharith RDM = 3 up, BLM = 2 up; Rival = 1
    # down; Infamous = 5 down
    for player in ["b", "c", "d"]:
        r.rate(
            player_id=player, publish_id=pid_a, thumb=Thumb.UP,
        )
    for player in ["x", "y"]:
        r.rate(
            player_id=player, publish_id=pid_c, thumb=Thumb.UP,
        )
    r.rate(
        player_id="b", publish_id=pid_b, thumb=Thumb.DOWN,
    )
    for player in ["q", "w", "e", "r", "t"]:
        r.rate(
            player_id=player, publish_id=pid_d, thumb=Thumb.DOWN,
        )
    lb = GearswapLeaderboard(
        _publisher=p, _adopt=a, _rating=r,
    )
    return p, a, r, lb


def test_by_adoptions_top():
    _, _, _, lb = _seed()
    out = lb.by_adoptions()
    # Chharith (3 RDM + 2 BLM = 5), Infamous (5),
    # Rival (1) — Chharith wins ties on author_id sort
    assert out[0].author_id == "chharith"
    assert out[0].score == 5
    assert out[0].rank == 1


def test_by_adoptions_filter_by_job():
    _, _, _, lb = _seed()
    out = lb.by_adoptions(job="RDM")
    assert len(out) == 2
    assert out[0].author_id == "chharith"
    assert out[0].score == 3


def test_by_adoptions_unknown_job_empty():
    _, _, _, lb = _seed()
    assert lb.by_adoptions(job="GHOST") == []


def test_by_upvotes_top():
    _, _, _, lb = _seed()
    out = lb.by_upvotes()
    # Chharith net +5 (3 RDM up + 2 BLM up)
    assert out[0].author_id == "chharith"
    assert out[0].score == 5


def test_by_upvotes_negative_score_present():
    _, _, _, lb = _seed()
    out = lb.by_upvotes()
    rival_score = next(
        e.score for e in out if e.author_id == "rival"
    )
    inf_score = next(
        e.score for e in out if e.author_id == "infamous"
    )
    assert rival_score == -1
    assert inf_score == -5


def test_by_upvotes_filter_by_job():
    _, _, _, lb = _seed()
    out = lb.by_upvotes(job="RDM")
    # Only authors with RDM publishes — chharith (+3),
    # rival (-1)
    ids = {e.author_id for e in out}
    assert ids == {"chharith", "rival"}


def test_by_job_required():
    _, _, _, lb = _seed()
    assert lb.by_job(job="") == []


def test_by_job_ranking():
    _, _, _, lb = _seed()
    out = lb.by_job(job="RDM")
    assert out[0].author_id == "chharith"
    assert out[1].author_id == "rival"


def test_zero_limit():
    _, _, _, lb = _seed()
    assert lb.by_adoptions(limit=0) == []
    assert lb.by_upvotes(limit=0) == []


def test_limit_caps():
    _, _, _, lb = _seed()
    out = lb.by_adoptions(limit=2)
    assert len(out) == 2


def test_publish_count_field():
    _, _, _, lb = _seed()
    out = lb.by_adoptions()
    chharith = next(e for e in out if e.author_id == "chharith")
    assert chharith.publish_count == 2  # RDM + BLM


def test_rank_starts_at_1():
    _, _, _, lb = _seed()
    out = lb.by_adoptions()
    assert out[0].rank == 1


def test_author_rank_known():
    _, _, _, lb = _seed()
    rk = lb.author_rank(
        author_id="chharith", kind=BoardKind.BY_ADOPTIONS,
    )
    assert rk == 1


def test_author_rank_unknown_none():
    _, _, _, lb = _seed()
    rk = lb.author_rank(
        author_id="ghost", kind=BoardKind.BY_ADOPTIONS,
    )
    assert rk is None


def test_author_rank_by_upvotes():
    _, _, _, lb = _seed()
    rk = lb.author_rank(
        author_id="infamous", kind=BoardKind.BY_UPVOTES,
    )
    # infamous has worst net, should be last (3rd)
    assert rk == 3


def test_author_rank_by_job_blank_none():
    _, _, _, lb = _seed()
    rk = lb.author_rank(
        author_id="chharith", kind=BoardKind.BY_JOB, job="",
    )
    assert rk is None


def test_author_rank_by_job():
    _, _, _, lb = _seed()
    rk = lb.author_rank(
        author_id="chharith", kind=BoardKind.BY_JOB, job="RDM",
    )
    assert rk == 1


def test_unlisted_excluded():
    p, _, _, lb = _seed()
    p.unlist(author_id="chharith", publish_id=p.by_author(
        author_id="chharith",
    )[0].publish_id)
    out = lb.by_adoptions()
    chharith = next(
        (e for e in out if e.author_id == "chharith"), None,
    )
    # chharith still has BLM published — should still appear
    assert chharith is not None


def test_revoked_publisher_drops_off_board():
    p, _, _, lb = _seed()
    # revoke ALL chharith publishes
    for entry in p.by_author(author_id="chharith"):
        p.revoke(publish_id=entry.publish_id, reason="bad")
    out = lb.by_adoptions()
    ids = {e.author_id for e in out}
    assert "chharith" not in ids


def test_three_board_kinds():
    assert len(list(BoardKind)) == 3
