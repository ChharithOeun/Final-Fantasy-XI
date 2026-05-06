"""Sahagin Kingdom — the smallest, meanest sea power.

The Sahagin hold the smallest territory of any underwater
race, but their reach is enormous. A single fortified
capital city — KING'S BROOD — sits in a deep coral trench
nobody can siege without a full alliance. Around that one
fixed throne, dozens of pocket resistance bases dot the
sea floor in zones where the Sahagin nominally have no
control. They appear, hit, and vanish.

This module defines the kingdom shape — capital plus
satellite presence — and exposes territory queries used
by raid spawn logic, mermaid hostility, and the bounty
system.

Public surface
--------------
    SahaginPresence enum
    Capital dataclass (frozen)
    SahaginKingdom
        .set_capital(zone_id, band, fortification)
        .add_presence(zone_id, band, presence)
        .presence_in(zone_id, band) -> SahaginPresence
        .all_presence_zones() -> tuple[(zone, band, presence), ...]
        .territory_count() -> int
        .is_capital(zone_id, band) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SahaginPresence(str, enum.Enum):
    NONE = "none"
    SCOUT = "scout"             # one or two recon swimmers
    CELL = "cell"               # full resistance cell
    STRONGHOLD = "stronghold"   # fortified outpost
    CAPITAL = "capital"         # KING'S BROOD itself


@dataclasses.dataclass(frozen=True)
class Capital:
    zone_id: str
    band: int
    fortification: int   # 0..100, defenders' tactical strength


_PresenceCell = tuple[str, int]


@dataclasses.dataclass
class SahaginKingdom:
    _capital: t.Optional[Capital] = None
    _presence: dict[_PresenceCell, SahaginPresence] = dataclasses.field(
        default_factory=dict,
    )

    def set_capital(
        self, *, zone_id: str, band: int,
        fortification: int = 100,
    ) -> bool:
        if not zone_id:
            return False
        if fortification < 0 or fortification > 100:
            return False
        self._capital = Capital(
            zone_id=zone_id, band=band, fortification=fortification,
        )
        # capital cell auto-marks presence as CAPITAL
        self._presence[(zone_id, band)] = SahaginPresence.CAPITAL
        return True

    def add_presence(
        self, *, zone_id: str, band: int,
        presence: SahaginPresence,
    ) -> bool:
        if not zone_id:
            return False
        if presence == SahaginPresence.CAPITAL:
            return False  # only set_capital can place capital
        if (
            self._capital is not None
            and self._capital.zone_id == zone_id
            and self._capital.band == band
        ):
            return False  # don't downgrade the capital
        self._presence[(zone_id, band)] = presence
        return True

    def presence_in(
        self, *, zone_id: str, band: int,
    ) -> SahaginPresence:
        return self._presence.get(
            (zone_id, band), SahaginPresence.NONE,
        )

    def all_presence_zones(
        self,
    ) -> tuple[tuple[str, int, SahaginPresence], ...]:
        return tuple(
            (z, b, p) for (z, b), p in self._presence.items()
        )

    def territory_count(self) -> int:
        return len(self._presence)

    def is_capital(
        self, *, zone_id: str, band: int,
    ) -> bool:
        if self._capital is None:
            return False
        return (
            self._capital.zone_id == zone_id
            and self._capital.band == band
        )


__all__ = [
    "SahaginPresence", "Capital", "SahaginKingdom",
]
