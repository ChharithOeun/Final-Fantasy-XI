"""Tests for gearswap_publisher."""
from __future__ import annotations

from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)


def _setup():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    return p


def _publish(p, **overrides):
    kwargs = dict(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith",
        lua_source="-- working lua source",
        reputation_snapshot=50,
        hours_played_on_job=500,
        published_at=1000,
    )
    kwargs.update(overrides)
    return p.publish(**kwargs)


def test_eligibility_happy():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", job="RDM",
        hours_played_on_job=500, reputation_snapshot=50,
    )
    assert elig.eligible is True


def test_non_mentor_rejected():
    p = GearswapPublisher()
    elig = p.check_eligibility(
        author_id="someone", job="RDM",
        hours_played_on_job=500, reputation_snapshot=50,
    )
    assert elig.eligible is False
    assert elig.failure_reason == "not_mentor"


def test_insufficient_hours_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", job="RDM",
        hours_played_on_job=10, reputation_snapshot=50,
    )
    assert elig.eligible is False
    assert elig.failure_reason == "insufficient_hours_on_job"


def test_blank_job_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", job="",
        hours_played_on_job=500, reputation_snapshot=50,
    )
    assert elig.eligible is False
    assert elig.failure_reason == "job_required"


def test_blank_author_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="", job="RDM",
        hours_played_on_job=500, reputation_snapshot=50,
    )
    assert elig.eligible is False
    assert elig.failure_reason == "author_id_required"


def test_negative_reputation_still_eligible():
    """Infamous mentors can still publish — gallery shows the score."""
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", job="RDM",
        hours_played_on_job=500, reputation_snapshot=-100,
    )
    assert elig.eligible is True
    assert elig.reputation_seen == -100


def test_publish_happy():
    p = _setup()
    pid = _publish(p)
    assert pid is not None
    assert pid.startswith("pub_")


def test_publish_returns_none_when_ineligible():
    p = GearswapPublisher()
    pid = _publish(p, author_id="not_mentor")
    assert pid is None


def test_publish_blank_addon_id_rejected():
    p = _setup()
    pid = _publish(p, addon_id="")
    assert pid is None


def test_publish_blank_lua_rejected():
    p = _setup()
    pid = _publish(p, lua_source="")
    assert pid is None


def test_lookup_returns_published():
    p = _setup()
    pid = _publish(p)
    entry = p.lookup(publish_id=pid)
    assert entry is not None
    assert entry.author_id == "chharith"
    assert entry.author_display_name == "Chharith"


def test_lookup_unknown_none():
    p = _setup()
    assert p.lookup(publish_id="ghost") is None


def test_published_records_content_hash():
    p = _setup()
    pid = _publish(p, lua_source="-- exact source")
    entry = p.lookup(publish_id=pid)
    # sha256 of the source — we just check it's stable + nonempty
    assert len(entry.content_hash) == 64
    assert entry.content_hash == p.lookup(
        publish_id=pid,
    ).content_hash


def test_unique_publish_ids_increment():
    p = _setup()
    pid1 = _publish(p)
    pid2 = _publish(p)
    assert pid1 != pid2


def test_by_author_lists_all():
    p = _setup()
    _publish(p)
    _publish(p, addon_id="rdm_v2")
    out = p.by_author(author_id="chharith")
    assert len(out) == 2


def test_by_author_unknown_empty():
    p = _setup()
    assert p.by_author(author_id="nobody") == []


def test_unlist_owner():
    p = _setup()
    pid = _publish(p)
    out = p.unlist(author_id="chharith", publish_id=pid)
    assert out is True
    entry = p.lookup(publish_id=pid)
    assert entry.status == PublishStatus.UNLISTED


def test_unlist_non_owner_blocked():
    p = _setup()
    pid = _publish(p)
    out = p.unlist(author_id="impostor", publish_id=pid)
    assert out is False


def test_unlist_unknown_blocked():
    p = _setup()
    out = p.unlist(author_id="chharith", publish_id="ghost")
    assert out is False


def test_relist_after_unlist():
    p = _setup()
    pid = _publish(p)
    p.unlist(author_id="chharith", publish_id=pid)
    out = p.relist(author_id="chharith", publish_id=pid)
    assert out is True
    entry = p.lookup(publish_id=pid)
    assert entry.status == PublishStatus.PUBLISHED


def test_relist_when_not_unlisted_blocked():
    p = _setup()
    pid = _publish(p)
    out = p.relist(author_id="chharith", publish_id=pid)
    assert out is False


def test_revoke_terminal():
    p = _setup()
    pid = _publish(p)
    out = p.revoke(publish_id=pid, reason="contains_exploit")
    assert out is True
    entry = p.lookup(publish_id=pid)
    assert entry.status == PublishStatus.REVOKED
    assert entry.revoke_reason == "contains_exploit"


def test_revoke_blank_reason_blocked():
    p = _setup()
    pid = _publish(p)
    out = p.revoke(publish_id=pid, reason="")
    assert out is False


def test_revoked_cannot_be_unlisted_back():
    """Revoked status is terminal — author cannot reverse it."""
    p = _setup()
    pid = _publish(p)
    p.revoke(publish_id=pid, reason="bad")
    # author tries to unlist (which should normally work)
    out = p.unlist(author_id="chharith", publish_id=pid)
    assert out is False


def test_total_published_excludes_unlisted():
    p = _setup()
    pid1 = _publish(p)
    _publish(p, addon_id="v2")
    p.unlist(author_id="chharith", publish_id=pid1)
    assert p.total_published() == 1


def test_total_entries_includes_all():
    p = _setup()
    _publish(p)
    _publish(p, addon_id="v2")
    assert p.total_entries() == 2


def test_set_mentor_status_blank_blocked():
    p = GearswapPublisher()
    out = p.set_mentor_status(
        author_id="", is_mentor=True,
    )
    assert out is False


def test_four_publish_statuses():
    assert len(list(PublishStatus)) == 4
