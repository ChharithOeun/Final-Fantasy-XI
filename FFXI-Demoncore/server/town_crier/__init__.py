"""Town crier — public announcer broadcasts.

A town crier NPC stands in the plaza and shouts the news of the
day: "Hear ye, hear ye! The Goblin Market Festival opens at dawn
the third day of the Wind Moon!" Players nearby hear it; nearby
NPCs may relay it as a rumor (rumor_propagation hook).

Distinct from rumor_propagation (one-on-one gossip): this is
the ONE-TO-MANY public broadcast, scheduled by faction-level
event organizers.

Lifecycle
---------
    QUEUED       — announcement registered for a venue+slot
    PROCLAIMED   — has been spoken at least once
    EXPIRED      — past its expiry window; no longer announced

Public surface
--------------
    AnnouncementKind enum
    Priority enum
    CrierAnnouncement dataclass
    BroadcastResult dataclass
    TownCrierRegistry
        .register_crier(crier_id, venue_id, schedule_hours)
        .queue_announcement(announcement)
        .proclaim(crier_id, now_seconds, hour) -> BroadcastResult
        .expire_old(now_seconds) — sweep stale announcements
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default expiry (game-seconds). Most announcements stale after
# 3 game-days unless explicitly scheduled.
DEFAULT_EXPIRY_SECONDS = 60 * 60 * 24 * 3


class AnnouncementKind(str, enum.Enum):
    EVENT_OPENING = "event_opening"
    NEW_QUEST = "new_quest"
    BOSS_DEFEATED = "boss_defeated"
    NATION_CONQUEST = "nation_conquest"
    DECREE = "decree"                  # nation-wide policy
    WARNING = "warning"                # beastmen raid imminent
    LOST_AND_FOUND = "lost_and_found"
    OBITUARY = "obituary"              # named NPC death
    MARKET_PRICE = "market_price"
    TOURNAMENT = "tournament"


class AnnouncementPriority(str, enum.Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


_PRIORITY_ORDER: dict[AnnouncementPriority, int] = {
    AnnouncementPriority.URGENT: 0,
    AnnouncementPriority.HIGH: 1,
    AnnouncementPriority.NORMAL: 2,
    AnnouncementPriority.LOW: 3,
}


@dataclasses.dataclass(frozen=True)
class CrierProfile:
    crier_id: str
    venue_id: str
    schedule_hours: tuple[int, ...]   # hours during which active
    audience_radius_tiles: int = 30


@dataclasses.dataclass
class CrierAnnouncement:
    announcement_id: str
    kind: AnnouncementKind
    text: str
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    queued_at_seconds: float = 0.0
    expires_at_seconds: float = 0.0
    proclaim_count: int = 0
    times_to_repeat: int = 3            # repeat for emphasis
    notes: str = ""

    def is_active(self, *, now_seconds: float) -> bool:
        return now_seconds < self.expires_at_seconds

    def is_done(self) -> bool:
        return self.proclaim_count >= self.times_to_repeat


@dataclasses.dataclass(frozen=True)
class BroadcastResult:
    accepted: bool
    crier_id: str
    proclaimed: tuple[str, ...]      # announcement_ids
    reason: t.Optional[str] = None


@dataclasses.dataclass
class TownCrierRegistry:
    _criers: dict[str, CrierProfile] = dataclasses.field(
        default_factory=dict,
    )
    _announcements: dict[
        str, CrierAnnouncement,
    ] = dataclasses.field(default_factory=dict)

    def register_crier(
        self, profile: CrierProfile,
    ) -> CrierProfile:
        self._criers[profile.crier_id] = profile
        return profile

    def crier(self, crier_id: str) -> t.Optional[CrierProfile]:
        return self._criers.get(crier_id)

    def queue_announcement(
        self, *, announcement: CrierAnnouncement,
        now_seconds: float = 0.0,
        ttl_seconds: float = DEFAULT_EXPIRY_SECONDS,
    ) -> CrierAnnouncement:
        if announcement.expires_at_seconds <= 0:
            announcement.expires_at_seconds = (
                now_seconds + ttl_seconds
            )
        if announcement.queued_at_seconds <= 0:
            announcement.queued_at_seconds = now_seconds
        self._announcements[
            announcement.announcement_id
        ] = announcement
        return announcement

    def active_queue(
        self, *, now_seconds: float,
    ) -> tuple[CrierAnnouncement, ...]:
        actives = [
            a for a in self._announcements.values()
            if a.is_active(now_seconds=now_seconds)
            and not a.is_done()
        ]
        actives.sort(
            key=lambda a: (
                _PRIORITY_ORDER[a.priority],
                a.queued_at_seconds,
            ),
        )
        return tuple(actives)

    def proclaim(
        self, *, crier_id: str, now_seconds: float, hour: int,
        max_per_call: int = 1,
    ) -> BroadcastResult:
        crier = self._criers.get(crier_id)
        if crier is None:
            return BroadcastResult(
                accepted=False, crier_id=crier_id,
                proclaimed=(), reason="no such crier",
            )
        if hour % 24 not in crier.schedule_hours:
            return BroadcastResult(
                accepted=False, crier_id=crier_id,
                proclaimed=(),
                reason="crier off-shift this hour",
            )
        queue = self.active_queue(now_seconds=now_seconds)
        if not queue:
            return BroadcastResult(
                accepted=True, crier_id=crier_id,
                proclaimed=(),
                reason="nothing to proclaim",
            )
        spoken: list[str] = []
        for ann in queue[:max_per_call]:
            ann.proclaim_count += 1
            spoken.append(ann.announcement_id)
        return BroadcastResult(
            accepted=True, crier_id=crier_id,
            proclaimed=tuple(spoken),
        )

    def expire_old(self, *, now_seconds: float) -> int:
        before = len(self._announcements)
        self._announcements = {
            aid: a for aid, a in self._announcements.items()
            if a.is_active(now_seconds=now_seconds)
            and not a.is_done()
        }
        return before - len(self._announcements)

    def total_announcements(self) -> int:
        return len(self._announcements)

    def total_criers(self) -> int:
        return len(self._criers)


__all__ = [
    "DEFAULT_EXPIRY_SECONDS",
    "AnnouncementKind", "AnnouncementPriority",
    "CrierProfile", "CrierAnnouncement",
    "BroadcastResult", "TownCrierRegistry",
]
