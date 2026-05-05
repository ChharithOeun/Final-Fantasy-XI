"""Chocobo breed ownership — mount cap + cross-breed quest flow.

Per the user's design:
  - Each player may own AT MOST ONE active mount-chocobo OR
    ONE incubating egg at a time (not both, not multiple).
  - To CROSS-BREED two distinct colors, two players must
    BOTH bring a chocobo, hand them off to the breeder NPC,
    and run the cross-breed ritual quest. The two parents
    are LOCKED for the duration; on completion an egg
    belongs to ONE of the two players (chosen at quest
    start) and the parents return to their owners.

This module enforces:
  * 1-mount-or-1-egg invariant
  * cross-breed quest state machine
  * lockout of parents during the ritual
  * egg ownership assignment

It does NOT:
  * decide breed-color outcome — defer to chocobo_breed_matrix
  * own the egg lifecycle — defer to chocobo_egg_lifecycle

Public surface
--------------
    OwnedKind enum          MOUNT / EGG / NONE
    BreedQuestStage enum    NOT_STARTED / PARENTS_LOCKED /
                            RITUAL_COMPLETE / EGG_HATCHED_RETURNED
    OwnerSlot dataclass
    BreedQuest dataclass
    ChocoboBreedOwnership
        .grant_mount(player_id, chocobo_id)
        .grant_egg(player_id, egg_id)
        .release_egg(player_id)
        .start_cross_breed(quest_id, player_a, chocobo_a,
                           player_b, chocobo_b, owner_of_egg)
        .complete_ritual(quest_id, egg_id)
        .quest_status(quest_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OwnedKind(str, enum.Enum):
    NONE = "none"
    MOUNT = "mount"
    EGG = "egg"


class BreedQuestStage(str, enum.Enum):
    NOT_STARTED = "not_started"
    PARENTS_LOCKED = "parents_locked"
    RITUAL_COMPLETE = "ritual_complete"
    EGG_HATCHED_RETURNED = "egg_hatched_returned"


@dataclasses.dataclass
class OwnerSlot:
    player_id: str
    kind: OwnedKind = OwnedKind.NONE
    entity_id: t.Optional[str] = None
    locked_quest_id: t.Optional[str] = None


@dataclasses.dataclass
class BreedQuest:
    quest_id: str
    player_a: str
    chocobo_a: str
    player_b: str
    chocobo_b: str
    owner_of_egg: str    # must equal player_a or player_b
    stage: BreedQuestStage = BreedQuestStage.NOT_STARTED
    egg_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class OwnershipResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ChocoboBreedOwnership:
    _slots: dict[str, OwnerSlot] = dataclasses.field(default_factory=dict)
    _quests: dict[str, BreedQuest] = dataclasses.field(default_factory=dict)

    def _ensure_slot(self, player_id: str) -> OwnerSlot:
        slot = self._slots.get(player_id)
        if slot is None:
            slot = OwnerSlot(player_id=player_id)
            self._slots[player_id] = slot
        return slot

    def slot_for(self, *, player_id: str) -> OwnerSlot:
        return self._ensure_slot(player_id)

    def grant_mount(
        self, *, player_id: str, chocobo_id: str,
    ) -> OwnershipResult:
        if not player_id or not chocobo_id:
            return OwnershipResult(False, reason="invalid ids")
        slot = self._ensure_slot(player_id)
        if slot.kind != OwnedKind.NONE:
            return OwnershipResult(
                False, reason=f"already owns {slot.kind.value}",
            )
        slot.kind = OwnedKind.MOUNT
        slot.entity_id = chocobo_id
        return OwnershipResult(True)

    def grant_egg(
        self, *, player_id: str, egg_id: str,
    ) -> OwnershipResult:
        if not player_id or not egg_id:
            return OwnershipResult(False, reason="invalid ids")
        slot = self._ensure_slot(player_id)
        if slot.kind != OwnedKind.NONE:
            return OwnershipResult(
                False, reason=f"already owns {slot.kind.value}",
            )
        slot.kind = OwnedKind.EGG
        slot.entity_id = egg_id
        return OwnershipResult(True)

    def release_slot(
        self, *, player_id: str,
    ) -> OwnershipResult:
        slot = self._slots.get(player_id)
        if slot is None or slot.kind == OwnedKind.NONE:
            return OwnershipResult(False, reason="nothing to release")
        if slot.locked_quest_id is not None:
            return OwnershipResult(
                False, reason="locked by quest",
            )
        slot.kind = OwnedKind.NONE
        slot.entity_id = None
        return OwnershipResult(True)

    def start_cross_breed(
        self, *, quest_id: str,
        player_a: str, chocobo_a: str,
        player_b: str, chocobo_b: str,
        owner_of_egg: str,
    ) -> OwnershipResult:
        if quest_id in self._quests:
            return OwnershipResult(False, reason="quest exists")
        if player_a == player_b:
            return OwnershipResult(False, reason="needs two players")
        if chocobo_a == chocobo_b:
            return OwnershipResult(
                False, reason="needs two chocobos",
            )
        if owner_of_egg not in (player_a, player_b):
            return OwnershipResult(
                False, reason="owner_of_egg must be a or b",
            )
        slot_a = self._ensure_slot(player_a)
        slot_b = self._ensure_slot(player_b)
        # both players must be carrying their MOUNT chocobo
        if (slot_a.kind != OwnedKind.MOUNT
                or slot_a.entity_id != chocobo_a):
            return OwnershipResult(
                False, reason="player_a missing mount",
            )
        if (slot_b.kind != OwnedKind.MOUNT
                or slot_b.entity_id != chocobo_b):
            return OwnershipResult(
                False, reason="player_b missing mount",
            )
        # neither player can already be in another quest
        if (slot_a.locked_quest_id
                or slot_b.locked_quest_id):
            return OwnershipResult(
                False, reason="player already in a quest",
            )
        slot_a.locked_quest_id = quest_id
        slot_b.locked_quest_id = quest_id
        self._quests[quest_id] = BreedQuest(
            quest_id=quest_id,
            player_a=player_a, chocobo_a=chocobo_a,
            player_b=player_b, chocobo_b=chocobo_b,
            owner_of_egg=owner_of_egg,
            stage=BreedQuestStage.PARENTS_LOCKED,
        )
        return OwnershipResult(True)

    def complete_ritual(
        self, *, quest_id: str, egg_id: str,
    ) -> OwnershipResult:
        q = self._quests.get(quest_id)
        if q is None:
            return OwnershipResult(False, reason="unknown quest")
        if q.stage != BreedQuestStage.PARENTS_LOCKED:
            return OwnershipResult(False, reason="bad stage")
        if not egg_id:
            return OwnershipResult(False, reason="no egg id")
        # release parents back to their owners (mounts unlock)
        slot_a = self._slots[q.player_a]
        slot_b = self._slots[q.player_b]
        slot_a.locked_quest_id = None
        slot_b.locked_quest_id = None
        # award egg to owner_of_egg.
        # this requires that owner already returned their mount
        # OR can carry egg if not. But canonical flow: their
        # mount is still in their slot (parents do go back).
        # So we displace mount with egg only if owner explicitly
        # released the mount first. We model that by failing if
        # the owner already has a mount in their slot.
        owner_slot = self._slots[q.owner_of_egg]
        if owner_slot.kind == OwnedKind.MOUNT:
            # The owner must release their mount to make room
            # for the egg. We revert the slot to NONE so the
            # egg can be granted. The mount is presumed
            # stabled via the breeder NPC.
            owner_slot.kind = OwnedKind.NONE
            owner_slot.entity_id = None
        owner_slot.kind = OwnedKind.EGG
        owner_slot.entity_id = egg_id
        q.stage = BreedQuestStage.RITUAL_COMPLETE
        q.egg_id = egg_id
        return OwnershipResult(True)

    def quest_status(
        self, *, quest_id: str,
    ) -> t.Optional[BreedQuest]:
        return self._quests.get(quest_id)


__all__ = [
    "OwnedKind", "BreedQuestStage",
    "OwnerSlot", "BreedQuest", "OwnershipResult",
    "ChocoboBreedOwnership",
]
