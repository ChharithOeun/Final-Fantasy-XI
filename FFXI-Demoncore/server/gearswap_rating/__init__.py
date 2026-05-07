"""GearSwap rating — thumbs, comments, reports per published lua.

Drives the social signal layer for the gallery. Players
who adopted a build can leave a thumb (up/down) and a
short comment. Anyone can file a report flagging a build
(exploit / spelling error / wrong slot / outdated for a
patch). The rating data feeds back into the author's
mentor reputation and into the gallery's popularity sort.

The rating store is intentionally separate from
gearswap_adopt — adoption is a personal install action,
rating is a social judgment. A player can adopt without
rating, and an old screenshot tester can rate without
adopting (we just require they had it adopted at some
point, enforced by the caller via a check against
gearswap_adopt).

We deliberately allow only ONE thumb per (player, publish)
pair. Re-rating overwrites — players change their mind,
that's fine. Reports are append-only because the
moderation log needs all flags, even duplicates.

Public surface
--------------
    Thumb enum (UP/DOWN)
    ReportReason enum
    Comment dataclass (frozen)
    Report dataclass (frozen)
    RatingSummary dataclass (frozen)
    GearswapRating
        .rate(player_id, publish_id, thumb) -> bool
        .un_rate(player_id, publish_id) -> bool
        .comment(player_id, publish_id, body, posted_at)
            -> Optional[Comment]
        .report(player_id, publish_id, reason, posted_at)
            -> Optional[Report]
        .summary(publish_id) -> RatingSummary
        .comments_for(publish_id) -> list[Comment]
        .reports_for(publish_id) -> list[Report]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_COMMENT_LEN = 280


class Thumb(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class ReportReason(str, enum.Enum):
    EXPLOIT = "exploit"           # uses banned/cheat behavior
    SPELLING = "spelling"         # gear name typo'd, won't load
    WRONG_SLOT = "wrong_slot"     # piece in slot it doesn't fit
    OUTDATED = "outdated"         # broken by a game patch
    OTHER = "other"


@dataclasses.dataclass(frozen=True)
class Comment:
    player_id: str
    publish_id: str
    body: str
    posted_at: int


@dataclasses.dataclass(frozen=True)
class Report:
    player_id: str
    publish_id: str
    reason: ReportReason
    posted_at: int


@dataclasses.dataclass(frozen=True)
class RatingSummary:
    publish_id: str
    thumbs_up: int
    thumbs_down: int
    comment_count: int
    report_count: int


@dataclasses.dataclass
class GearswapRating:
    # (player_id, publish_id) -> Thumb (one per pair)
    _thumbs: dict[tuple[str, str], Thumb] = dataclasses.field(
        default_factory=dict,
    )
    _comments: list[Comment] = dataclasses.field(
        default_factory=list,
    )
    _reports: list[Report] = dataclasses.field(
        default_factory=list,
    )

    def rate(
        self, *, player_id: str, publish_id: str, thumb: Thumb,
    ) -> bool:
        if not player_id or not publish_id:
            return False
        self._thumbs[(player_id, publish_id)] = thumb
        return True

    def un_rate(
        self, *, player_id: str, publish_id: str,
    ) -> bool:
        key = (player_id, publish_id)
        if key not in self._thumbs:
            return False
        del self._thumbs[key]
        return True

    def comment(
        self, *, player_id: str, publish_id: str,
        body: str, posted_at: int,
    ) -> t.Optional[Comment]:
        if not player_id or not publish_id:
            return None
        body = body.strip()
        if not body or len(body) > _MAX_COMMENT_LEN:
            return None
        c = Comment(
            player_id=player_id, publish_id=publish_id,
            body=body, posted_at=posted_at,
        )
        self._comments.append(c)
        return c

    def report(
        self, *, player_id: str, publish_id: str,
        reason: ReportReason, posted_at: int,
    ) -> t.Optional[Report]:
        if not player_id or not publish_id:
            return None
        r = Report(
            player_id=player_id, publish_id=publish_id,
            reason=reason, posted_at=posted_at,
        )
        self._reports.append(r)
        return r

    def summary(self, *, publish_id: str) -> RatingSummary:
        ups = sum(
            1 for (_p, pid), t in self._thumbs.items()
            if pid == publish_id and t == Thumb.UP
        )
        downs = sum(
            1 for (_p, pid), t in self._thumbs.items()
            if pid == publish_id and t == Thumb.DOWN
        )
        ccount = sum(
            1 for c in self._comments if c.publish_id == publish_id
        )
        rcount = sum(
            1 for r in self._reports if r.publish_id == publish_id
        )
        return RatingSummary(
            publish_id=publish_id, thumbs_up=ups,
            thumbs_down=downs, comment_count=ccount,
            report_count=rcount,
        )

    def comments_for(
        self, *, publish_id: str,
    ) -> list[Comment]:
        out = [
            c for c in self._comments
            if c.publish_id == publish_id
        ]
        out.sort(key=lambda c: c.posted_at)
        return out

    def reports_for(
        self, *, publish_id: str,
    ) -> list[Report]:
        out = [
            r for r in self._reports
            if r.publish_id == publish_id
        ]
        out.sort(key=lambda r: r.posted_at)
        return out

    def thumb_for(
        self, *, player_id: str, publish_id: str,
    ) -> t.Optional[Thumb]:
        return self._thumbs.get((player_id, publish_id))

    def total_thumbs(self) -> int:
        return len(self._thumbs)

    def total_comments(self) -> int:
        return len(self._comments)

    def total_reports(self) -> int:
        return len(self._reports)


__all__ = [
    "Thumb", "ReportReason", "Comment", "Report",
    "RatingSummary", "GearswapRating",
]
