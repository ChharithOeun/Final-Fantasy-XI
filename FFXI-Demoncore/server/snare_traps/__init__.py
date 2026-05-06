"""Snare traps — patient hunting that pays in your sleep.

Active hunting (with bow) is a player-time activity:
you're at the keyboard, you're tracking, you're loosing
arrows. Trapping is the opposite — you set the snare,
walk away, come back in an hour, and check what (if
anything) the wilderness gave you.

Each trap kind has a target weight class and a catch
chance per check. Heavier traps catch heavier game; a
foot snare meant for a coney won't hold a manticore,
and a deadfall built for a dhalmel triggers wastefully
on a passing rabbit.

Trap kinds
----------
    FOOT_SNARE     SMALL game (rabbit, coney)
    SPRING_NOOSE   SMALL/MED (fowl, beaver)
    PIT_TRAP       MED/LARGE (boar, deer)
    DEADFALL       MED/LARGE (deer, dhalmel)
    NET_TRAP       SMALL/MED only — can't hold large
    BAITED_CAGE    SMALL/MED, baited boost (rabbit, fox)

Outcomes
--------
    EMPTY        nothing checked in
    PREY_CAUGHT  successful catch — quarry_id reported
    SPRUNG_EMPTY trap triggered but quarry escaped/scared off
    DESTROYED    something heavy broke the trap

Public surface
--------------
    TrapKind enum
    WeightClass enum (SMALL/MEDIUM/LARGE)
    CheckOutcome enum
    SnareTrap dataclass (mutable)
    CheckResult dataclass (frozen)
    SnareTrapRegistry
        .place(trap_id, owner_id, kind, zone, x, y,
               baited, placed_at) -> bool
        .check(trap_id, traffic_kind, traffic_weight,
               now) -> CheckResult
        .remove(trap_id, by_owner_id) -> bool
        .traps_in_zone(zone) -> list[SnareTrap]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WeightClass(str, enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class TrapKind(str, enum.Enum):
    FOOT_SNARE = "foot_snare"
    SPRING_NOOSE = "spring_noose"
    PIT_TRAP = "pit_trap"
    DEADFALL = "deadfall"
    NET_TRAP = "net_trap"
    BAITED_CAGE = "baited_cage"


class CheckOutcome(str, enum.Enum):
    EMPTY = "empty"
    PREY_CAUGHT = "prey_caught"
    SPRUNG_EMPTY = "sprung_empty"
    DESTROYED = "destroyed"


# Which weight classes each trap can hold. A larger
# animal hitting a too-light trap usually destroys it.
_TRAP_HOLDS: dict[TrapKind, set[WeightClass]] = {
    TrapKind.FOOT_SNARE: {WeightClass.SMALL},
    TrapKind.SPRING_NOOSE: {WeightClass.SMALL, WeightClass.MEDIUM},
    TrapKind.PIT_TRAP: {WeightClass.MEDIUM, WeightClass.LARGE},
    TrapKind.DEADFALL: {WeightClass.MEDIUM, WeightClass.LARGE},
    TrapKind.NET_TRAP: {WeightClass.SMALL, WeightClass.MEDIUM},
    TrapKind.BAITED_CAGE: {WeightClass.SMALL, WeightClass.MEDIUM},
}

# Bait gives BAITED_CAGE its appeal — it nearly always
# catches if a target-weight animal walked by.
_BAIT_BONUS_KINDS: set[TrapKind] = {TrapKind.BAITED_CAGE}


@dataclasses.dataclass
class SnareTrap:
    trap_id: str
    owner_id: str
    kind: TrapKind
    zone: str
    x: float
    y: float
    baited: bool
    placed_at: int
    armed: bool


@dataclasses.dataclass(frozen=True)
class CheckResult:
    outcome: CheckOutcome
    quarry_id: str
    trap_destroyed: bool


_EMPTY_RESULT = CheckResult(
    outcome=CheckOutcome.EMPTY, quarry_id="",
    trap_destroyed=False,
)


@dataclasses.dataclass
class SnareTrapRegistry:
    _traps: dict[str, SnareTrap] = dataclasses.field(
        default_factory=dict,
    )

    def place(
        self, *, trap_id: str, owner_id: str,
        kind: TrapKind, zone: str,
        x: float, y: float,
        baited: bool, placed_at: int,
    ) -> bool:
        if not trap_id or not owner_id or not zone:
            return False
        if trap_id in self._traps:
            return False
        self._traps[trap_id] = SnareTrap(
            trap_id=trap_id, owner_id=owner_id,
            kind=kind, zone=zone, x=x, y=y,
            baited=baited, placed_at=placed_at,
            armed=True,
        )
        return True

    def check(
        self, *, trap_id: str,
        traffic_kind: str,
        traffic_weight: WeightClass,
        now: int,
    ) -> CheckResult:
        t_obj = self._traps.get(trap_id)
        if t_obj is None:
            return _EMPTY_RESULT
        if not t_obj.armed:
            return _EMPTY_RESULT
        # No traffic at all → trap stays armed, returns empty.
        if not traffic_kind:
            return _EMPTY_RESULT
        holds = _TRAP_HOLDS[t_obj.kind]
        # weight too heavy → trap destroyed by overloaded prey
        if traffic_weight == WeightClass.LARGE and \
                WeightClass.LARGE not in holds:
            t_obj.armed = False
            return CheckResult(
                outcome=CheckOutcome.DESTROYED,
                quarry_id=traffic_kind,
                trap_destroyed=True,
            )
        # right weight → catch (baited cage always, others
        # are inherently caught here since traffic_kind is
        # "the animal that walked into the trigger area")
        if traffic_weight in holds:
            t_obj.armed = False
            if t_obj.kind in _BAIT_BONUS_KINDS and t_obj.baited:
                # baited cage is reliable
                return CheckResult(
                    outcome=CheckOutcome.PREY_CAUGHT,
                    quarry_id=traffic_kind,
                    trap_destroyed=False,
                )
            return CheckResult(
                outcome=CheckOutcome.PREY_CAUGHT,
                quarry_id=traffic_kind,
                trap_destroyed=False,
            )
        # wrong weight (too small) → trap sprung uselessly
        t_obj.armed = False
        return CheckResult(
            outcome=CheckOutcome.SPRUNG_EMPTY,
            quarry_id="",
            trap_destroyed=False,
        )

    def remove(
        self, *, trap_id: str, by_owner_id: str,
    ) -> bool:
        t_obj = self._traps.get(trap_id)
        if t_obj is None:
            return False
        if t_obj.owner_id != by_owner_id:
            return False
        del self._traps[trap_id]
        return True

    def traps_in_zone(
        self, *, zone: str,
    ) -> list[SnareTrap]:
        return [t for t in self._traps.values() if t.zone == zone]

    def get(self, *, trap_id: str) -> t.Optional[SnareTrap]:
        return self._traps.get(trap_id)

    def total_traps(self) -> int:
        return len(self._traps)


__all__ = [
    "WeightClass", "TrapKind", "CheckOutcome",
    "SnareTrap", "CheckResult", "SnareTrapRegistry",
]
