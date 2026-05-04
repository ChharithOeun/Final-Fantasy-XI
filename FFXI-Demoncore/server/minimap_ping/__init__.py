"""Minimap ping — party-shared map markers.

A player taps a point on the minimap; a brief pulse appears for
them and (for shared pings) for everyone in their party. This is
the in-game equivalent of a MOBA ping — fast tactical signaling
that doesn't require typing in chat.

Pings carry an INTENT (ATTACK_HERE / DEFEND_HERE / RETREAT /
LOOT / WAYPOINT / DANGER) which drives the icon and color in
the renderer. Each ping has a brief lifetime; tick() culls
expired pings.

Anti-spam: a player has a short cooldown between pings, and the
total live pings per player is capped.

Public surface
--------------
    PingIntent enum
    PingScope enum
    Ping dataclass
    PingResult dataclass
    MinimapPingSystem
        .place_ping(player_id, zone_id, x, y, intent, scope,
                    party_member_ids)
        .visible_to(viewer_id, viewer_zone_id) -> tuple[Ping]
        .tick(now_seconds) -> tuple[expired ids]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults.
DEFAULT_PING_LIFETIME_SECONDS = 6.0
DEFAULT_PING_COOLDOWN_SECONDS = 1.5
MAX_LIVE_PINGS_PER_PLAYER = 3


class PingIntent(str, enum.Enum):
    ATTACK_HERE = "attack_here"
    DEFEND_HERE = "defend_here"
    RETREAT = "retreat"
    LOOT = "loot"
    WAYPOINT = "waypoint"
    DANGER = "danger"
    GENERIC = "generic"


class PingScope(str, enum.Enum):
    SELF = "self"
    PARTY = "party"
    ALLIANCE = "alliance"


_INTENT_COLOR: dict[PingIntent, str] = {
    PingIntent.ATTACK_HERE: "red",
    PingIntent.DEFEND_HERE: "blue",
    PingIntent.RETREAT: "yellow",
    PingIntent.LOOT: "gold",
    PingIntent.WAYPOINT: "cyan",
    PingIntent.DANGER: "magenta",
    PingIntent.GENERIC: "white",
}


@dataclasses.dataclass(frozen=True)
class Ping:
    ping_id: str
    placer_id: str
    zone_id: str
    x: float
    y: float
    z: float
    intent: PingIntent
    color: str
    scope: PingScope
    party_member_ids: tuple[str, ...]
    placed_at_seconds: float
    expires_at_seconds: float


@dataclasses.dataclass(frozen=True)
class PingResult:
    accepted: bool
    ping: t.Optional[Ping] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MinimapPingSystem:
    lifetime_seconds: float = DEFAULT_PING_LIFETIME_SECONDS
    cooldown_seconds: float = DEFAULT_PING_COOLDOWN_SECONDS
    max_live_per_player: int = MAX_LIVE_PINGS_PER_PLAYER
    _pings: dict[str, Ping] = dataclasses.field(
        default_factory=dict,
    )
    _last_ping_at: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def place_ping(
        self, *, placer_id: str, zone_id: str,
        x: float, y: float, z: float = 0.0,
        intent: PingIntent = PingIntent.GENERIC,
        scope: PingScope = PingScope.PARTY,
        party_member_ids: tuple[str, ...] = (),
        now_seconds: float = 0.0,
    ) -> PingResult:
        # Cooldown gate
        last = self._last_ping_at.get(placer_id)
        if (
            last is not None
            and (now_seconds - last) < self.cooldown_seconds
        ):
            return PingResult(
                False, reason="ping cooldown",
            )
        # Live-ping cap
        live_count = sum(
            1 for p in self._pings.values()
            if p.placer_id == placer_id
        )
        if live_count >= self.max_live_per_player:
            return PingResult(
                False, reason="too many live pings",
            )
        pid = f"ping_{self._next_id}"
        self._next_id += 1
        ping = Ping(
            ping_id=pid, placer_id=placer_id,
            zone_id=zone_id, x=x, y=y, z=z,
            intent=intent,
            color=_INTENT_COLOR[intent],
            scope=scope,
            party_member_ids=party_member_ids,
            placed_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + self.lifetime_seconds
            ),
        )
        self._pings[pid] = ping
        self._last_ping_at[placer_id] = now_seconds
        return PingResult(accepted=True, ping=ping)

    def get(self, ping_id: str) -> t.Optional[Ping]:
        return self._pings.get(ping_id)

    def visible_to(
        self, *, viewer_id: str, viewer_zone_id: str,
    ) -> tuple[Ping, ...]:
        out: list[Ping] = []
        for ping in self._pings.values():
            if ping.zone_id != viewer_zone_id:
                continue
            if ping.scope == PingScope.SELF:
                if ping.placer_id == viewer_id:
                    out.append(ping)
                continue
            # PARTY / ALLIANCE — viewer must be the placer or
            # in the placer's listed party_member_ids
            if (
                viewer_id == ping.placer_id
                or viewer_id in ping.party_member_ids
            ):
                out.append(ping)
        # Most recent first
        out.sort(
            key=lambda p: -p.placed_at_seconds,
        )
        return tuple(out)

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for pid, ping in list(self._pings.items()):
            if now_seconds >= ping.expires_at_seconds:
                del self._pings[pid]
                expired.append(pid)
        return tuple(expired)

    def total_active(self) -> int:
        return len(self._pings)


__all__ = [
    "DEFAULT_PING_LIFETIME_SECONDS",
    "DEFAULT_PING_COOLDOWN_SECONDS",
    "MAX_LIVE_PINGS_PER_PLAYER",
    "PingIntent", "PingScope",
    "Ping", "PingResult",
    "MinimapPingSystem",
]
