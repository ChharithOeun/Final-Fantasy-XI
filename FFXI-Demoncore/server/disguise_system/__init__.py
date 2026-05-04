"""Disguise system — temporary alias of identity.

A player can DISGUISE themselves: alter the visible name, race,
or job-string shown on their nameplate to other players. Useful
for RP, infiltration, and outlaw stealth (an outlaw can hide
their wanted poster temporarily by disguising — at a faith /
honor cost when discovered).

A disguise has a duration. While ACTIVE, the player's name plate
displays the alias. The original identity is recoverable via
PIERCE_DISGUISE — a high-perception NPC, a player with high
INT, or anti-disguise gear can reveal them. Pierce events log a
witness; multiple witnesses build toward exposure.

Public surface
--------------
    DisguiseKind enum
    PierceResult enum
    Disguise dataclass
    DisguiseSystem
        .disguise(player_id, alias_name, alias_race, alias_job,
                  duration, kind)
        .reveal(player_id) — voluntary
        .pierce(viewer_id, target_id, perception)
        .visible_identity(viewer_id, target_id) -> name/race/job
        .tick(now_seconds) -> tuple[expired]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
DEFAULT_PIERCE_THRESHOLD = 100
EXPOSURE_PIERCE_COUNT = 3
DEFAULT_MAX_DURATION = 30 * 60.0    # 30 minutes


class DisguiseKind(str, enum.Enum):
    RP_ONLY = "rp_only"               # cosmetic
    INFILTRATION = "infiltration"     # plot/quest
    OUTLAW_STEALTH = "outlaw_stealth"  # hides wanted status
    DEMON_GLAMOUR = "demon_glamour"   # endgame magical


class PierceResult(str, enum.Enum):
    REVEALED = "revealed"
    PARTIAL_PIERCE = "partial_pierce"
    NO_EFFECT = "no_effect"


@dataclasses.dataclass
class Disguise:
    player_id: str
    kind: DisguiseKind
    alias_name: str
    alias_race: str
    alias_job: str
    started_at_seconds: float
    expires_at_seconds: float
    is_active: bool = True
    pierces: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass(frozen=True)
class VisibleIdentity:
    name: str
    race: str
    job: str
    is_disguised_view: bool


@dataclasses.dataclass
class DisguiseSystem:
    pierce_threshold: int = DEFAULT_PIERCE_THRESHOLD
    exposure_pierce_count: int = EXPOSURE_PIERCE_COUNT
    max_duration: float = DEFAULT_MAX_DURATION
    _active: dict[str, Disguise] = dataclasses.field(
        default_factory=dict,
    )
    # Real identities of players (for unmasked rendering).
    _real_identity: dict[
        str, tuple[str, str, str],
    ] = dataclasses.field(default_factory=dict)

    def register_real_identity(
        self, *, player_id: str,
        name: str, race: str, job: str,
    ) -> bool:
        if not name or not race:
            return False
        self._real_identity[player_id] = (name, race, job)
        return True

    def disguise(
        self, *, player_id: str,
        kind: DisguiseKind,
        alias_name: str,
        alias_race: str,
        alias_job: str,
        duration_seconds: float,
        now_seconds: float = 0.0,
    ) -> t.Optional[Disguise]:
        if player_id in self._active:
            return None
        if duration_seconds <= 0:
            return None
        if duration_seconds > self.max_duration:
            duration_seconds = self.max_duration
        if not alias_name or not alias_race:
            return None
        d = Disguise(
            player_id=player_id, kind=kind,
            alias_name=alias_name,
            alias_race=alias_race,
            alias_job=alias_job,
            started_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + duration_seconds
            ),
            is_active=True,
        )
        self._active[player_id] = d
        return d

    def reveal(
        self, *, player_id: str,
    ) -> bool:
        d = self._active.get(player_id)
        if d is None:
            return False
        d.is_active = False
        del self._active[player_id]
        return True

    def is_disguised(
        self, *, player_id: str,
    ) -> bool:
        return player_id in self._active

    def pierce(
        self, *, viewer_id: str, target_id: str,
        perception: int,
    ) -> PierceResult:
        d = self._active.get(target_id)
        if d is None:
            return PierceResult.NO_EFFECT
        if viewer_id == target_id:
            return PierceResult.NO_EFFECT
        if perception < self.pierce_threshold:
            return PierceResult.NO_EFFECT
        # Deduplicate by viewer
        if viewer_id in d.pierces:
            return PierceResult.PARTIAL_PIERCE
        d.pierces.append(viewer_id)
        if len(d.pierces) >= self.exposure_pierce_count:
            d.is_active = False
            del self._active[target_id]
            return PierceResult.REVEALED
        return PierceResult.PARTIAL_PIERCE

    def visible_identity(
        self, *, viewer_id: str, target_id: str,
    ) -> t.Optional[VisibleIdentity]:
        real = self._real_identity.get(target_id)
        if real is None:
            return None
        d = self._active.get(target_id)
        # If viewer pierced this disguise individually, they
        # see the real identity even while it's active for others.
        viewer_already_pierced = (
            d is not None and viewer_id in d.pierces
        )
        # Self-view is always real.
        if viewer_id == target_id:
            return VisibleIdentity(
                name=real[0], race=real[1], job=real[2],
                is_disguised_view=False,
            )
        if d is None or viewer_already_pierced:
            return VisibleIdentity(
                name=real[0], race=real[1], job=real[2],
                is_disguised_view=False,
            )
        return VisibleIdentity(
            name=d.alias_name,
            race=d.alias_race,
            job=d.alias_job,
            is_disguised_view=True,
        )

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for pid, d in list(self._active.items()):
            if now_seconds >= d.expires_at_seconds:
                d.is_active = False
                del self._active[pid]
                expired.append(pid)
        return tuple(expired)

    def total_active_disguises(self) -> int:
        return len(self._active)


__all__ = [
    "DEFAULT_PIERCE_THRESHOLD",
    "EXPOSURE_PIERCE_COUNT",
    "DEFAULT_MAX_DURATION",
    "DisguiseKind", "PierceResult",
    "Disguise", "VisibleIdentity",
    "DisguiseSystem",
]
