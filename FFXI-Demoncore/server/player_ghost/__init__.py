"""Player ghost — post-permadeath haunting mechanic.

When a player permadies, their CHARACTER fades — but the soul
lingers as a ghost for a configurable period. Ghosts can:
* HAUNT the player who killed them (debuff aura when within range)
* WHISPER cryptic warnings to other players who step near the
  death site
* MARK their death-site as a memorial pin on map_discovery
* TRANSFER residual mood/grudge to npc_emotional_cascade

After the haunt window expires, the ghost moves on. This is the
soft-tail of permadeath: not a do-over, but a final flicker of
agency the dead get to spend.

Public surface
--------------
    GhostState enum
    HauntKind enum
    PlayerGhost dataclass
    HauntApplication dataclass
    PlayerGhostRegistry
        .summon_ghost(player_id, killer_id, death_site, ...)
        .apply_haunt(ghost_id, victim_id, kind, intensity)
        .whisper(ghost_id, listener_id) -> Optional[message]
        .tick(elapsed_seconds) -> tuple[expired ghosts]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default haunt window — 7 in-game days (7*24*3600 s).
DEFAULT_HAUNT_WINDOW_SECONDS = 7 * 24 * 3600
DEFAULT_HAUNT_RANGE = 30          # game-units
MAX_HAUNT_INTENSITY = 100


class GhostState(str, enum.Enum):
    LINGERING = "lingering"
    HAUNTING = "haunting"
    WHISPERING = "whispering"
    DEPARTED = "departed"        # haunt window expired


class HauntKind(str, enum.Enum):
    DEBUFF_AURA = "debuff_aura"
    SUDDEN_CHILL = "sudden_chill"
    LURING_VOICE = "luring_voice"
    NIGHTMARE = "nightmare"
    CURSE_BREATH = "curse_breath"


# Whisper templates per ghost mood — one is picked deterministically
# by hashing the (ghost_id, listener_id) pair.
_WHISPER_LIBRARY: tuple[str, ...] = (
    "Don't take the eastern path...",
    "Watch the trees, they aren't trees.",
    "I died here. Don't.",
    "It came from the rocks.",
    "Three of them. Be ready.",
    "Listen — listen now.",
    "Run.",
    "Help him, please.",
)


@dataclasses.dataclass
class PlayerGhost:
    ghost_id: str
    deceased_player_id: str
    killer_id: t.Optional[str]
    death_zone_id: str
    death_site_x: float = 0.0
    death_site_y: float = 0.0
    death_site_z: float = 0.0
    summoned_at_seconds: float = 0.0
    expires_at_seconds: float = 0.0
    state: GhostState = GhostState.LINGERING
    haunts_applied: int = 0
    whispers_heard_by: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass(frozen=True)
class HauntApplication:
    ghost_id: str
    victim_id: str
    kind: HauntKind
    intensity: int
    note: str = ""


@dataclasses.dataclass(frozen=True)
class GhostExpiration:
    ghost_id: str
    deceased_player_id: str
    expired_at_seconds: float


@dataclasses.dataclass
class PlayerGhostRegistry:
    haunt_window_seconds: float = DEFAULT_HAUNT_WINDOW_SECONDS
    haunt_range: float = DEFAULT_HAUNT_RANGE
    _ghosts: dict[str, PlayerGhost] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def summon_ghost(
        self, *, deceased_player_id: str,
        killer_id: t.Optional[str] = None,
        death_zone_id: str,
        death_site_x: float = 0.0,
        death_site_y: float = 0.0,
        death_site_z: float = 0.0,
        now_seconds: float = 0.0,
    ) -> t.Optional[PlayerGhost]:
        # One ghost per player at a time
        for g in self._ghosts.values():
            if (
                g.deceased_player_id == deceased_player_id
                and g.state != GhostState.DEPARTED
            ):
                return None
        gid = f"ghost_{self._next_id}"
        self._next_id += 1
        ghost = PlayerGhost(
            ghost_id=gid,
            deceased_player_id=deceased_player_id,
            killer_id=killer_id,
            death_zone_id=death_zone_id,
            death_site_x=death_site_x,
            death_site_y=death_site_y,
            death_site_z=death_site_z,
            summoned_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + self.haunt_window_seconds
            ),
        )
        self._ghosts[gid] = ghost
        return ghost

    def get(self, ghost_id: str) -> t.Optional[PlayerGhost]:
        return self._ghosts.get(ghost_id)

    def ghost_for_player(
        self, deceased_player_id: str,
    ) -> t.Optional[PlayerGhost]:
        for g in self._ghosts.values():
            if (
                g.deceased_player_id == deceased_player_id
                and g.state != GhostState.DEPARTED
            ):
                return g
        return None

    def apply_haunt(
        self, *, ghost_id: str, victim_id: str,
        kind: HauntKind, intensity: int,
    ) -> t.Optional[HauntApplication]:
        ghost = self._ghosts.get(ghost_id)
        if ghost is None:
            return None
        if ghost.state == GhostState.DEPARTED:
            return None
        if intensity <= 0:
            return None
        clamped = min(intensity, MAX_HAUNT_INTENSITY)
        ghost.state = GhostState.HAUNTING
        ghost.haunts_applied += 1
        return HauntApplication(
            ghost_id=ghost_id, victim_id=victim_id,
            kind=kind, intensity=clamped,
        )

    def whisper(
        self, *, ghost_id: str, listener_id: str,
    ) -> t.Optional[str]:
        ghost = self._ghosts.get(ghost_id)
        if ghost is None:
            return None
        if ghost.state == GhostState.DEPARTED:
            return None
        ghost.state = GhostState.WHISPERING
        if listener_id not in ghost.whispers_heard_by:
            ghost.whispers_heard_by.append(listener_id)
        # Deterministic pick from library
        idx = abs(hash((ghost_id, listener_id))) % len(
            _WHISPER_LIBRARY,
        )
        return _WHISPER_LIBRARY[idx]

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[GhostExpiration, ...]:
        expired: list[GhostExpiration] = []
        for ghost in self._ghosts.values():
            if ghost.state == GhostState.DEPARTED:
                continue
            if now_seconds >= ghost.expires_at_seconds:
                ghost.state = GhostState.DEPARTED
                expired.append(GhostExpiration(
                    ghost_id=ghost.ghost_id,
                    deceased_player_id=(
                        ghost.deceased_player_id
                    ),
                    expired_at_seconds=now_seconds,
                ))
        return tuple(expired)

    def total_active_ghosts(self) -> int:
        return sum(
            1 for g in self._ghosts.values()
            if g.state != GhostState.DEPARTED
        )

    def total_ghosts_ever(self) -> int:
        return len(self._ghosts)


__all__ = [
    "DEFAULT_HAUNT_WINDOW_SECONDS",
    "DEFAULT_HAUNT_RANGE", "MAX_HAUNT_INTENSITY",
    "GhostState", "HauntKind",
    "PlayerGhost", "HauntApplication",
    "GhostExpiration", "PlayerGhostRegistry",
]
