"""Wedding system — in-game ceremonies between players.

Two players plan a ceremony at a designated venue, invite witnesses,
exchange rings, and both receive a Wed certificate item plus a small
permanent stat bonus while the marriage holds. Divorce is possible
but cools the bonus.

Public surface
--------------
    WeddingState enum
    WeddingPlan immutable
    WeddingRegistry per-server
        .schedule(p1, p2, venue, time)
        .add_witness(plan_id, witness_id)
        .perform(plan_id, ring_a, ring_b) -> Result
        .divorce(plan_id) -> Result
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WeddingState(str, enum.Enum):
    SCHEDULED = "scheduled"
    PERFORMED = "performed"
    DIVORCED = "divorced"
    CANCELLED = "cancelled"


@dataclasses.dataclass(frozen=True)
class WeddingVenue:
    venue_id: str
    name: str
    capacity: int


WEDDING_VENUES: tuple[WeddingVenue, ...] = (
    WeddingVenue("cathedral_sandy", "San d'Oria Cathedral",
                 capacity=30),
    WeddingVenue("metalworks_bastok", "Bastok Metalworks Hall",
                 capacity=20),
    WeddingVenue("rhinostery_windy", "Windurst Rhinostery",
                 capacity=20),
    WeddingVenue("aht_grand_temple", "Aht Urhgan Grand Temple",
                 capacity=40),
)

VENUE_BY_ID: dict[str, WeddingVenue] = {
    v.venue_id: v for v in WEDDING_VENUES
}


@dataclasses.dataclass
class WeddingPlan:
    wedding_id: str
    partner_a_id: str
    partner_b_id: str
    venue_id: str
    scheduled_for_tick: int
    state: WeddingState = WeddingState.SCHEDULED
    witnesses: set[str] = dataclasses.field(default_factory=set)
    performed_at_tick: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class ActionResult:
    accepted: bool
    wedding_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class WeddingRegistry:
    server_id: str
    _next_id: int = 1
    _plans: dict[str, WeddingPlan] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def schedule(
        self, *,
        partner_a_id: str, partner_b_id: str,
        venue_id: str, scheduled_for_tick: int,
    ) -> ActionResult:
        if partner_a_id == partner_b_id:
            return ActionResult(False, "", reason="cannot self-marry")
        if venue_id not in VENUE_BY_ID:
            return ActionResult(False, "", reason="unknown venue")
        # Each partner can only have one active wedding plan
        for p in self._plans.values():
            if p.state in (WeddingState.SCHEDULED,
                            WeddingState.PERFORMED):
                if partner_a_id in (p.partner_a_id, p.partner_b_id):
                    return ActionResult(
                        False, "",
                        reason=f"{partner_a_id} already in plan {p.wedding_id}",
                    )
                if partner_b_id in (p.partner_a_id, p.partner_b_id):
                    return ActionResult(
                        False, "",
                        reason=f"{partner_b_id} already in plan {p.wedding_id}",
                    )
        wid = f"wed_{self._next_id}"
        self._next_id += 1
        self._plans[wid] = WeddingPlan(
            wedding_id=wid,
            partner_a_id=partner_a_id, partner_b_id=partner_b_id,
            venue_id=venue_id,
            scheduled_for_tick=scheduled_for_tick,
        )
        return ActionResult(True, wid)

    def add_witness(
        self, *, wedding_id: str, witness_id: str,
    ) -> ActionResult:
        plan = self._plans.get(wedding_id)
        if plan is None:
            return ActionResult(False, wedding_id,
                                reason="unknown wedding")
        if plan.state != WeddingState.SCHEDULED:
            return ActionResult(False, wedding_id,
                                reason="not scheduled")
        venue = VENUE_BY_ID[plan.venue_id]
        if len(plan.witnesses) >= venue.capacity:
            return ActionResult(False, wedding_id,
                                reason="venue capacity reached")
        if witness_id in (plan.partner_a_id, plan.partner_b_id):
            return ActionResult(False, wedding_id,
                                reason="partner cannot witness")
        plan.witnesses.add(witness_id)
        return ActionResult(True, wedding_id)

    def perform(
        self, *, wedding_id: str, now_tick: int,
    ) -> ActionResult:
        plan = self._plans.get(wedding_id)
        if plan is None:
            return ActionResult(False, wedding_id,
                                reason="unknown wedding")
        if plan.state != WeddingState.SCHEDULED:
            return ActionResult(False, wedding_id,
                                reason=f"state is {plan.state.value}")
        if now_tick < plan.scheduled_for_tick:
            return ActionResult(False, wedding_id,
                                reason="too early")
        if len(plan.witnesses) < 1:
            return ActionResult(False, wedding_id,
                                reason="need at least one witness")
        plan.state = WeddingState.PERFORMED
        plan.performed_at_tick = now_tick
        return ActionResult(True, wedding_id)

    def divorce(
        self, *, wedding_id: str,
    ) -> ActionResult:
        plan = self._plans.get(wedding_id)
        if plan is None:
            return ActionResult(False, wedding_id,
                                reason="unknown wedding")
        if plan.state != WeddingState.PERFORMED:
            return ActionResult(False, wedding_id,
                                reason="not married")
        plan.state = WeddingState.DIVORCED
        return ActionResult(True, wedding_id)

    def cancel(self, *, wedding_id: str) -> ActionResult:
        plan = self._plans.get(wedding_id)
        if plan is None:
            return ActionResult(False, wedding_id,
                                reason="unknown wedding")
        if plan.state != WeddingState.SCHEDULED:
            return ActionResult(False, wedding_id,
                                reason="cannot cancel after performance")
        plan.state = WeddingState.CANCELLED
        return ActionResult(True, wedding_id)

    def get(self, wedding_id: str) -> t.Optional[WeddingPlan]:
        return self._plans.get(wedding_id)

    def is_married(self, player_id: str) -> bool:
        for p in self._plans.values():
            if p.state == WeddingState.PERFORMED:
                if player_id in (p.partner_a_id, p.partner_b_id):
                    return True
        return False


__all__ = [
    "WeddingState", "WeddingVenue",
    "WEDDING_VENUES", "VENUE_BY_ID",
    "WeddingPlan", "ActionResult",
    "WeddingRegistry",
]
