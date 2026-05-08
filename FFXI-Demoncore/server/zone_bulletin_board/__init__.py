"""Zone bulletin boards — public posts per zone.

Walk into Bastok Markets, see a wooden board outside the
Tenshodo. Pinned: news from the Conquest tally, weather
warnings from the Geomancy guild, "WANTED" posters from
the wanted_poster system, players advertising party
recruits. The board is the in-world social-feed for the
zone.

A POST has:
    post_id, zone_id, author_id (NPC or player),
    kind (NEWS / WEATHER / WANTED / RECRUIT / FOR_SALE
    / FOR_TRADE / FESTIVAL / LORE / WARNING),
    title, body, posted_at_ms, expires_at_ms (None = never)

Posting limits:
    - Per-player active-post cap (default 5) so players
      can't spam the board
    - NPC system posts (kind=NEWS/WARNING/FESTIVAL) have
      no cap — they're trusted authors
    - title <= 80 chars, body <= 500 chars

Search/list:
    - posts_in(zone_id, now_ms) returns active posts
    - filter_by_kind(zone_id, kind, now_ms)
    - posts_by_author(author_id, now_ms) — your own posts

Lifecycle:
    create_post() returns post_id or None on rejection.
    update_post() lets the author edit body/title.
    remove_post() deletes (only by author or moderator).

Public surface
--------------
    PostKind enum
    AuthorKind enum
    Post dataclass (frozen)
    ZoneBulletinBoard
        .create_post(...) -> Optional[Post]
        .update_post(post_id, author_id, title, body)
            -> bool
        .remove_post(post_id, author_id, is_moderator=False)
            -> bool
        .posts_in(zone_id, now_ms) -> list[Post]
        .filter_by_kind(zone_id, kind, now_ms) -> list[Post]
        .posts_by_author(author_id, now_ms) -> list[Post]
        .active_count_for_author(author_id, now_ms) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_DEFAULT_PLAYER_POST_CAP = 5
_TITLE_MAX = 80
_BODY_MAX = 500


class PostKind(str, enum.Enum):
    NEWS = "news"
    WEATHER = "weather"
    WANTED = "wanted"
    RECRUIT = "recruit"
    FOR_SALE = "for_sale"
    FOR_TRADE = "for_trade"
    FESTIVAL = "festival"
    LORE = "lore"
    WARNING = "warning"


class AuthorKind(str, enum.Enum):
    PLAYER = "player"
    NPC = "npc"


_NPC_ONLY_KINDS = {
    PostKind.NEWS, PostKind.WARNING, PostKind.FESTIVAL,
}


@dataclasses.dataclass(frozen=True)
class Post:
    post_id: str
    zone_id: str
    author_id: str
    author_kind: AuthorKind
    kind: PostKind
    title: str
    body: str
    posted_at_ms: int
    expires_at_ms: t.Optional[int]


@dataclasses.dataclass
class ZoneBulletinBoard:
    _posts: dict[str, Post] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1
    _player_post_cap: int = _DEFAULT_PLAYER_POST_CAP

    def _is_active(self, post: Post, now_ms: int) -> bool:
        if post.expires_at_ms is None:
            return True
        return post.expires_at_ms > now_ms

    def create_post(
        self, *, zone_id: str, author_id: str,
        author_kind: AuthorKind, kind: PostKind,
        title: str, body: str, posted_at_ms: int,
        expires_at_ms: t.Optional[int] = None,
    ) -> t.Optional[Post]:
        if not zone_id or not author_id:
            return None
        if not title or len(title) > _TITLE_MAX:
            return None
        if not body or len(body) > _BODY_MAX:
            return None
        # Player can't post NPC-only kinds
        if (author_kind == AuthorKind.PLAYER
                and kind in _NPC_ONLY_KINDS):
            return None
        if (expires_at_ms is not None
                and expires_at_ms <= posted_at_ms):
            return None
        # Cap player active posts
        if author_kind == AuthorKind.PLAYER:
            active = self.active_count_for_author(
                author_id=author_id, now_ms=posted_at_ms,
            )
            if active >= self._player_post_cap:
                return None
        post_id = f"post_{self._next_id}"
        self._next_id += 1
        post = Post(
            post_id=post_id, zone_id=zone_id,
            author_id=author_id,
            author_kind=author_kind, kind=kind,
            title=title, body=body,
            posted_at_ms=posted_at_ms,
            expires_at_ms=expires_at_ms,
        )
        self._posts[post_id] = post
        return post

    def update_post(
        self, *, post_id: str, author_id: str,
        title: t.Optional[str] = None,
        body: t.Optional[str] = None,
    ) -> bool:
        if post_id not in self._posts:
            return False
        post = self._posts[post_id]
        if post.author_id != author_id:
            return False
        new_title = title if title is not None else post.title
        new_body = body if body is not None else post.body
        if not new_title or len(new_title) > _TITLE_MAX:
            return False
        if not new_body or len(new_body) > _BODY_MAX:
            return False
        self._posts[post_id] = dataclasses.replace(
            post, title=new_title, body=new_body,
        )
        return True

    def remove_post(
        self, *, post_id: str, requester_id: str,
        is_moderator: bool = False,
    ) -> bool:
        if post_id not in self._posts:
            return False
        post = self._posts[post_id]
        if not is_moderator and post.author_id != requester_id:
            return False
        del self._posts[post_id]
        return True

    def posts_in(
        self, *, zone_id: str, now_ms: int,
    ) -> list[Post]:
        out = [
            p for p in self._posts.values()
            if p.zone_id == zone_id
            and self._is_active(p, now_ms)
        ]
        out.sort(key=lambda p: -p.posted_at_ms)
        return out

    def filter_by_kind(
        self, *, zone_id: str, kind: PostKind,
        now_ms: int,
    ) -> list[Post]:
        return [
            p for p in self.posts_in(
                zone_id=zone_id, now_ms=now_ms,
            )
            if p.kind == kind
        ]

    def posts_by_author(
        self, *, author_id: str, now_ms: int,
    ) -> list[Post]:
        out = [
            p for p in self._posts.values()
            if p.author_id == author_id
            and self._is_active(p, now_ms)
        ]
        out.sort(key=lambda p: -p.posted_at_ms)
        return out

    def active_count_for_author(
        self, *, author_id: str, now_ms: int,
    ) -> int:
        return len(self.posts_by_author(
            author_id=author_id, now_ms=now_ms,
        ))


__all__ = [
    "PostKind", "AuthorKind", "Post", "ZoneBulletinBoard",
]
