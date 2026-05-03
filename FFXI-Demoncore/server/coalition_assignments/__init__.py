"""Coalition daily assignments — kill / gather / deliver tasks.

Each Coalition (Mummers, Pioneers, Inventors, Peacekeepers,
Scouts, Couriers — see coalition_imprimaturs) posts a small
roster of daily assignments. Players accept up to 3 per day
across all coalitions; completion grants Bayld + Sparks of
Eminence + 1 Imprimatur of the matching coalition.

Three task kinds:
    KILL        — defeat N mobs of a family
    GATHER      — collect N items
    DELIVER     — bring an item to a target NPC

Public surface
--------------
    AssignmentKind enum
    Assignment dataclass / ASSIGNMENT_CATALOG
    PlayerCoalitionLog
        .accept(assignment_id) / .progress(...) / .turn_in()
        .reset_daily(today_vana_day)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.coalition_imprimaturs import Coalition


MAX_ACTIVE_ASSIGNMENTS = 3


class AssignmentKind(str, enum.Enum):
    KILL = "kill"
    GATHER = "gather"
    DELIVER = "deliver"


@dataclasses.dataclass(frozen=True)
class Assignment:
    assignment_id: str
    coalition: Coalition
    kind: AssignmentKind
    label: str
    target_id: str          # mob_family / item_id / npc_id
    quantity: int
    bayld_reward: int
    sparks_reward: int


# Two assignments per coalition × 6 coalitions = 12
ASSIGNMENT_CATALOG: tuple[Assignment, ...] = (
    Assignment("mummers_kill_imps", Coalition.MUMMERS,
                AssignmentKind.KILL, "Cull the imps",
                target_id="imp", quantity=6,
                bayld_reward=600, sparks_reward=400),
    Assignment("mummers_deliver_costume", Coalition.MUMMERS,
                AssignmentKind.DELIVER, "Deliver Mummer Robe",
                target_id="mummer_robe", quantity=1,
                bayld_reward=400, sparks_reward=300),
    Assignment("pioneers_gather_orichalcum", Coalition.PIONEERS,
                AssignmentKind.GATHER, "Gather Orichalcum Ore",
                target_id="orichalcum_ore", quantity=4,
                bayld_reward=800, sparks_reward=500),
    Assignment("pioneers_kill_xzomit", Coalition.PIONEERS,
                AssignmentKind.KILL, "Slay 5 Xzomit",
                target_id="xzomit", quantity=5,
                bayld_reward=750, sparks_reward=500),
    Assignment("inventors_gather_mythril", Coalition.INVENTORS,
                AssignmentKind.GATHER, "Gather Mythril Bars",
                target_id="mythril_bar", quantity=4,
                bayld_reward=900, sparks_reward=600),
    Assignment("inventors_deliver_blueprint",
                Coalition.INVENTORS, AssignmentKind.DELIVER,
                "Deliver Inventor's Blueprint",
                target_id="inventors_blueprint", quantity=1,
                bayld_reward=500, sparks_reward=400),
    Assignment("peacekeepers_kill_orcs",
                Coalition.PEACEKEEPERS, AssignmentKind.KILL,
                "Eliminate orc raiders",
                target_id="orc_raider", quantity=6,
                bayld_reward=1000, sparks_reward=700),
    Assignment("peacekeepers_kill_skeleton",
                Coalition.PEACEKEEPERS, AssignmentKind.KILL,
                "Cleanse skeleton incursion",
                target_id="skeleton_warrior", quantity=8,
                bayld_reward=900, sparks_reward=600),
    Assignment("scouts_gather_intel",
                Coalition.SCOUTS, AssignmentKind.GATHER,
                "Recover Scout Reports",
                target_id="scout_report", quantity=3,
                bayld_reward=700, sparks_reward=450),
    Assignment("scouts_kill_yagudo_scout",
                Coalition.SCOUTS, AssignmentKind.KILL,
                "Silence Yagudo scouts",
                target_id="yagudo_scout", quantity=4,
                bayld_reward=600, sparks_reward=400),
    Assignment("couriers_deliver_parcel",
                Coalition.COURIERS, AssignmentKind.DELIVER,
                "Deliver sealed parcel to Adoulin",
                target_id="sealed_parcel", quantity=1,
                bayld_reward=500, sparks_reward=350),
    Assignment("couriers_gather_letter",
                Coalition.COURIERS, AssignmentKind.GATHER,
                "Recover lost mail bag",
                target_id="lost_mail_bag", quantity=2,
                bayld_reward=700, sparks_reward=450),
)


ASSIGNMENT_BY_ID: dict[str, Assignment] = {
    a.assignment_id: a for a in ASSIGNMENT_CATALOG
}


def assignments_for(coalition: Coalition) -> tuple[Assignment, ...]:
    return tuple(
        a for a in ASSIGNMENT_CATALOG if a.coalition == coalition
    )


@dataclasses.dataclass
class _ActiveAssignment:
    assignment: Assignment
    progress: int = 0


@dataclasses.dataclass(frozen=True)
class TurnInResult:
    accepted: bool
    coalition: t.Optional[Coalition] = None
    bayld_awarded: int = 0
    sparks_awarded: int = 0
    imprimatur_awarded: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerCoalitionLog:
    player_id: str
    last_reset_day: int = -1
    active: dict[str, _ActiveAssignment] = dataclasses.field(
        default_factory=dict,
    )
    completed_today: list[str] = dataclasses.field(
        default_factory=list,
    )

    def reset_daily(self, *, current_vana_day: int) -> None:
        if self.last_reset_day != current_vana_day:
            self.last_reset_day = current_vana_day
            self.active.clear()
            self.completed_today.clear()

    def accept(
        self, *, assignment_id: str, current_vana_day: int,
    ) -> bool:
        self.reset_daily(current_vana_day=current_vana_day)
        if len(self.active) >= MAX_ACTIVE_ASSIGNMENTS:
            return False
        if assignment_id in self.active:
            return False
        a = ASSIGNMENT_BY_ID.get(assignment_id)
        if a is None:
            return False
        self.active[assignment_id] = _ActiveAssignment(assignment=a)
        return True

    def progress(
        self, *, assignment_id: str, target_id: str,
        amount: int = 1,
    ) -> bool:
        ent = self.active.get(assignment_id)
        if ent is None or amount <= 0:
            return False
        if ent.assignment.target_id != target_id:
            return False
        ent.progress = min(
            ent.assignment.quantity, ent.progress + amount,
        )
        return True

    def is_complete(self, *, assignment_id: str) -> bool:
        ent = self.active.get(assignment_id)
        if ent is None:
            return False
        return ent.progress >= ent.assignment.quantity

    def turn_in(self, *, assignment_id: str) -> TurnInResult:
        ent = self.active.get(assignment_id)
        if ent is None:
            return TurnInResult(False, reason="not active")
        if ent.progress < ent.assignment.quantity:
            return TurnInResult(False, reason="incomplete")
        del self.active[assignment_id]
        self.completed_today.append(assignment_id)
        return TurnInResult(
            accepted=True,
            coalition=ent.assignment.coalition,
            bayld_awarded=ent.assignment.bayld_reward,
            sparks_awarded=ent.assignment.sparks_reward,
            imprimatur_awarded=True,
        )


__all__ = [
    "MAX_ACTIVE_ASSIGNMENTS",
    "AssignmentKind", "Assignment",
    "ASSIGNMENT_CATALOG", "ASSIGNMENT_BY_ID",
    "assignments_for", "TurnInResult",
    "PlayerCoalitionLog",
]
