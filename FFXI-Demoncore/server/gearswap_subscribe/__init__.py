"""GearSwap subscribe — follow your favourite authors.

Famous authors get followers. When the author publishes
a fresh lua or pushes a revision to an existing one,
their subscribers see a notification on next login (or
right then, if they're online).

Two notification kinds:
    NEW_PUBLISH   author shipped a brand-new lua
                  (different addon_id from anything
                  they had before)
    NEW_REVISION  author pushed v2+ of an existing lua
                  the subscriber may have adopted

The module owns:
    - the (subscriber, author) follow set
    - an outbox of pending notifications, dispatched
      by the UI poller and marked-read on display

Notifications are append-only — the UI marks them read
to take them off the unread queue but the audit trail
stays. Kept under a per-subscriber cap (200) to bound
memory.

Public surface
--------------
    NotificationKind enum
    Notification dataclass (frozen)
    GearswapSubscribe
        .follow(subscriber_id, author_id) -> bool
        .unfollow(subscriber_id, author_id) -> bool
        .is_following(subscriber_id, author_id) -> bool
        .followers_of(author_id) -> list[str]
        .following(subscriber_id) -> list[str]
        .notify_publish(author_id, publish_id, addon_id,
                        published_at) -> int  # n notified
        .notify_revision(author_id, publish_id, revision_no,
                         published_at) -> int
        .unread_for(subscriber_id) -> list[Notification]
        .mark_read(subscriber_id, notification_ids)
            -> int   # n marked
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_OUTBOX_PER_SUBSCRIBER = 200


class NotificationKind(str, enum.Enum):
    NEW_PUBLISH = "new_publish"
    NEW_REVISION = "new_revision"


@dataclasses.dataclass(frozen=True)
class Notification:
    notification_id: int
    subscriber_id: str
    author_id: str
    publish_id: str
    kind: NotificationKind
    revision_no: int          # 0 for NEW_PUBLISH; >=2 for NEW_REVISION
    addon_id: str
    posted_at: int
    read: bool


@dataclasses.dataclass
class GearswapSubscribe:
    # author_id -> set[subscriber_id]
    _followers: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    _outbox: list[Notification] = dataclasses.field(
        default_factory=list,
    )
    _next_id: int = 1

    def follow(
        self, *, subscriber_id: str, author_id: str,
    ) -> bool:
        if not subscriber_id or not author_id:
            return False
        if subscriber_id == author_id:
            return False   # no following yourself
        self._followers.setdefault(
            author_id, set(),
        ).add(subscriber_id)
        return True

    def unfollow(
        self, *, subscriber_id: str, author_id: str,
    ) -> bool:
        s = self._followers.get(author_id)
        if not s or subscriber_id not in s:
            return False
        s.remove(subscriber_id)
        return True

    def is_following(
        self, *, subscriber_id: str, author_id: str,
    ) -> bool:
        s = self._followers.get(author_id)
        return s is not None and subscriber_id in s

    def followers_of(
        self, *, author_id: str,
    ) -> list[str]:
        return sorted(self._followers.get(author_id, set()))

    def following(
        self, *, subscriber_id: str,
    ) -> list[str]:
        return sorted(
            a for a, fs in self._followers.items()
            if subscriber_id in fs
        )

    def _enqueue(
        self, *, subscriber_id: str, author_id: str,
        publish_id: str, kind: NotificationKind,
        revision_no: int, addon_id: str, posted_at: int,
    ) -> None:
        # Cap per-subscriber outbox by dropping oldest
        # for THIS subscriber if at the cap.
        existing = [
            i for i, n in enumerate(self._outbox)
            if n.subscriber_id == subscriber_id
        ]
        if len(existing) >= _MAX_OUTBOX_PER_SUBSCRIBER:
            # Drop the oldest by index
            del self._outbox[existing[0]]
        self._outbox.append(Notification(
            notification_id=self._next_id,
            subscriber_id=subscriber_id,
            author_id=author_id, publish_id=publish_id,
            kind=kind, revision_no=revision_no,
            addon_id=addon_id, posted_at=posted_at,
            read=False,
        ))
        self._next_id += 1

    def notify_publish(
        self, *, author_id: str, publish_id: str,
        addon_id: str, published_at: int,
    ) -> int:
        subs = self._followers.get(author_id, set())
        for sub in subs:
            self._enqueue(
                subscriber_id=sub, author_id=author_id,
                publish_id=publish_id,
                kind=NotificationKind.NEW_PUBLISH,
                revision_no=0, addon_id=addon_id,
                posted_at=published_at,
            )
        return len(subs)

    def notify_revision(
        self, *, author_id: str, publish_id: str,
        addon_id: str, revision_no: int, published_at: int,
    ) -> int:
        if revision_no < 2:
            return 0
        subs = self._followers.get(author_id, set())
        for sub in subs:
            self._enqueue(
                subscriber_id=sub, author_id=author_id,
                publish_id=publish_id,
                kind=NotificationKind.NEW_REVISION,
                revision_no=revision_no, addon_id=addon_id,
                posted_at=published_at,
            )
        return len(subs)

    def unread_for(
        self, *, subscriber_id: str,
    ) -> list[Notification]:
        out = [
            n for n in self._outbox
            if n.subscriber_id == subscriber_id
            and not n.read
        ]
        out.sort(key=lambda n: n.posted_at)
        return out

    def mark_read(
        self, *, subscriber_id: str,
        notification_ids: list[int],
    ) -> int:
        target = set(notification_ids)
        n = 0
        for i, note in enumerate(self._outbox):
            if (note.subscriber_id == subscriber_id
                    and note.notification_id in target
                    and not note.read):
                self._outbox[i] = dataclasses.replace(
                    note, read=True,
                )
                n += 1
        return n

    def total_followers(self) -> int:
        return sum(len(s) for s in self._followers.values())


__all__ = [
    "NotificationKind", "Notification", "GearswapSubscribe",
]
