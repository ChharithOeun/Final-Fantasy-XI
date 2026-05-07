"""Tests for gearswap_trending."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import Thumb
from server.gearswap_trending import GearswapTrending


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    p.set_mentor_status(
        author_id="rookie", is_mentor=True,
        display_name="Rookie",
    )
    pid_old = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- old",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    pid_new = p.publish(
        author_id="rookie", job="RDM",
        addon_id="rdm_rookie", lua_source="-- new",
        reputation_snapshot=10, hours_played_on_job=300,
        published_at=900_000,
    )
    a = GearswapAdopt(_publisher=p)
    t = GearswapTrending(_publisher=p, _adopt=a)
    return p, a, t, pid_old, pid_new


def test_record_thumb_happy():
    _, _, t, pid_old, _ = _seed()
    out = t.record_thumb(
        player_id="bob", publish_id=pid_old,
        thumb=Thumb.UP, posted_at=1000,
    )
    assert out is True


def test_record_thumb_blank_blocked():
    _, _, t, pid_old, _ = _seed()
    assert t.record_thumb(
        player_id="", publish_id=pid_old,
        thumb=Thumb.UP, posted_at=1000,
    ) is False


def test_record_thumb_unknown_publish():
    _, _, t, _, _ = _seed()
    out = t.record_thumb(
        player_id="bob", publish_id="ghost",
        thumb=Thumb.UP, posted_at=1000,
    )
    assert out is False


def test_score_for_recent_adopts():
    _, a, t, _, pid_new = _seed()
    a.adopt(
        player_id="bob", publish_id=pid_new,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    a.adopt(
        player_id="cara", publish_id=pid_new,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    score = t.score_for(
        publish_id=pid_new, now=1_000_100, window_days=7,
    )
    assert score == 2  # 2 adopts, no thumbs


def test_score_for_recent_thumbs_weighted_2x():
    _, _, t, _, pid_new = _seed()
    t.record_thumb(
        player_id="bob", publish_id=pid_new,
        thumb=Thumb.UP, posted_at=1_000_000,
    )
    score = t.score_for(
        publish_id=pid_new, now=1_000_100, window_days=7,
    )
    assert score == 2  # 1 up * 2


def test_score_for_downs_subtract():
    _, _, t, _, pid_new = _seed()
    t.record_thumb(
        player_id="bob", publish_id=pid_new,
        thumb=Thumb.UP, posted_at=1_000_000,
    )
    t.record_thumb(
        player_id="cara", publish_id=pid_new,
        thumb=Thumb.DOWN, posted_at=1_000_000,
    )
    score = t.score_for(
        publish_id=pid_new, now=1_000_100, window_days=7,
    )
    assert score == 1  # 1*2 - 1


def test_score_for_old_events_excluded():
    _, a, t, pid_old, _ = _seed()
    a.adopt(
        player_id="bob", publish_id=pid_old,
        mode=AdoptMode.USE_AS_IS, adopted_at=1000,
    )
    # window: 7 days back from 1_000_000
    score = t.score_for(
        publish_id=pid_old, now=1_000_000, window_days=7,
    )
    assert score == 0


def test_score_for_zero_window():
    _, _, t, pid_new, _ = _seed()
    assert t.score_for(
        publish_id=pid_new, now=1_000_000, window_days=0,
    ) == 0


def test_top_excludes_quiet_publishes():
    _, _, t, _, _ = _seed()
    # Neither has activity — both should drop off
    out = t.top(now=1_000_000, window_days=7)
    assert out == []


def test_top_orders_by_score():
    _, a, t, pid_old, pid_new = _seed()
    # New: 5 adopts, 0 thumbs = score 5
    for player in ["b", "c", "d", "e", "f"]:
        a.adopt(
            player_id=player, publish_id=pid_new,
            mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
        )
    # Old: 1 adopt, 3 ups = score 1 + 6 = 7
    a.adopt(
        player_id="x", publish_id=pid_old,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    for player in ["y", "z", "w"]:
        t.record_thumb(
            player_id=player, publish_id=pid_old,
            thumb=Thumb.UP, posted_at=1_000_000,
        )
    out = t.top(now=1_000_100, window_days=7)
    # old score 7, new score 5
    assert out[0].publish_id == pid_old
    assert out[0].score == 7


def test_top_filters_by_job():
    p, a, t, _, _ = _seed()
    pid_blm = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_x", lua_source="-- z",
        reputation_snapshot=80, hours_played_on_job=300,
        published_at=900_000,
    )
    a.adopt(
        player_id="b", publish_id=pid_blm,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    out = t.top(
        now=1_000_100, window_days=7, job="BLM",
    )
    assert len(out) == 1
    assert out[0].job == "BLM"


def test_top_unlisted_excluded():
    p, a, t, pid_old, _ = _seed()
    a.adopt(
        player_id="b", publish_id=pid_old,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    p.unlist(author_id="chharith", publish_id=pid_old)
    out = t.top(now=1_000_100, window_days=7)
    pid_set = {e.publish_id for e in out}
    assert pid_old not in pid_set


def test_top_revoked_excluded():
    p, a, t, pid_old, _ = _seed()
    a.adopt(
        player_id="b", publish_id=pid_old,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    p.revoke(publish_id=pid_old, reason="exploit")
    out = t.top(now=1_000_100, window_days=7)
    pid_set = {e.publish_id for e in out}
    assert pid_old not in pid_set


def test_top_zero_limit():
    _, _, t, _, _ = _seed()
    assert t.top(now=1_000_000, window_days=7, limit=0) == []


def test_top_zero_window_empty():
    _, _, t, _, _ = _seed()
    assert t.top(now=1_000_000, window_days=0) == []


def test_top_caps_at_limit():
    p, a, t, _, _ = _seed()
    # Make 3 trendy publishes
    for i in range(3):
        pid = p.publish(
            author_id="chharith", job="RDM",
            addon_id=f"rdm_{i}", lua_source=f"-- {i}",
            reputation_snapshot=80, hours_played_on_job=500,
            published_at=900_000,
        )
        a.adopt(
            player_id=f"p{i}", publish_id=pid,
            mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
        )
    out = t.top(now=1_000_100, window_days=7, limit=2)
    assert len(out) == 2


def test_top_rank_starts_at_1():
    _, a, t, _, pid_new = _seed()
    a.adopt(
        player_id="b", publish_id=pid_new,
        mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
    )
    out = t.top(now=1_000_100, window_days=7)
    assert out[0].rank == 1


def test_top_recent_adopts_field():
    _, a, t, _, pid_new = _seed()
    for player in ["b", "c"]:
        a.adopt(
            player_id=player, publish_id=pid_new,
            mode=AdoptMode.USE_AS_IS, adopted_at=1_000_000,
        )
    out = t.top(now=1_000_100, window_days=7)
    assert out[0].recent_adopts == 2


def test_top_recent_thumbs_fields():
    _, _, t, _, pid_new = _seed()
    t.record_thumb(
        player_id="b", publish_id=pid_new,
        thumb=Thumb.UP, posted_at=1_000_000,
    )
    t.record_thumb(
        player_id="c", publish_id=pid_new,
        thumb=Thumb.DOWN, posted_at=1_000_000,
    )
    out = t.top(now=1_000_100, window_days=7)
    assert out[0].recent_thumbs_up == 1
    assert out[0].recent_thumbs_down == 1
