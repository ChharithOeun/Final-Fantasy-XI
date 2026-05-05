"""Oxygen system — underwater breath meter.

Going below the SURFACE band starts a per-player breath
clock. Default capacity is 60s. Gear stacks ADDITIVELY:
diving_suit gives +180s, depth_gear gives +60s, pearl
amulet gives +30s. Some mobs (kraken cult drowners, deep
sirens) trigger extra drain on hit.

Returning to the SURFACE band — or entering a registered
breathing pocket — restores instantly.

When oxygen hits zero the player starts taking drowning
damage; that hook just exposes is_drowning so other
modules (damage_physics, visible_health) can layer on
the actual hit. Keeping the bookkeeping pure here means
the same breath meter works for hardcore-mode ironman
runs and for the casual sub-tour difficulty alike.

Public surface
--------------
    GearKind str enum
    OxygenStatus dataclass (frozen)
    OxygenSystem
        .register(player_id)
        .equip_gear(player_id, gear)
        .unequip_gear(player_id, gear)
        .set_band(player_id, band, now_seconds)
        .tick(player_id, now_seconds) -> OxygenStatus
        .apply_drain(player_id, drain_seconds, now_seconds)
        .surface_or_pocket(player_id, now_seconds)
        .is_drowning(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GearKind(str, enum.Enum):
    DIVING_SUIT = "diving_suit"
    DEPTH_GEAR = "depth_gear"
    PEARL_AMULET = "pearl_amulet"
    BREATHING_REED = "breathing_reed"


BASE_OXYGEN_SECONDS = 60.0
GEAR_BONUS_SECONDS: dict[GearKind, float] = {
    GearKind.DIVING_SUIT: 180.0,
    GearKind.DEPTH_GEAR: 60.0,
    GearKind.PEARL_AMULET: 30.0,
    GearKind.BREATHING_REED: 15.0,
}
SURFACE_BAND = 0


@dataclasses.dataclass
class _Player:
    player_id: str
    gear: set[GearKind] = dataclasses.field(default_factory=set)
    band: int = SURFACE_BAND
    last_tick: int = 0
    remaining: float = BASE_OXYGEN_SECONDS
    drowning: bool = False


@dataclasses.dataclass(frozen=True)
class OxygenStatus:
    remaining_seconds: float
    capacity_seconds: float
    drowning: bool


def _capacity_for(gear: t.Iterable[GearKind]) -> float:
    return BASE_OXYGEN_SECONDS + sum(
        GEAR_BONUS_SECONDS[g] for g in gear
    )


@dataclasses.dataclass
class OxygenSystem:
    _players: dict[str, _Player] = dataclasses.field(default_factory=dict)

    def register(self, *, player_id: str) -> bool:
        if not player_id or player_id in self._players:
            return False
        self._players[player_id] = _Player(player_id=player_id)
        return True

    def equip_gear(
        self, *, player_id: str, gear: GearKind,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        before_cap = _capacity_for(p.gear)
        p.gear.add(gear)
        after_cap = _capacity_for(p.gear)
        # extending capacity also extends remaining proportionally
        # the floor is the previous remaining; you don't lose air
        p.remaining = min(after_cap, p.remaining + (after_cap - before_cap))
        return True

    def unequip_gear(
        self, *, player_id: str, gear: GearKind,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None or gear not in p.gear:
            return False
        p.gear.discard(gear)
        # cap your remaining to new (smaller) capacity
        p.remaining = min(p.remaining, _capacity_for(p.gear))
        return True

    def set_band(
        self, *, player_id: str,
        band: int, now_seconds: int,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        # advance the clock first against the OLD band
        self._advance(p, now_seconds)
        p.band = band
        if band == SURFACE_BAND:
            p.remaining = _capacity_for(p.gear)
            p.drowning = False
        return True

    def tick(
        self, *, player_id: str, now_seconds: int,
    ) -> t.Optional[OxygenStatus]:
        p = self._players.get(player_id)
        if p is None:
            return None
        self._advance(p, now_seconds)
        return OxygenStatus(
            remaining_seconds=p.remaining,
            capacity_seconds=_capacity_for(p.gear),
            drowning=p.drowning,
        )

    def apply_drain(
        self, *, player_id: str,
        drain_seconds: float,
        now_seconds: int,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        self._advance(p, now_seconds)
        p.remaining = max(0.0, p.remaining - drain_seconds)
        if p.remaining == 0.0:
            p.drowning = True
        return True

    def surface_or_pocket(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        p.last_tick = now_seconds
        p.remaining = _capacity_for(p.gear)
        p.drowning = False
        return True

    def is_drowning(self, *, player_id: str) -> bool:
        p = self._players.get(player_id)
        return bool(p and p.drowning)

    # internal: advance the breath clock to now against current band
    def _advance(self, p: _Player, now_seconds: int) -> None:
        elapsed = max(0, now_seconds - p.last_tick)
        p.last_tick = now_seconds
        if p.band == SURFACE_BAND:
            # at surface, refill instead of drain
            p.remaining = _capacity_for(p.gear)
            p.drowning = False
            return
        # underwater: 1 second of real time = 1s of breath
        p.remaining = max(0.0, p.remaining - elapsed)
        if p.remaining == 0.0:
            p.drowning = True


__all__ = [
    "GearKind", "OxygenStatus", "OxygenSystem",
    "BASE_OXYGEN_SECONDS", "GEAR_BONUS_SECONDS",
    "SURFACE_BAND",
]
