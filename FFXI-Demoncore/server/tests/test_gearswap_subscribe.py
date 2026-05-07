"""Tests for gearswap_subscribe."""
from __future__ import annotations

from server.gearswap_subscribe import (
    GearswapSubscribe, NotificationKind,
)


def test_follow_happy():
    s = GearswapSubscribe()
    out = s.follow(subscriber_id="bob", author_id="chharith")
    assert out is True


def test_follow_blank_blocked():
    s = GearswapSubscribe()
    assert s.follow(
        subscriber_id="", author_id="chharith",
    ) is False
    assert s.follow(
        subscriber_id="bob", author_id="",
    ) is False


def test_follow_self_blocked():
    s = GearswapSubscribe()
    assert s.follow(
        subscriber_id="bob", author_id="bob",
    ) is False


def test_follow_idempotent():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.follow(subscriber_id="bob", author_id="chharith")
    assert s.followers_of(author_id="chharith") == ["bob"]


def test_unfollow_happy():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    assert s.unfollow(
        subscriber_id="bob", author_id="chharith",
    ) is True


def test_unfollow_unknown_blocked():
    s = GearswapSubscribe()
    assert s.unfollow(
        subscriber_id="bob", author_id="chharith",
    ) is False


def test_is_following_true():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    assert s.is_following(
        subscriber_id="bob", author_id="chharith",
    ) is True


def test_is_following_false():
    s = GearswapSubscribe()
    assert s.is_following(
        subscriber_id="bob", author_id="chharith",
    ) is False


def test_followers_of_sorted():
    s = GearswapSubscribe()
    for sid in ["zed", "alice", "bob"]:
        s.follow(subscriber_id=sid, author_id="chharith")
    assert s.followers_of(
        author_id="chharith",
    ) == ["alice", "bob", "zed"]


def test_following_lists_authors():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.follow(subscriber_id="bob", author_id="rival")
    out = s.following(subscriber_id="bob")
    assert out == ["chharith", "rival"]


def test_notify_publish_fans_out():
    s = GearswapSubscribe()
    for sid in ["bob", "cara"]:
        s.follow(subscriber_id=sid, author_id="chharith")
    n = s.notify_publish(
        author_id="chharith", publish_id="pub_1",
        addon_id="rdm_chharith", published_at=1000,
    )
    assert n == 2
    bob_unread = s.unread_for(subscriber_id="bob")
    assert len(bob_unread) == 1
    assert bob_unread[0].kind == NotificationKind.NEW_PUBLISH


def test_notify_publish_no_followers_zero():
    s = GearswapSubscribe()
    n = s.notify_publish(
        author_id="ghost", publish_id="pub_1",
        addon_id="rdm_x", published_at=1000,
    )
    assert n == 0


def test_notify_revision_fans_out():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    n = s.notify_revision(
        author_id="chharith", publish_id="pub_1",
        addon_id="rdm_chharith", revision_no=2,
        published_at=2000,
    )
    assert n == 1
    note = s.unread_for(subscriber_id="bob")[0]
    assert note.kind == NotificationKind.NEW_REVISION
    assert note.revision_no == 2


def test_notify_revision_under_2_blocked():
    """Revision 1 IS the initial publish — that's
    NEW_PUBLISH, not NEW_REVISION."""
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    n = s.notify_revision(
        author_id="chharith", publish_id="pub_1",
        addon_id="rdm_chharith", revision_no=1,
        published_at=2000,
    )
    assert n == 0
    assert s.unread_for(subscriber_id="bob") == []


def test_unread_for_sorted_by_time():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.notify_publish(
        author_id="chharith", publish_id="p2",
        addon_id="b", published_at=2000,
    )
    s.notify_publish(
        author_id="chharith", publish_id="p1",
        addon_id="a", published_at=1000,
    )
    out = s.unread_for(subscriber_id="bob")
    assert out[0].posted_at == 1000


def test_unread_excludes_other_subscribers():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.follow(subscriber_id="cara", author_id="chharith")
    s.notify_publish(
        author_id="chharith", publish_id="p1",
        addon_id="a", published_at=1000,
    )
    bob = s.unread_for(subscriber_id="bob")
    assert all(n.subscriber_id == "bob" for n in bob)


def test_mark_read_removes_from_unread():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.notify_publish(
        author_id="chharith", publish_id="p1",
        addon_id="a", published_at=1000,
    )
    note = s.unread_for(subscriber_id="bob")[0]
    n = s.mark_read(
        subscriber_id="bob",
        notification_ids=[note.notification_id],
    )
    assert n == 1
    assert s.unread_for(subscriber_id="bob") == []


def test_mark_read_other_subscribers_blocked():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.follow(subscriber_id="cara", author_id="chharith")
    s.notify_publish(
        author_id="chharith", publish_id="p1",
        addon_id="a", published_at=1000,
    )
    note = s.unread_for(subscriber_id="bob")[0]
    # cara tries to mark bob's notification read
    n = s.mark_read(
        subscriber_id="cara",
        notification_ids=[note.notification_id],
    )
    assert n == 0
    assert s.unread_for(subscriber_id="bob") != []


def test_mark_read_unknown_id_zero():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    n = s.mark_read(
        subscriber_id="bob", notification_ids=[9999],
    )
    assert n == 0


def test_total_followers():
    s = GearswapSubscribe()
    s.follow(subscriber_id="bob", author_id="chharith")
    s.follow(subscriber_id="cara", author_id="chharith")
    s.follow(subscriber_id="bob", author_id="rival")
    assert s.total_followers() == 3


def test_two_notification_kinds():
    assert len(list(NotificationKind)) == 2
