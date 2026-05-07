"""Tests for gearswap_gallery."""
from __future__ import annotations

from server.gearswap_gallery import (
    GearswapGallery, ReputationFilter, SortMode,
)
from server.gearswap_publisher import GearswapPublisher


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    p.set_mentor_status(
        author_id="rival", is_mentor=True,
        display_name="Rival",
    )
    p.set_mentor_status(
        author_id="infamous", is_mentor=True,
        display_name="Infamous",
    )
    pid_rdm_a = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith",
        lua_source="-- a", reputation_snapshot=80,
        hours_played_on_job=500, published_at=1000,
    )
    pid_rdm_b = p.publish(
        author_id="rival", job="RDM",
        addon_id="rdm_rival",
        lua_source="-- b", reputation_snapshot=20,
        hours_played_on_job=300, published_at=2000,
    )
    pid_rdm_c = p.publish(
        author_id="infamous", job="RDM",
        addon_id="rdm_infamous",
        lua_source="-- c", reputation_snapshot=-50,
        hours_played_on_job=400, published_at=3000,
    )
    pid_blm = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith",
        lua_source="-- d", reputation_snapshot=80,
        hours_played_on_job=300, published_at=1500,
    )
    g = GearswapGallery(_publisher=p)
    g.set_adopt_count(publish_id=pid_rdm_a, count=200)
    g.set_adopt_count(publish_id=pid_rdm_b, count=50)
    g.set_adopt_count(publish_id=pid_rdm_c, count=10)
    return p, g, {
        "rdm_a": pid_rdm_a, "rdm_b": pid_rdm_b,
        "rdm_c": pid_rdm_c, "blm": pid_blm,
    }


def test_browse_all_jobs_default():
    _, g, _ = _seed()
    out = g.browse()
    assert len(out) == 4


def test_browse_filtered_by_job():
    _, g, _ = _seed()
    out = g.browse(job="RDM")
    assert len(out) == 3
    for listing in out:
        assert listing.job == "RDM"


def test_browse_unknown_job_empty():
    _, g, _ = _seed()
    out = g.browse(job="GHOST")
    assert out == []


def test_browse_sort_newest():
    _, g, _ = _seed()
    out = g.browse(job="RDM", sort=SortMode.NEWEST)
    # rdm_c has published_at=3000 (newest)
    assert out[0].publish_id.endswith("3")  # 3rd published


def test_browse_sort_popular():
    _, g, _ = _seed()
    out = g.browse(job="RDM", sort=SortMode.POPULAR)
    # rdm_a has 200 adopts (highest)
    assert out[0].adopt_count == 200


def test_browse_sort_reputation():
    _, g, _ = _seed()
    out = g.browse(job="RDM", sort=SortMode.REPUTATION)
    # chharith (rep 80) first, infamous (-50) last
    assert out[0].reputation == 80
    assert out[-1].reputation == -50


def test_filter_positive_only_excludes_negatives():
    _, g, _ = _seed()
    out = g.browse(
        job="RDM",
        reputation_filter=ReputationFilter.POSITIVE_ONLY,
    )
    for listing in out:
        assert listing.reputation > 0


def test_filter_neutral_or_better():
    _, g, ids = _seed()
    out = g.browse(
        job="RDM",
        reputation_filter=ReputationFilter.NEUTRAL_OR_BETTER,
    )
    rep_seen = [l.reputation for l in out]
    # infamous (rep -50) excluded, others included
    assert -50 not in rep_seen
    assert 80 in rep_seen
    assert 20 in rep_seen


def test_filter_any_returns_negative():
    _, g, _ = _seed()
    out = g.browse(
        job="RDM",
        reputation_filter=ReputationFilter.ANY,
    )
    rep_seen = [l.reputation for l in out]
    assert -50 in rep_seen


def test_browse_zero_limit():
    _, g, _ = _seed()
    out = g.browse(limit=0)
    assert out == []


def test_browse_caps_at_limit():
    _, g, _ = _seed()
    out = g.browse(job="RDM", limit=2)
    assert len(out) == 2


def test_unlisted_excluded_from_browse():
    p, g, ids = _seed()
    p.unlist(author_id="chharith", publish_id=ids["rdm_a"])
    out = g.browse(job="RDM")
    pid_set = {l.publish_id for l in out}
    assert ids["rdm_a"] not in pid_set


def test_revoked_excluded_from_browse():
    p, g, ids = _seed()
    p.revoke(publish_id=ids["rdm_c"], reason="exploit")
    out = g.browse(job="RDM")
    pid_set = {l.publish_id for l in out}
    assert ids["rdm_c"] not in pid_set


def test_by_author_listing():
    _, g, _ = _seed()
    out = g.by_author_listing(author_id="chharith")
    assert len(out) == 2   # RDM + BLM


def test_by_author_unknown_empty():
    _, g, _ = _seed()
    assert g.by_author_listing(author_id="ghost") == []


def test_search_by_addon_id():
    _, g, _ = _seed()
    out = g.search(query="rdm_chharith")
    assert len(out) == 1
    assert out[0].addon_id == "rdm_chharith"


def test_search_by_author_name():
    _, g, _ = _seed()
    out = g.search(query="chharith")
    # 2 hits: RDM + BLM both authored by Chharith
    assert len(out) == 2


def test_search_by_job():
    _, g, _ = _seed()
    out = g.search(query="rdm")
    # all RDM entries match (3) + addon ids that contain "rdm"
    assert len(out) >= 3


def test_search_with_job_filter():
    _, g, _ = _seed()
    out = g.search(query="chharith", job="RDM")
    assert len(out) == 1


def test_search_blank_query_empty():
    _, g, _ = _seed()
    assert g.search(query="") == []


def test_search_no_match():
    _, g, _ = _seed()
    assert g.search(query="xyzzy") == []


def test_set_adopt_count_negative_blocked():
    _, g, ids = _seed()
    out = g.set_adopt_count(
        publish_id=ids["rdm_a"], count=-1,
    )
    assert out is False


def test_set_adopt_count_unknown_blocked():
    _, g, _ = _seed()
    out = g.set_adopt_count(publish_id="ghost", count=10)
    assert out is False


def test_three_sort_modes():
    assert len(list(SortMode)) == 3


def test_three_reputation_filters():
    assert len(list(ReputationFilter)) == 3
