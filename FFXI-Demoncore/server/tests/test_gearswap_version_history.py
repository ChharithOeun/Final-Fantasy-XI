"""Tests for gearswap_version_history."""
from __future__ import annotations

from server.gearswap_publisher import GearswapPublisher
from server.gearswap_version_history import (
    GearswapVersionHistory,
)


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    pid = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith",
        lua_source="-- v1 source",
        reputation_snapshot=80,
        hours_played_on_job=500, published_at=1000,
    )
    h = GearswapVersionHistory(_publisher=p)
    entry = p.lookup(publish_id=pid)
    h.seed_initial(
        publish_id=pid, lua_source=entry.lua_source,
        content_hash=entry.content_hash,
        published_at=entry.published_at,
    )
    return p, h, pid


def test_seed_initial():
    _, h, pid = _seed()
    cur = h.current(publish_id=pid)
    assert cur is not None
    assert cur.revision_no == 1
    assert cur.notes == "initial publish"


def test_seed_initial_idempotent():
    _, h, pid = _seed()
    out = h.seed_initial(
        publish_id=pid, lua_source="-- different",
        content_hash="x", published_at=2000,
    )
    assert out is None
    assert h.revision_count(publish_id=pid) == 1


def test_push_revision_happy():
    _, h, pid = _seed()
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2 source",
        notes="tuned haste set", published_at=2000,
    )
    assert rev is not None
    assert rev.revision_no == 2
    assert rev.notes == "tuned haste set"


def test_push_revision_non_author_blocked():
    _, h, pid = _seed()
    rev = h.push_revision(
        author_id="impostor", publish_id=pid,
        lua_source="-- v2", notes="hi", published_at=2000,
    )
    assert rev is None


def test_push_revision_unknown_publish_blocked():
    _, h, _ = _seed()
    rev = h.push_revision(
        author_id="chharith", publish_id="ghost",
        lua_source="-- v2", notes="hi", published_at=2000,
    )
    assert rev is None


def test_push_revision_blank_lua_blocked():
    _, h, pid = _seed()
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="", notes="hi", published_at=2000,
    )
    assert rev is None


def test_push_revision_long_notes_blocked():
    _, h, pid = _seed()
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="x" * 201,
        published_at=2000,
    )
    assert rev is None


def test_push_revision_revoked_blocked():
    p, h, pid = _seed()
    p.revoke(publish_id=pid, reason="exploit")
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="hi", published_at=2000,
    )
    assert rev is None


def test_push_revision_unlisted_still_allowed():
    """Author can keep updating even while unlisted; they
    might be polishing for a relist."""
    p, h, pid = _seed()
    p.unlist(author_id="chharith", publish_id=pid)
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="polish", published_at=2000,
    )
    assert rev is not None


def test_push_revision_nochange_blocked():
    """Pushing identical source is a no-op."""
    _, h, pid = _seed()
    rev = h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v1 source",   # same as initial
        notes="oops", published_at=2000,
    )
    assert rev is None


def test_revision_count_grows():
    _, h, pid = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v3", notes="b", published_at=3000,
    )
    assert h.revision_count(publish_id=pid) == 3


def test_history_in_order():
    _, h, pid = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v3", notes="b", published_at=3000,
    )
    hist = h.history(publish_id=pid)
    assert [r.revision_no for r in hist] == [1, 2, 3]


def test_current_returns_latest():
    _, h, pid = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v3", notes="b", published_at=3000,
    )
    cur = h.current(publish_id=pid)
    assert cur.revision_no == 3


def test_current_unknown_none():
    _, h, _ = _seed()
    assert h.current(publish_id="ghost") is None


def test_history_unknown_empty():
    _, h, _ = _seed()
    assert h.history(publish_id="ghost") == []


def test_has_update_true():
    p, h, pid = _seed()
    initial_hash = p.lookup(publish_id=pid).content_hash
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    assert h.has_update(
        publish_id=pid, adopted_hash=initial_hash,
    ) is True


def test_has_update_false_when_current():
    p, h, pid = _seed()
    initial_hash = p.lookup(publish_id=pid).content_hash
    assert h.has_update(
        publish_id=pid, adopted_hash=initial_hash,
    ) is False


def test_has_update_unknown_publish_false():
    _, h, _ = _seed()
    assert h.has_update(
        publish_id="ghost", adopted_hash="x",
    ) is False


def test_diff_to_current_known_hash():
    p, h, pid = _seed()
    initial_hash = p.lookup(publish_id=pid).content_hash
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v3", notes="b", published_at=3000,
    )
    out = h.diff_to_current(
        publish_id=pid, adopted_hash=initial_hash,
    )
    assert out == (1, 3)


def test_diff_to_current_unknown_hash():
    _, h, pid = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    out = h.diff_to_current(
        publish_id=pid, adopted_hash="bogus_hash",
    )
    assert out == (0, 2)


def test_diff_to_current_already_current():
    p, h, pid = _seed()
    initial_hash = p.lookup(publish_id=pid).content_hash
    assert h.diff_to_current(
        publish_id=pid, adopted_hash=initial_hash,
    ) is None


def test_diff_to_current_unknown_publish():
    _, h, _ = _seed()
    assert h.diff_to_current(
        publish_id="ghost", adopted_hash="x",
    ) is None


def test_total_revisions():
    p, h, pid = _seed()
    h.push_revision(
        author_id="chharith", publish_id=pid,
        lua_source="-- v2", notes="a", published_at=2000,
    )
    pid2 = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith",
        lua_source="-- blm v1", reputation_snapshot=80,
        hours_played_on_job=300, published_at=1500,
    )
    entry2 = p.lookup(publish_id=pid2)
    h.seed_initial(
        publish_id=pid2, lua_source=entry2.lua_source,
        content_hash=entry2.content_hash,
        published_at=entry2.published_at,
    )
    assert h.total_revisions() == 3
