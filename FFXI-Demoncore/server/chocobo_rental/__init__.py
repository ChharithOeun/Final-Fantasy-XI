"""Rental chocobos at city stables.

A simple opt-in mount system for players without a personal
captured/raised chocobo. Pay gil, ride for a fixed duration,
dismount automatically when the timer expires or combat starts.

Hard rules — rental chocobos are RECREATIONAL ONLY:
* CANNOT FIGHT.       Auto-dismount on combat aggro.
* CANNOT be COMPANIONS.  No BST charm slot, no SMN avatar bond,
                          no PUP automaton pair, etc.
* CANNOT be used for MOUNTED COMBAT. mounted_combat must refuse
                                       any rental chocobo.
* CANNOT enter dungeons / instances.
* CANNOT be parked in a Mog House.
* DO refund unused minutes if dismounted at a stable.

These are enforced via the public predicates
`is_combat_eligible() -> False`, `is_companion_eligible() -> False`,
and `is_mounted_combat_eligible() -> False`. mounted_combat /
companion systems should call these before accepting a chocobo
as a combat resource.

Stables exist in major cities + outposts. Per-stable pricing
varies (frontier outposts charge more).

Public surface
--------------
    StableId enum
    RentalRecord dataclass
    rental_quote(stable, minutes) -> int     gil cost
    PlayerRentalState
        .start(stable, minutes, gil_balance, now)
        .auto_dismount(now)                  combat / timer
        .return_at_stable(now)               refund unused
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DEFAULT_RENTAL_MINUTES = 30
MAX_RENTAL_MINUTES = 120
GIL_PER_MINUTE_BASE = 8


# Hard restriction flags — these are CLASS invariants, not
# per-rental config. Every rental chocobo is recreational.
RENTAL_COMBAT_ELIGIBLE = False
RENTAL_COMPANION_ELIGIBLE = False
RENTAL_MOUNTED_COMBAT_ELIGIBLE = False


class StableId(str, enum.Enum):
    SANDORIA_CHOCOBO_STABLE = "sandoria_chocobo_stable"
    BASTOK_CHOCOBO_STABLE = "bastok_chocobo_stable"
    WINDURST_CHOCOBO_STABLE = "windurst_chocobo_stable"
    JEUNO_CHOCOBO_STABLE = "jeuno_chocobo_stable"
    SELBINA_OUTPOST_STABLE = "selbina_outpost_stable"
    MHAURA_OUTPOST_STABLE = "mhaura_outpost_stable"
    KAZHAM_OUTPOST_STABLE = "kazham_outpost_stable"


# Per-stable price multiplier. Outposts cost more.
_STABLE_MULTIPLIER: dict[StableId, float] = {
    StableId.SANDORIA_CHOCOBO_STABLE: 1.0,
    StableId.BASTOK_CHOCOBO_STABLE: 1.0,
    StableId.WINDURST_CHOCOBO_STABLE: 1.0,
    StableId.JEUNO_CHOCOBO_STABLE: 1.1,    # Jeuno premium
    StableId.SELBINA_OUTPOST_STABLE: 1.5,
    StableId.MHAURA_OUTPOST_STABLE: 1.5,
    StableId.KAZHAM_OUTPOST_STABLE: 1.6,
}


def rental_quote(*, stable: StableId, minutes: int) -> int:
    if minutes <= 0:
        return 0
    if minutes > MAX_RENTAL_MINUTES:
        return 0
    mult = _STABLE_MULTIPLIER[stable]
    return int(GIL_PER_MINUTE_BASE * minutes * mult)


@dataclasses.dataclass
class RentalRecord:
    stable: StableId
    started_at_seconds: float
    minutes_paid: int
    gil_paid: int
    state: str = "active"      # active / dismounted / returned

    def expires_at_seconds(self) -> float:
        return self.started_at_seconds + self.minutes_paid * 60.0

    def minutes_remaining(self, *, now_seconds: float) -> int:
        if self.state != "active":
            return 0
        remaining_seconds = max(
            0.0, self.expires_at_seconds() - now_seconds,
        )
        return int(remaining_seconds // 60)

    # ---- Hard rules — always False for rental chocobos -------------
    def is_combat_eligible(self) -> bool:
        return RENTAL_COMBAT_ELIGIBLE

    def is_companion_eligible(self) -> bool:
        return RENTAL_COMPANION_ELIGIBLE

    def is_mounted_combat_eligible(self) -> bool:
        return RENTAL_MOUNTED_COMBAT_ELIGIBLE


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    record: t.Optional[RentalRecord] = None
    gil_paid: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ReturnResult:
    accepted: bool
    minutes_unused: int = 0
    gil_refunded: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerRentalState:
    player_id: str
    current: t.Optional[RentalRecord] = None

    @property
    def is_mounted(self) -> bool:
        return self.current is not None and self.current.state == "active"

    def start(
        self, *, stable: StableId,
        minutes: int = DEFAULT_RENTAL_MINUTES,
        gil_balance: int, now_seconds: float = 0.0,
    ) -> StartResult:
        if self.is_mounted:
            return StartResult(False, reason="already mounted")
        if minutes <= 0 or minutes > MAX_RENTAL_MINUTES:
            return StartResult(False, reason="invalid minutes")
        cost = rental_quote(stable=stable, minutes=minutes)
        if gil_balance < cost:
            return StartResult(False, reason="insufficient gil")
        rec = RentalRecord(
            stable=stable, started_at_seconds=now_seconds,
            minutes_paid=minutes, gil_paid=cost,
        )
        self.current = rec
        return StartResult(True, record=rec, gil_paid=cost)

    def auto_dismount(self, *, now_seconds: float,
                       reason: str = "combat") -> bool:
        """Combat or timer expiry triggers auto-dismount.
        Unused minutes are NOT refunded — refund only at stable."""
        if not self.is_mounted:
            return False
        self.current.state = "dismounted"
        return True

    def return_at_stable(
        self, *, stable: StableId, now_seconds: float,
    ) -> ReturnResult:
        if self.current is None or self.current.state != "active":
            return ReturnResult(False, reason="not actively mounted")
        if stable != self.current.stable:
            return ReturnResult(
                False, reason="must return at rental stable",
            )
        unused = self.current.minutes_remaining(now_seconds=now_seconds)
        per_minute_gil = (
            self.current.gil_paid // max(1, self.current.minutes_paid)
        )
        refund = unused * per_minute_gil
        self.current.state = "returned"
        return ReturnResult(
            True, minutes_unused=unused, gil_refunded=refund,
        )


# ---------------------------------------------------------------------
# Integration guards — other modules call these before accepting a
# rental chocobo as a combat / companion / mounted-combat resource.
# ---------------------------------------------------------------------

def is_rental_combat_eligible(rental: RentalRecord) -> bool:
    """Always False. Rental chocobos cannot fight."""
    return rental.is_combat_eligible()


def is_rental_companion_eligible(rental: RentalRecord) -> bool:
    """Always False. Rental chocobos cannot be BST/SMN/PUP companions."""
    return rental.is_companion_eligible()


def is_rental_mounted_combat_eligible(rental: RentalRecord) -> bool:
    """Always False. mounted_combat must refuse rental chocobos."""
    return rental.is_mounted_combat_eligible()


def reject_for_combat(rental: RentalRecord) -> str:
    """Standard error string when a caller tries to use a rental
    chocobo for any combat purpose."""
    return (
        "Rental chocobos are recreational only — "
        "they cannot fight, be companions, or join mounted combat. "
        "Use a captured or bred chocobo instead."
    )


__all__ = [
    "DEFAULT_RENTAL_MINUTES", "MAX_RENTAL_MINUTES",
    "GIL_PER_MINUTE_BASE",
    "RENTAL_COMBAT_ELIGIBLE", "RENTAL_COMPANION_ELIGIBLE",
    "RENTAL_MOUNTED_COMBAT_ELIGIBLE",
    "StableId", "RentalRecord",
    "StartResult", "ReturnResult",
    "rental_quote", "PlayerRentalState",
    "is_rental_combat_eligible",
    "is_rental_companion_eligible",
    "is_rental_mounted_combat_eligible",
    "reject_for_combat",
]
