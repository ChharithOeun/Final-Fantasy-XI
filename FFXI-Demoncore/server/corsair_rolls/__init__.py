"""Corsair phantom rolls.

Corsair gambles on a 6-sided "phantom die." The roll value
maps to a buff effect strength via the roll's effect_table.
Players can stop on the initial roll, or "double-up" to add a
fresh d6. If the running total exceeds 11, the roll BUSTS —
all stacks are wiped and a recast lockout is applied.

Each roll has:
* a Lucky number (extra-bonus result)
* an Unlucky number (penalty result)
* a base effect that scales with the total

Public surface
--------------
    PhantomRollKind enum (HUNTERS / DRACHEN / etc.)
    PhantomRoll dataclass
    PHANTOM_ROLL_CATALOG
    RollState
    CorsairRoller
        .roll(kind, rng_pool) -> RollResult
        .double_up(rng_pool) -> RollResult
        .end_roll() -> finalize, return RollOutcome
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_BOSS_CRITIC


BUST_THRESHOLD = 12   # totals 12+ bust


class PhantomRollKind(str, enum.Enum):
    HUNTERS = "hunters_roll"          # Accuracy
    SAMURAI = "samurai_roll"          # Store TP
    NINJA = "ninja_roll"              # Evasion
    DRACHEN = "drachen_roll"          # Pet Attack
    HEALERS = "healers_roll"          # Cure potency
    PUPPET = "puppet_roll"            # Pet Magic Atk
    CORSAIRS = "corsairs_roll"        # EXP bonus
    MAGUS = "magus_roll"              # Magic Defense
    WARLOCKS = "warlocks_roll"        # Magic Acc
    CHAOS = "chaos_roll"              # Attack
    FIGHTERS = "fighters_roll"        # Double Atk rate


@dataclasses.dataclass(frozen=True)
class PhantomRoll:
    kind: PhantomRollKind
    label: str
    effect: str           # human-readable buff name
    lucky: int            # extra bonus on this number
    unlucky: int          # penalty on this number


PHANTOM_ROLL_CATALOG: dict[PhantomRollKind, PhantomRoll] = {
    PhantomRollKind.HUNTERS: PhantomRoll(
        PhantomRollKind.HUNTERS, "Hunter's Roll", "Accuracy", 4, 8,
    ),
    PhantomRollKind.SAMURAI: PhantomRoll(
        PhantomRollKind.SAMURAI, "Samurai Roll", "Store TP", 2, 6,
    ),
    PhantomRollKind.NINJA: PhantomRoll(
        PhantomRollKind.NINJA, "Ninja Roll", "Evasion", 4, 8,
    ),
    PhantomRollKind.DRACHEN: PhantomRoll(
        PhantomRollKind.DRACHEN, "Drachen Roll", "Pet Attack", 4, 8,
    ),
    PhantomRollKind.HEALERS: PhantomRoll(
        PhantomRollKind.HEALERS, "Healer's Roll", "Cure Potency", 3, 7,
    ),
    PhantomRollKind.PUPPET: PhantomRoll(
        PhantomRollKind.PUPPET, "Puppet Roll", "Pet Magic Attack", 3, 7,
    ),
    PhantomRollKind.CORSAIRS: PhantomRoll(
        PhantomRollKind.CORSAIRS, "Corsair's Roll", "EXP Bonus", 5, 9,
    ),
    PhantomRollKind.MAGUS: PhantomRoll(
        PhantomRollKind.MAGUS, "Magus Roll", "Magic Defense", 2, 6,
    ),
    PhantomRollKind.WARLOCKS: PhantomRoll(
        PhantomRollKind.WARLOCKS, "Warlock's Roll", "Magic Accuracy", 4, 8,
    ),
    PhantomRollKind.CHAOS: PhantomRoll(
        PhantomRollKind.CHAOS, "Chaos Roll", "Attack", 4, 8,
    ),
    PhantomRollKind.FIGHTERS: PhantomRoll(
        PhantomRollKind.FIGHTERS, "Fighter's Roll", "Double Attack", 5, 9,
    ),
}


@dataclasses.dataclass(frozen=True)
class RollResult:
    accepted: bool
    total: int = 0
    busted: bool = False
    lucky_hit: bool = False
    unlucky_hit: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class RollState:
    kind: t.Optional[PhantomRollKind] = None
    total: int = 0
    rolls: list[int] = dataclasses.field(default_factory=list)
    busted: bool = False
    finalized: bool = False


@dataclasses.dataclass
class CorsairRoller:
    player_id: str
    state: RollState = dataclasses.field(default_factory=RollState)

    def _d6(self, rng_pool: RngPool) -> int:
        # 1..6 inclusive
        return rng_pool.randint(STREAM_BOSS_CRITIC, 1, 6)

    def roll(self, *, kind: PhantomRollKind,
             rng_pool: RngPool) -> RollResult:
        if self.state.kind is not None and not self.state.finalized:
            return RollResult(False, reason="active roll already running")
        die = self._d6(rng_pool)
        roll_def = PHANTOM_ROLL_CATALOG[kind]
        self.state = RollState(
            kind=kind, total=die, rolls=[die], busted=False,
        )
        return RollResult(
            accepted=True, total=die,
            lucky_hit=(die == roll_def.lucky),
            unlucky_hit=(die == roll_def.unlucky),
        )

    def double_up(self, *, rng_pool: RngPool) -> RollResult:
        if self.state.kind is None:
            return RollResult(False, reason="no active roll")
        if self.state.finalized:
            return RollResult(False, reason="roll already finalized")
        if self.state.busted:
            return RollResult(False, reason="already busted")
        die = self._d6(rng_pool)
        new_total = self.state.total + die
        self.state.rolls.append(die)
        self.state.total = new_total
        roll_def = PHANTOM_ROLL_CATALOG[self.state.kind]
        if new_total >= BUST_THRESHOLD:
            self.state.busted = True
            self.state.finalized = True
            return RollResult(
                accepted=True, total=new_total, busted=True,
            )
        return RollResult(
            accepted=True, total=new_total,
            lucky_hit=(new_total == roll_def.lucky),
            unlucky_hit=(new_total == roll_def.unlucky),
        )

    def end_roll(self) -> RollResult:
        """Finalize and lock the current roll for use."""
        if self.state.kind is None:
            return RollResult(False, reason="no active roll")
        self.state.finalized = True
        return RollResult(
            accepted=True, total=self.state.total,
            busted=self.state.busted,
        )


__all__ = [
    "BUST_THRESHOLD",
    "PhantomRollKind",
    "PhantomRoll",
    "PHANTOM_ROLL_CATALOG",
    "RollResult",
    "RollState",
    "CorsairRoller",
]
