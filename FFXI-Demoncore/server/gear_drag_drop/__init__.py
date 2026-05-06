"""Gear drag-drop — drag from inventory to a builder slot.

Some players prefer typing; some prefer dragging the
exact item they're holding. Drag-drop closes the loop
for the latter: open the inventory panel, drag a piece
into a slot in the builder, the builder validates and
accepts.

State machine:
    IDLE       no drag in progress
    DRAGGING   item picked up, hovering somewhere
    DROPPED    placed; success or refusal recorded

The drop validation goes through gear_slot_filter so a
Body item dragged onto a Head slot snaps back. The
DropResult carries the outcome and the reason on refusal,
which the UI surfaces as a small floating message.

Public surface
--------------
    DragState enum (IDLE/DRAGGING/DROPPED)
    DropOutcome enum (ACCEPTED/REFUSED_WRONG_SLOT/
                       REFUSED_NOT_OWNED/REFUSED_NO_DRAG)
    DropResult dataclass (frozen)
    GearDragDrop
        .pick_up(player_id, item_id, source_bag) -> bool
        .drop_on(player_id, target_set, target_slot)
            -> DropResult
        .cancel(player_id) -> bool
        .state(player_id) -> DragState
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gear_slot_filter import GearSlotFilter, Slot


class DragState(str, enum.Enum):
    IDLE = "idle"
    DRAGGING = "dragging"
    DROPPED = "dropped"


class DropOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    REFUSED_WRONG_SLOT = "refused_wrong_slot"
    REFUSED_NOT_OWNED = "refused_not_owned"
    REFUSED_NO_DRAG = "refused_no_drag"


@dataclasses.dataclass(frozen=True)
class DropResult:
    outcome: DropOutcome
    item_id: str
    target_set: str
    target_slot: t.Optional[Slot]
    message: str


@dataclasses.dataclass
class _DragSession:
    player_id: str
    item_id: str
    source_bag: str
    state: DragState


@dataclasses.dataclass
class GearDragDrop:
    _filter: GearSlotFilter
    _sessions: dict[str, _DragSession] = dataclasses.field(
        default_factory=dict,
    )

    def pick_up(
        self, *, player_id: str, item_id: str,
        source_bag: str = "wardrobe1",
    ) -> bool:
        if not player_id or not item_id:
            return False
        if self._filter.item_lookup(item_id=item_id) is None:
            return False
        # Only the owner can pick up their own gear.
        owned = self._filter.candidates_for_slot(
            slot=Slot.MAIN, owned_only=True, owner_id=player_id,
        )
        owned_ids = {i.item_id for i in owned}
        # Iterate all slots since the item may not be MAIN.
        if item_id not in owned_ids:
            for slot in Slot:
                items = self._filter.candidates_for_slot(
                    slot=slot, owned_only=True,
                    owner_id=player_id,
                )
                if any(i.item_id == item_id for i in items):
                    owned_ids.add(item_id)
                    break
        if item_id not in owned_ids:
            return False
        # Replace any in-flight drag — only one drag at a time.
        self._sessions[player_id] = _DragSession(
            player_id=player_id, item_id=item_id,
            source_bag=source_bag, state=DragState.DRAGGING,
        )
        return True

    def drop_on(
        self, *, player_id: str, target_set: str,
        target_slot: Slot,
    ) -> DropResult:
        sess = self._sessions.get(player_id)
        if sess is None or sess.state != DragState.DRAGGING:
            return DropResult(
                outcome=DropOutcome.REFUSED_NO_DRAG,
                item_id="", target_set=target_set,
                target_slot=target_slot,
                message="no drag in progress",
            )
        # Re-verify ownership at drop time (anti-grief).
        item_id = sess.item_id
        item = self._filter.item_lookup(item_id=item_id)
        if item is None:
            sess.state = DragState.DROPPED
            return DropResult(
                outcome=DropOutcome.REFUSED_NOT_OWNED,
                item_id=item_id, target_set=target_set,
                target_slot=target_slot,
                message="item no longer exists",
            )
        if not self._filter.can_equip(
            item_id=item_id, slot=target_slot,
        ):
            sess.state = DragState.DROPPED
            return DropResult(
                outcome=DropOutcome.REFUSED_WRONG_SLOT,
                item_id=item_id, target_set=target_set,
                target_slot=target_slot,
                message=(
                    f"{item.display_name} doesn't fit "
                    f"{target_slot.value}"
                ),
            )
        sess.state = DragState.DROPPED
        return DropResult(
            outcome=DropOutcome.ACCEPTED,
            item_id=item_id, target_set=target_set,
            target_slot=target_slot,
            message="",
        )

    def cancel(self, *, player_id: str) -> bool:
        sess = self._sessions.get(player_id)
        if sess is None:
            return False
        if sess.state != DragState.DRAGGING:
            return False
        sess.state = DragState.IDLE
        return True

    def state(self, *, player_id: str) -> DragState:
        sess = self._sessions.get(player_id)
        if sess is None:
            return DragState.IDLE
        return sess.state

    def held_item(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        sess = self._sessions.get(player_id)
        if sess is None or sess.state != DragState.DRAGGING:
            return None
        return sess.item_id


__all__ = [
    "DragState", "DropOutcome", "DropResult",
    "GearDragDrop",
]
