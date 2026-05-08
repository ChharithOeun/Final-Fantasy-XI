"""Tests for zone_bulletin_board."""
from __future__ import annotations

from server.zone_bulletin_board import (
    AuthorKind, PostKind, ZoneBulletinBoard,
)


def _player_post(b, author="bob", kind=PostKind.RECRUIT,
                 title="LFM SAM", body="Need DD for KSNM",
                 t=1000, expires=None, zone="bastok"):
    return b.create_post(
        zone_id=zone, author_id=author,
        author_kind=AuthorKind.PLAYER, kind=kind,
        title=title, body=body,
        posted_at_ms=t, expires_at_ms=expires,
    )


def test_create_post_happy():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert p is not None
    assert p.post_id.startswith("post_")


def test_create_blank_zone_blocked():
    b = ZoneBulletinBoard()
    p = b.create_post(
        zone_id="", author_id="bob",
        author_kind=AuthorKind.PLAYER,
        kind=PostKind.RECRUIT,
        title="t", body="b", posted_at_ms=1000,
    )
    assert p is None


def test_create_blank_title_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b, title="")
    assert p is None


def test_create_long_title_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b, title="x" * 100)
    assert p is None


def test_create_long_body_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b, body="x" * 1000)
    assert p is None


def test_player_npc_only_kind_blocked():
    """Players can't post NEWS/WARNING/FESTIVAL."""
    b = ZoneBulletinBoard()
    blocked = _player_post(b, kind=PostKind.NEWS)
    assert blocked is None


def test_npc_can_post_news():
    b = ZoneBulletinBoard()
    p = b.create_post(
        zone_id="bastok", author_id="cid",
        author_kind=AuthorKind.NPC, kind=PostKind.NEWS,
        title="Conquest tally", body="Bastok leads.",
        posted_at_ms=1000,
    )
    assert p is not None


def test_player_post_cap_blocked():
    b = ZoneBulletinBoard()
    for i in range(5):
        _player_post(b, title=f"LFM #{i}", t=1000 + i)
    blocked = _player_post(b, title="LFM #6", t=1100)
    assert blocked is None


def test_expiry_drops_from_active():
    b = ZoneBulletinBoard()
    _player_post(b, t=1000, expires=2000)
    active = b.posts_in(zone_id="bastok", now_ms=1500)
    assert len(active) == 1
    expired = b.posts_in(zone_id="bastok", now_ms=3000)
    assert expired == []


def test_expiry_before_now_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b, t=2000, expires=1000)
    assert p is None


def test_no_expiry_persists():
    b = ZoneBulletinBoard()
    _player_post(b, t=1000, expires=None)
    active = b.posts_in(
        zone_id="bastok", now_ms=999999,
    )
    assert len(active) == 1


def test_update_own_post():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.update_post(
        post_id=p.post_id, author_id="bob",
        body="Updated body",
    ) is True


def test_update_other_player_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.update_post(
        post_id=p.post_id, author_id="cara",
        body="HACKED",
    ) is False


def test_update_invalid_title():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.update_post(
        post_id=p.post_id, author_id="bob",
        title="",
    ) is False


def test_remove_own_post():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.remove_post(
        post_id=p.post_id, requester_id="bob",
    ) is True


def test_remove_other_blocked():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.remove_post(
        post_id=p.post_id, requester_id="cara",
    ) is False


def test_remove_moderator_overrides():
    b = ZoneBulletinBoard()
    p = _player_post(b)
    assert b.remove_post(
        post_id=p.post_id, requester_id="mod",
        is_moderator=True,
    ) is True


def test_filter_by_kind():
    b = ZoneBulletinBoard()
    _player_post(b, title="LFM 1", kind=PostKind.RECRUIT,
                 t=1000)
    _player_post(b, title="Sword for sale",
                 kind=PostKind.FOR_SALE, t=1100)
    out = b.filter_by_kind(
        zone_id="bastok", kind=PostKind.FOR_SALE,
        now_ms=1200,
    )
    assert len(out) == 1
    assert out[0].kind == PostKind.FOR_SALE


def test_posts_by_author():
    b = ZoneBulletinBoard()
    _player_post(b, author="bob", title="A", t=1000)
    _player_post(b, author="cara", title="B", t=1100)
    out = b.posts_by_author(
        author_id="bob", now_ms=1200,
    )
    assert len(out) == 1
    assert out[0].author_id == "bob"


def test_active_count():
    b = ZoneBulletinBoard()
    _player_post(b, title="A", t=1000, expires=1500)
    _player_post(b, title="B", t=1100, expires=2000)
    # at 1300 both active
    assert b.active_count_for_author(
        author_id="bob", now_ms=1300,
    ) == 2
    # at 1700 only second
    assert b.active_count_for_author(
        author_id="bob", now_ms=1700,
    ) == 1


def test_posts_sorted_newest_first():
    b = ZoneBulletinBoard()
    _player_post(b, title="A", t=1000)
    _player_post(b, title="B", t=2000)
    _player_post(b, title="C", t=1500)
    out = b.posts_in(zone_id="bastok", now_ms=3000)
    titles = [p.title for p in out]
    assert titles == ["B", "C", "A"]


def test_nine_post_kinds():
    assert len(list(PostKind)) == 9
