"""World announcement banner — across-screen tiered announcements.

These announcements DO NOT live in the chatbox — they slide
across the top of the screen. Tiers escalate by importance:

  TIER_INFO       small toast, 4s, neutral
  TIER_NOTABLE    a server-first kill, town crier news
  TIER_ALERT      siege incoming, beastman raid
  TIER_CRITICAL   permadeath broadcast, server-wide crisis
  TIER_OMEN       once-a-year world event (eclipse, corruption)

Banners queue per player (so a critical announcement doesn't
overwrite an info one in mid-render). Each tier has its own
display window and visual treatment hint for the renderer.

Public surface
--------------
    BannerTier enum
    Banner dataclass
    WorldAnnouncementBanner
        .post(message, tier, audience...)
        .pending_for(player_id) -> tuple[Banner]
        .ack(player_id, banner_id)  — drop after rendered
        .tick(now_seconds) — auto-ack expired
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default per-tier display durations (seconds).
_TIER_DEFAULT_DURATIONS = {
    "tier_info": 4.0,
    "tier_notable": 6.0,
    "tier_alert": 8.0,
    "tier_critical": 12.0,
    "tier_omen": 15.0,
}


class BannerTier(str, enum.Enum):
    TIER_INFO = "tier_info"
    TIER_NOTABLE = "tier_notable"
    TIER_ALERT = "tier_alert"
    TIER_CRITICAL = "tier_critical"
    TIER_OMEN = "tier_omen"


_TIER_RANK: dict[BannerTier, int] = {
    BannerTier.TIER_INFO: 0,
    BannerTier.TIER_NOTABLE: 1,
    BannerTier.TIER_ALERT: 2,
    BannerTier.TIER_CRITICAL: 3,
    BannerTier.TIER_OMEN: 4,
}


class AudienceScope(str, enum.Enum):
    SERVER = "server"
    NATION = "nation"
    LINKSHELL = "linkshell"
    PERSONAL = "personal"


@dataclasses.dataclass(frozen=True)
class Banner:
    banner_id: str
    message: str
    tier: BannerTier
    scope: AudienceScope
    target_id: t.Optional[str]      # nation/ls/player id
    posted_at_seconds: float
    expires_at_seconds: float
    icon: str = ""
    sound_clip_id: t.Optional[str] = None


@dataclasses.dataclass
class WorldAnnouncementBanner:
    _banners: dict[str, Banner] = dataclasses.field(
        default_factory=dict,
    )
    # Per-(player_id, banner_id) ack tracker so we don't show
    # a banner twice to the same viewer.
    _acked: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)
    _next_id: int = 0

    def post(
        self, *, message: str, tier: BannerTier,
        scope: AudienceScope = AudienceScope.SERVER,
        target_id: t.Optional[str] = None,
        now_seconds: float = 0.0,
        duration_seconds: t.Optional[float] = None,
        icon: str = "",
        sound_clip_id: t.Optional[str] = None,
    ) -> t.Optional[Banner]:
        if not message:
            return None
        if scope != AudienceScope.SERVER and target_id is None:
            return None
        bid = f"banner_{self._next_id}"
        self._next_id += 1
        if duration_seconds is None:
            duration_seconds = _TIER_DEFAULT_DURATIONS[
                tier.value
            ]
        b = Banner(
            banner_id=bid, message=message, tier=tier,
            scope=scope, target_id=target_id,
            posted_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + duration_seconds
            ),
            icon=icon, sound_clip_id=sound_clip_id,
        )
        self._banners[bid] = b
        return b

    def get(self, banner_id: str) -> t.Optional[Banner]:
        return self._banners.get(banner_id)

    def _viewer_in_scope(
        self, *, banner: Banner,
        viewer_nation: t.Optional[str],
        viewer_linkshells: tuple[str, ...],
        viewer_id: str,
    ) -> bool:
        if banner.scope == AudienceScope.SERVER:
            return True
        if banner.scope == AudienceScope.NATION:
            return viewer_nation == banner.target_id
        if banner.scope == AudienceScope.LINKSHELL:
            return banner.target_id in viewer_linkshells
        if banner.scope == AudienceScope.PERSONAL:
            return banner.target_id == viewer_id
        return False

    def pending_for(
        self, *, viewer_id: str,
        viewer_nation: t.Optional[str] = None,
        viewer_linkshells: tuple[str, ...] = (),
    ) -> tuple[Banner, ...]:
        acked = self._acked.get(viewer_id, set())
        out: list[Banner] = []
        for b in self._banners.values():
            if b.banner_id in acked:
                continue
            if not self._viewer_in_scope(
                banner=b,
                viewer_nation=viewer_nation,
                viewer_linkshells=viewer_linkshells,
                viewer_id=viewer_id,
            ):
                continue
            out.append(b)
        # Highest tier first, tiebreak by posted_at desc
        out.sort(
            key=lambda b: (
                -_TIER_RANK[b.tier],
                -b.posted_at_seconds,
            ),
        )
        return tuple(out)

    def ack(
        self, *, viewer_id: str, banner_id: str,
    ) -> bool:
        if banner_id not in self._banners:
            return False
        self._acked.setdefault(
            viewer_id, set(),
        ).add(banner_id)
        return True

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for bid, b in list(self._banners.items()):
            if now_seconds >= b.expires_at_seconds:
                del self._banners[bid]
                expired.append(bid)
        # Clean up acks for expired banners
        for vid in list(self._acked.keys()):
            self._acked[vid] -= set(expired)
        return tuple(expired)

    def total_active(self) -> int:
        return len(self._banners)


__all__ = [
    "BannerTier", "AudienceScope",
    "Banner",
    "WorldAnnouncementBanner",
]
