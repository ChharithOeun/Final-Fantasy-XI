"""Nation officer defection — loyalty drift and switching sides.

Officers don't stay loyal forever. A combination of
mistreatment (denial of preferred assignment, pay
arrears, defeat in battle) and external pressure (a
rival nation's flattering offer) can drive an officer's
loyalty down. When loyalty crosses critical thresholds,
defection becomes possible.

This module tracks DEFECTION RISK FACTORS per officer
and resolves DEFECTION ATTEMPTS deterministically given
a seed. The actual loyalty value is owned by
nation_officer_roster; this system reads it (passed in)
and writes loyalty deltas via record_grievance() that
the caller routes back.

Risk factors carry weight; total risk = sum(weights) +
inverse-loyalty floor.

A defection ATTEMPT is initiated by another nation
(via approach()) and resolves with resolve_attempt()
given the officer's current loyalty + an entropy seed.

Public surface
--------------
    GrievanceKind enum (8 kinds with default weights)
    AttemptState enum
    Grievance dataclass (frozen)
    DefectionAttempt dataclass (frozen)
    NationOfficerDefectionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GRIEVANCE_WEIGHTS = {
    "denied_preferred_post": 5,
    "pay_arrears": 8,
    "publicly_shamed": 12,
    "defeat_in_battle": 6,
    "ally_executed": 15,
    "rival_flattery": 4,
    "ideological_drift": 7,
    "personal_insult": 10,
}


class GrievanceKind(str, enum.Enum):
    DENIED_PREFERRED_POST = "denied_preferred_post"
    PAY_ARREARS = "pay_arrears"
    PUBLICLY_SHAMED = "publicly_shamed"
    DEFEAT_IN_BATTLE = "defeat_in_battle"
    ALLY_EXECUTED = "ally_executed"
    RIVAL_FLATTERY = "rival_flattery"
    IDEOLOGICAL_DRIFT = "ideological_drift"
    PERSONAL_INSULT = "personal_insult"


class AttemptState(str, enum.Enum):
    PENDING = "pending"
    DEFECTED = "defected"
    REJECTED = "rejected"
    REPORTED = "reported"


@dataclasses.dataclass(frozen=True)
class Grievance:
    grievance_id: str
    officer_id: str
    kind: GrievanceKind
    note: str
    occurred_day: int
    weight: int


@dataclasses.dataclass(frozen=True)
class DefectionAttempt:
    attempt_id: str
    officer_id: str
    suitor_nation: str
    offer_gil: int
    offer_post: str
    approach_day: int
    state: AttemptState
    resolved_day: t.Optional[int]
    new_loyalty: int


@dataclasses.dataclass
class NationOfficerDefectionSystem:
    _grievances: dict[str, list[Grievance]] = (
        dataclasses.field(default_factory=dict)
    )
    _attempts: dict[str, DefectionAttempt] = (
        dataclasses.field(default_factory=dict)
    )
    _next_g: int = 1
    _next_a: int = 1

    def record_grievance(
        self, *, officer_id: str,
        kind: GrievanceKind, note: str,
        occurred_day: int,
    ) -> t.Optional[str]:
        if not officer_id:
            return None
        if not note or occurred_day < 0:
            return None
        gid = f"griev_{self._next_g}"
        self._next_g += 1
        weight = _GRIEVANCE_WEIGHTS[kind.value]
        g = Grievance(
            grievance_id=gid, officer_id=officer_id,
            kind=kind, note=note,
            occurred_day=occurred_day, weight=weight,
        )
        self._grievances.setdefault(
            officer_id, [],
        ).append(g)
        return gid

    def grievance_total(
        self, *, officer_id: str,
    ) -> int:
        return sum(
            g.weight for g in self._grievances.get(
                officer_id, ()
            )
        )

    def approach(
        self, *, officer_id: str,
        suitor_nation: str, offer_gil: int,
        offer_post: str, approach_day: int,
    ) -> t.Optional[str]:
        if not officer_id or not suitor_nation:
            return None
        if offer_gil < 0:
            return None
        if not offer_post or approach_day < 0:
            return None
        # Block parallel-PENDING attempts from same
        # suitor for same officer.
        for a in self._attempts.values():
            if (a.officer_id == officer_id
                    and a.suitor_nation
                    == suitor_nation
                    and a.state
                    == AttemptState.PENDING):
                return None
        aid = f"def_{self._next_a}"
        self._next_a += 1
        self._attempts[aid] = DefectionAttempt(
            attempt_id=aid, officer_id=officer_id,
            suitor_nation=suitor_nation,
            offer_gil=offer_gil,
            offer_post=offer_post,
            approach_day=approach_day,
            state=AttemptState.PENDING,
            resolved_day=None,
            new_loyalty=0,
        )
        return aid

    def resolve_attempt(
        self, *, attempt_id: str,
        current_loyalty: int, seed: int,
        now_day: int,
    ) -> t.Optional[AttemptState]:
        if attempt_id not in self._attempts:
            return None
        a = self._attempts[attempt_id]
        if a.state != AttemptState.PENDING:
            return None
        if (current_loyalty < 1
                or current_loyalty > 100):
            return None
        # Score: lower loyalty + higher grievance +
        # higher offer + (entropy 0..19) drives defection.
        griev = self.grievance_total(
            officer_id=a.officer_id,
        )
        offer_pull = min(40, a.offer_gil // 1_000)
        entropy = seed % 20
        defection_score = (
            (100 - current_loyalty) + griev
            + offer_pull + entropy
        )
        loyalty_score = (
            current_loyalty + (50 - min(50, griev))
        )
        if defection_score >= loyalty_score + 30:
            new_state = AttemptState.DEFECTED
            new_loy = current_loyalty
        elif loyalty_score >= defection_score + 30:
            # Officer reports the bribe to the loyal
            # crown — extra-strong loyalty result.
            new_state = AttemptState.REPORTED
            new_loy = min(100, current_loyalty + 5)
        else:
            new_state = AttemptState.REJECTED
            new_loy = current_loyalty
        self._attempts[attempt_id] = (
            dataclasses.replace(
                a, state=new_state,
                resolved_day=now_day,
                new_loyalty=new_loy,
            )
        )
        return new_state

    def attempt(
        self, *, attempt_id: str,
    ) -> t.Optional[DefectionAttempt]:
        return self._attempts.get(attempt_id)

    def attempts_for(
        self, *, officer_id: str,
    ) -> list[DefectionAttempt]:
        return [
            a for a in self._attempts.values()
            if a.officer_id == officer_id
        ]

    def grievances_for(
        self, *, officer_id: str,
    ) -> list[Grievance]:
        return list(
            self._grievances.get(officer_id, ()),
        )


__all__ = [
    "GrievanceKind", "AttemptState", "Grievance",
    "DefectionAttempt",
    "NationOfficerDefectionSystem",
]
