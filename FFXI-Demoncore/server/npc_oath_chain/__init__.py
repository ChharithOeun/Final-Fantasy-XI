"""NPC oath chain — chained loyalty to a sworn liege.

Some officers don't just defect — they take their
SWORN SUBORDINATES with them. A junior officer who
swore an oath to Volker may follow him to Windurst when
he leaves Bastok. Whether they do depends on the
strength of the oath and the subordinate's own loyalty
profile.

This module manages OATH BONDS (sworn-to relationships)
and resolves CASCADE DEFECTIONS deterministically given
a seed.

Bond strength:
    LOOSE         informal mentorship; rarely cascades
    BOUND         formal subordination; sometimes
                  cascades
    BLOOD_OATH    sacred vow; almost always cascades

Cascade decision factors:
    - bond strength
    - subordinate's own loyalty to current nation
    - subordinate's grievances against current nation
    - seed entropy

Public surface
--------------
    BondStrength enum
    CascadeOutcome enum (FOLLOWED / STAYED /
                          AMBIVALENT)
    OathBond dataclass (frozen)
    CascadeRecord dataclass (frozen)
    NPCOathChainSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_BOND_PULL = {
    "loose": 10,
    "bound": 30,
    "blood_oath": 60,
}


class BondStrength(str, enum.Enum):
    LOOSE = "loose"
    BOUND = "bound"
    BLOOD_OATH = "blood_oath"


class CascadeOutcome(str, enum.Enum):
    FOLLOWED = "followed"
    STAYED = "stayed"
    AMBIVALENT = "ambivalent"


@dataclasses.dataclass(frozen=True)
class OathBond:
    bond_id: str
    liege_id: str
    sworn_id: str
    strength: BondStrength
    sworn_day: int
    broken_day: t.Optional[int]


@dataclasses.dataclass(frozen=True)
class CascadeRecord:
    record_id: str
    liege_id: str
    sworn_id: str
    bond_id: str
    outcome: CascadeOutcome
    pull_score: int
    stay_score: int
    seed: int
    occurred_day: int


@dataclasses.dataclass
class NPCOathChainSystem:
    _bonds: dict[str, OathBond] = dataclasses.field(
        default_factory=dict,
    )
    _records: dict[str, CascadeRecord] = (
        dataclasses.field(default_factory=dict)
    )
    _next_b: int = 1
    _next_r: int = 1

    def swear_oath(
        self, *, liege_id: str, sworn_id: str,
        strength: BondStrength, sworn_day: int,
    ) -> t.Optional[str]:
        if not liege_id or not sworn_id:
            return None
        if liege_id == sworn_id:
            return None
        if sworn_day < 0:
            return None
        # Block duplicate active bond same pair
        for b in self._bonds.values():
            if (b.liege_id == liege_id
                    and b.sworn_id == sworn_id
                    and b.broken_day is None):
                return None
        bid = f"oath_{self._next_b}"
        self._next_b += 1
        self._bonds[bid] = OathBond(
            bond_id=bid, liege_id=liege_id,
            sworn_id=sworn_id, strength=strength,
            sworn_day=sworn_day, broken_day=None,
        )
        return bid

    def break_oath(
        self, *, bond_id: str, now_day: int,
    ) -> bool:
        if bond_id not in self._bonds:
            return False
        b = self._bonds[bond_id]
        if b.broken_day is not None:
            return False
        if now_day < b.sworn_day:
            return False
        self._bonds[bond_id] = dataclasses.replace(
            b, broken_day=now_day,
        )
        return True

    def active_bonds_to_liege(
        self, *, liege_id: str,
    ) -> list[OathBond]:
        return [
            b for b in self._bonds.values()
            if (b.liege_id == liege_id
                and b.broken_day is None)
        ]

    def resolve_cascade(
        self, *, bond_id: str,
        sworn_loyalty_to_current: int,
        sworn_grievance_score: int,
        seed: int, now_day: int,
    ) -> t.Optional[CascadeOutcome]:
        if bond_id not in self._bonds:
            return None
        b = self._bonds[bond_id]
        if b.broken_day is not None:
            return None
        if (sworn_loyalty_to_current < 1
                or sworn_loyalty_to_current > 100):
            return None
        if sworn_grievance_score < 0:
            return None
        pull = (
            _BOND_PULL[b.strength.value]
            + sworn_grievance_score
            + (seed % 13)
        )
        stay = (
            sworn_loyalty_to_current
            + ((seed >> 4) % 13)
        )
        if pull >= stay + 15:
            outcome = CascadeOutcome.FOLLOWED
        elif stay >= pull + 15:
            outcome = CascadeOutcome.STAYED
        else:
            outcome = CascadeOutcome.AMBIVALENT
        rid = f"casc_{self._next_r}"
        self._next_r += 1
        self._records[rid] = CascadeRecord(
            record_id=rid, liege_id=b.liege_id,
            sworn_id=b.sworn_id, bond_id=bond_id,
            outcome=outcome, pull_score=pull,
            stay_score=stay, seed=seed,
            occurred_day=now_day,
        )
        return outcome

    def cascade_for_liege(
        self, *, liege_id: str,
    ) -> list[CascadeRecord]:
        return [
            r for r in self._records.values()
            if r.liege_id == liege_id
        ]

    def followers_of(
        self, *, liege_id: str,
    ) -> list[str]:
        """Sworn IDs whose latest cascade resolved
        FOLLOWED."""
        per_sworn: dict[str, CascadeRecord] = {}
        for r in self._records.values():
            if r.liege_id != liege_id:
                continue
            cur = per_sworn.get(r.sworn_id)
            if (cur is None
                    or r.occurred_day > cur.occurred_day):
                per_sworn[r.sworn_id] = r
        return [
            sid for sid, r in per_sworn.items()
            if r.outcome == CascadeOutcome.FOLLOWED
        ]

    def bond(
        self, *, bond_id: str,
    ) -> t.Optional[OathBond]:
        return self._bonds.get(bond_id)


__all__ = [
    "BondStrength", "CascadeOutcome", "OathBond",
    "CascadeRecord", "NPCOathChainSystem",
]
