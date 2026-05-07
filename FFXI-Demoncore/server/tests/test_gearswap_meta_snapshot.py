"""Tests for gearswap_meta_snapshot."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_meta_snapshot import (
    GearswapMetaSnapshot,
)
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import GearswapRating, Thumb


def _seed():
    p = GearswapPublisher()
    for aid, name in [
        ("chharith", "Chharith"),
        ("rival", "Rival"),
        ("dom", "DominantAuthor"),
    ]:
        p.set_mentor_status(
            author_id=aid, is_mentor=True, display_name=name,
        )
    pid_rdm_a = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- a",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    pid_rdm_b = p.publish(
        author_id="rival", job="RDM",
        addon_id="rdm_rival", lua_source="-- b",
        reputation_snapshot=20, hours_played_on_job=300,
        published_at=2000,
    )
    pid_blm_dom = p.publish(
        author_id="dom", job="BLM",
        addon_id="blm_dom", lua_source="-- d",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1500,
    )
    pid_blm_b = p.publish(
        author_id="rival", job="BLM",
        addon_id="blm_rival", lua_source="-- e",
        reputation_snapshot=20, hours_played_on_job=300,
        published_at=2500,
    )
    a = GearswapAdopt(_publisher=p)
    r = GearswapRating()
    # RDM: spread 6 / 4 = healthy
    for player in ["b", "c", "d", "e", "f", "g"]:
        a.adopt(
            player_id=player, publish_id=pid_rdm_a,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    for player in ["x", "y", "z", "w"]:
        a.adopt(
            player_id=player, publish_id=pid_rdm_b,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    # BLM: 18 / 2 = concentrated (90%)
    for i in range(18):
        a.adopt(
            player_id=f"blm{i}", publish_id=pid_blm_dom,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    for player in ["q1", "q2"]:
        a.adopt(
            player_id=player, publish_id=pid_blm_b,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    # Some thumbs
    for player in ["t1", "t2", "t3"]:
        r.rate(
            player_id=player, publish_id=pid_rdm_a,
            thumb=Thumb.UP,
        )
    m = GearswapMetaSnapshot(
        _publisher=p, _adopt=a, _rating=r,
    )
    return p, a, r, m, {
        "rdm_a": pid_rdm_a, "rdm_b": pid_rdm_b,
        "blm_dom": pid_blm_dom, "blm_b": pid_blm_b,
    }


def test_take_snapshot_returns_meta():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    assert snap.snapshot_at == 5000
    assert len(snap.jobs) == 2  # RDM + BLM


def test_take_snapshot_persisted():
    _, _, _, m, _ = _seed()
    m.take_snapshot(now=5000)
    assert m.total_snapshots() == 1
    assert m.latest() is not None


def test_latest_returns_most_recent():
    _, _, _, m, _ = _seed()
    m.take_snapshot(now=5000)
    m.take_snapshot(now=6000)
    assert m.latest().snapshot_at == 6000


def test_latest_none_when_no_snapshots():
    _, _, _, m, _ = _seed()
    assert m.latest() is None


def test_meta_for_job_rdm_healthy():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    rdm = m.meta_for_job(snap, job="RDM")
    assert rdm is not None
    assert rdm.publish_count == 2
    assert rdm.total_adopters == 10
    assert rdm.top_adopt_count == 6
    assert rdm.health == "healthy"


def test_meta_for_job_blm_concentrated():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    blm = m.meta_for_job(snap, job="BLM")
    assert blm.health == "concentrated"
    assert blm.top_share > 0.6


def test_meta_for_job_top_publish_correct():
    _, _, _, m, ids = _seed()
    snap = m.take_snapshot(now=5000)
    rdm = m.meta_for_job(snap, job="RDM")
    assert rdm.top_publish_id == ids["rdm_a"]
    assert rdm.top_author_display_name == "Chharith"


def test_meta_for_job_unknown_none():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    assert m.meta_for_job(snap, job="GHOST") is None


def test_quiet_health_under_10_adopts():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    pid = p.publish(
        author_id="chharith", job="DRG",
        addon_id="drg_x", lua_source="-- d",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    a = GearswapAdopt(_publisher=p)
    a.adopt(
        player_id="x", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    r = GearswapRating()
    m = GearswapMetaSnapshot(
        _publisher=p, _adopt=a, _rating=r,
    )
    snap = m.take_snapshot(now=3000)
    drg = m.meta_for_job(snap, job="DRG")
    assert drg.health == "quiet"


def test_avg_net_thumbs():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    rdm = m.meta_for_job(snap, job="RDM")
    # rdm_a has 3 ups, rdm_b has 0 → mean = 1.5
    assert rdm.avg_net_thumbs == 1.5


def test_unlisted_excluded():
    p, _, _, m, ids = _seed()
    p.unlist(author_id="chharith", publish_id=ids["rdm_a"])
    snap = m.take_snapshot(now=5000)
    rdm = m.meta_for_job(snap, job="RDM")
    # rdm_a removed; only rdm_b counts
    assert rdm.publish_count == 1
    assert rdm.top_publish_id == ids["rdm_b"]


def test_revoked_excluded():
    p, _, _, m, ids = _seed()
    p.revoke(publish_id=ids["rdm_a"], reason="bad")
    snap = m.take_snapshot(now=5000)
    rdm = m.meta_for_job(snap, job="RDM")
    assert rdm.publish_count == 1


def test_history_returns_list():
    _, _, _, m, _ = _seed()
    m.take_snapshot(now=1000)
    m.take_snapshot(now=2000)
    m.take_snapshot(now=3000)
    out = m.history()
    assert len(out) == 3


def test_history_zero_limit():
    _, _, _, m, _ = _seed()
    m.take_snapshot(now=1000)
    assert m.history(limit=0) == []


def test_history_limit_caps():
    _, _, _, m, _ = _seed()
    for t in [1000, 2000, 3000, 4000]:
        m.take_snapshot(now=t)
    assert len(m.history(limit=2)) == 2


def test_history_cap_at_200():
    _, _, _, m, _ = _seed()
    for t in range(250):
        m.take_snapshot(now=t)
    assert m.total_snapshots() == 200


def test_jobs_sorted_alphabetically():
    _, _, _, m, _ = _seed()
    snap = m.take_snapshot(now=5000)
    job_names = [j.job for j in snap.jobs]
    assert job_names == sorted(job_names)
