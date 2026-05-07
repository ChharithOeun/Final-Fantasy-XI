"""Tests for gearswap_author_dashboard."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_author_dashboard import (
    GearswapAuthorDashboard,
)
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import (
    GearswapRating, ReportReason, Thumb,
)
from server.gearswap_version_history import (
    GearswapVersionHistory,
)


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    pid_rdm = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- rdm v1",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    pid_blm = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith", lua_source="-- blm v1",
        reputation_snapshot=80, hours_played_on_job=300,
        published_at=2000,
    )
    a = GearswapAdopt(_publisher=p)
    r = GearswapRating()
    h = GearswapVersionHistory(_publisher=p)
    for pid in (pid_rdm, pid_blm):
        entry = p.lookup(publish_id=pid)
        h.seed_initial(
            publish_id=pid, lua_source=entry.lua_source,
            content_hash=entry.content_hash,
            published_at=entry.published_at,
        )
    # 5 adopts on RDM, 2 on BLM
    for player in ["b", "c", "d", "e", "f"]:
        a.adopt(
            player_id=player, publish_id=pid_rdm,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    for player in ["x", "y"]:
        a.adopt(
            player_id=player, publish_id=pid_blm,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    # 3 RDM upvotes, 1 RDM downvote, 1 BLM up
    r.rate(
        player_id="b", publish_id=pid_rdm, thumb=Thumb.UP,
    )
    r.rate(
        player_id="c", publish_id=pid_rdm, thumb=Thumb.UP,
    )
    r.rate(
        player_id="d", publish_id=pid_rdm, thumb=Thumb.UP,
    )
    r.rate(
        player_id="e", publish_id=pid_rdm, thumb=Thumb.DOWN,
    )
    r.rate(
        player_id="x", publish_id=pid_blm, thumb=Thumb.UP,
    )
    # 2 reports on BLM
    r.report(
        player_id="x", publish_id=pid_blm,
        reason=ReportReason.SPELLING, posted_at=3500,
    )
    r.report(
        player_id="y", publish_id=pid_blm,
        reason=ReportReason.OUTDATED, posted_at=3600,
    )
    d = GearswapAuthorDashboard(
        _publisher=p, _adopt=a, _rating=r, _history=h,
    )
    return p, a, r, h, d, pid_rdm, pid_blm


def test_for_author_happy():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    assert out is not None
    assert out.author_id == "chharith"
    assert out.author_display_name == "Chharith"


def test_for_author_unknown_none():
    _, _, _, _, d, _, _ = _seed()
    assert d.for_author(author_id="ghost", now=5000) is None


def test_for_author_blank_none():
    _, _, _, _, d, _, _ = _seed()
    assert d.for_author(author_id="", now=5000) is None


def test_total_publishes():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    assert out.total_publishes == 2


def test_live_publishes_excludes_unlisted():
    p, _, _, _, d, pid_rdm, _ = _seed()
    p.unlist(author_id="chharith", publish_id=pid_rdm)
    out = d.for_author(author_id="chharith", now=5000)
    assert out.total_publishes == 2
    assert out.live_publishes == 1


def test_total_adopts():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    assert out.total_adopts == 7   # 5 + 2


def test_net_thumbs():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    # RDM: +3 -1 = +2; BLM: +1 = +1; net = +3
    assert out.net_thumbs == 3


def test_total_reports():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    assert out.total_reports == 2


def test_adopts_in_window_inside():
    _, _, _, _, d, _, _ = _seed()
    # All adopts at t=3000; window covers (now=4000) - 7d
    out = d.for_author(
        author_id="chharith", now=4000, day_window=7,
    )
    assert out.adopts_in_window == 7


def test_adopts_in_window_outside():
    _, _, _, _, d, _, _ = _seed()
    # window=1 day; now=3000+86401 means cutoff is 1s
    # AFTER all the t=3000 adopts.
    out = d.for_author(
        author_id="chharith", now=3000 + 86401, day_window=1,
    )
    assert out.adopts_in_window == 0


def test_adopts_in_window_zero_window():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(
        author_id="chharith", now=5000, day_window=0,
    )
    assert out.adopts_in_window == 0


def test_per_lua_count():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    assert len(out.luas) == 2


def test_per_lua_sorted_by_adopts():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    # RDM (5) before BLM (2)
    assert out.luas[0].job == "RDM"
    assert out.luas[1].job == "BLM"


def test_per_lua_thumbs_filled():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    rdm = next(s for s in out.luas if s.job == "RDM")
    assert rdm.thumbs_up == 3
    assert rdm.thumbs_down == 1


def test_per_lua_report_count():
    _, _, _, _, d, _, _ = _seed()
    out = d.for_author(author_id="chharith", now=5000)
    blm = next(s for s in out.luas if s.job == "BLM")
    assert blm.report_count == 2


def test_per_lua_revision_count_after_push():
    p, _, _, h, d, pid_rdm, _ = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid_rdm,
        lua_source="-- rdm v2", notes="tuned",
        published_at=4000,
    )
    out = d.for_author(author_id="chharith", now=5000)
    rdm = next(s for s in out.luas if s.job == "RDM")
    assert rdm.revision_count == 2


def test_per_lua_status_field():
    p, _, _, _, d, pid_rdm, _ = _seed()
    p.unlist(author_id="chharith", publish_id=pid_rdm)
    out = d.for_author(author_id="chharith", now=5000)
    rdm = next(s for s in out.luas if s.job == "RDM")
    assert rdm.status == "unlisted"


def test_revoked_still_in_dashboard():
    """The author still sees their own revoked builds —
    so they know what got nuked and why."""
    p, _, _, _, d, pid_rdm, _ = _seed()
    p.revoke(publish_id=pid_rdm, reason="bad")
    out = d.for_author(author_id="chharith", now=5000)
    assert out.total_publishes == 2
    assert out.live_publishes == 1
