"""Scar collection — battle scars from significant fights.

A character who's been through Maat at lvl 75, fought
Tiamat in the sky, survived a Jailer of Love defeat —
their character should LOOK like that. Demoncore tracks
scar acquisition events and renders the right scars on
the player's body.

Scars trigger when:
    DEFEAT_BY_NM        you went down to a Notorious
                        Monster (HP=0, raised). Body
                        location random by zone.
    BOSS_NEAR_DEATH     you survived a high-tier fight
                        below 5% HP at any point.
    SKILLCHAIN_BACKFIRE rare; mis-timing a chain causes
                        a self-burn scar (forearm).
    PERMADEATH_PRE      from a previous character who
                        permadied; an heir starts with
                        an inherited scar via
                        family_lineage.
    VOLUNTARY_OATH      ritual scarring as a NIN/SAM
                        coming-of-age vow (bicep).

Per-scar:
    body_part        ARM_LEFT, ARM_RIGHT, FACE,
                     CHEST, BACK, LEG_LEFT, LEG_RIGHT
    severity         FAINT / VISIBLE / DEEP
    acquired_day
    source_id        what caused it (mob_id, "vow", etc)
    visible          flag — some armor covers scars

Scars never disappear. The player can OBSCURE them with
makeup/cosmetic for a per-day fee, but they remain in
the registry.

Public surface
--------------
    Cause enum
    BodyPart enum
    Severity enum
    Scar dataclass (frozen)
    ScarCollection
        .acquire(player_id, body_part, severity, cause,
                 source_id, day) -> bool
        .obscure(player_id, scar_id, until_day) -> bool
        .scars_for(player_id, only_visible=False)
            -> list[Scar]
        .scar_count(player_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Cause(str, enum.Enum):
    DEFEAT_BY_NM = "defeat_by_nm"
    BOSS_NEAR_DEATH = "boss_near_death"
    SKILLCHAIN_BACKFIRE = "skillchain_backfire"
    PERMADEATH_PRE = "permadeath_pre"
    VOLUNTARY_OATH = "voluntary_oath"


class BodyPart(str, enum.Enum):
    FACE = "face"
    ARM_LEFT = "arm_left"
    ARM_RIGHT = "arm_right"
    CHEST = "chest"
    BACK = "back"
    LEG_LEFT = "leg_left"
    LEG_RIGHT = "leg_right"


class Severity(str, enum.Enum):
    FAINT = "faint"
    VISIBLE = "visible"
    DEEP = "deep"


@dataclasses.dataclass(frozen=True)
class Scar:
    scar_id: str
    player_id: str
    body_part: BodyPart
    severity: Severity
    cause: Cause
    source_id: str
    acquired_day: int
    obscured_until: int  # 0 = visible


@dataclasses.dataclass
class _Scar:
    body_part: BodyPart
    severity: Severity
    cause: Cause
    source_id: str
    acquired_day: int
    obscured_until: int = 0


@dataclasses.dataclass
class ScarCollection:
    _scars: dict[str, dict[str, _Scar]] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def acquire(
        self, *, player_id: str, body_part: BodyPart,
        severity: Severity, cause: Cause,
        source_id: str, day: int,
    ) -> t.Optional[str]:
        if not player_id or not source_id:
            return None
        if day < 0:
            return None
        scar_id = f"scar_{self._next_id}"
        self._next_id += 1
        if player_id not in self._scars:
            self._scars[player_id] = {}
        self._scars[player_id][scar_id] = _Scar(
            body_part=body_part, severity=severity,
            cause=cause, source_id=source_id,
            acquired_day=day,
        )
        return scar_id

    def obscure(
        self, *, player_id: str, scar_id: str,
        until_day: int,
    ) -> bool:
        if player_id not in self._scars:
            return False
        if scar_id not in self._scars[player_id]:
            return False
        if until_day < 0:
            return False
        self._scars[player_id][scar_id].obscured_until = (
            until_day
        )
        return True

    def scars_for(
        self, *, player_id: str, now_day: int = 0,
        only_visible: bool = False,
    ) -> list[Scar]:
        if player_id not in self._scars:
            return []
        out = []
        for scar_id, s in self._scars[player_id].items():
            if only_visible and s.obscured_until > now_day:
                continue
            out.append(Scar(
                scar_id=scar_id, player_id=player_id,
                body_part=s.body_part,
                severity=s.severity, cause=s.cause,
                source_id=s.source_id,
                acquired_day=s.acquired_day,
                obscured_until=s.obscured_until,
            ))
        out.sort(key=lambda s: s.acquired_day)
        return out

    def scar_count(
        self, *, player_id: str,
    ) -> int:
        if player_id not in self._scars:
            return 0
        return len(self._scars[player_id])


__all__ = [
    "Cause", "BodyPart", "Severity", "Scar",
    "ScarCollection",
]
