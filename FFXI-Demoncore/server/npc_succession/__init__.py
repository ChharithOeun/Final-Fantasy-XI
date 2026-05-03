"""NPC succession — heirs take over after a named NPC dies.

Demoncore's world is mortal. NPCs can die — by player murder, by
beastmen raid, by old age, by plot. When a NAMED NPC who holds
a role (shopkeeper, quest-giver, master crafter, faction
leader) dies, the world doesn't lose the role; an HEIR steps in.
The role continues; some things are inherited (shop inventory,
faction reputation toward the player, public-facing
relationships) and some are NOT (private memories, personality
quirks).

Inheritance model
-----------------
A `SuccessionPlan` declares for a named NPC:
* The role they hold (the role_id continues across heirs)
* An ordered list of heir candidates (apprentice, child,
  guildmate)
* What's inherited:
    - SHOP_INVENTORY
    - FACTION_REPUTATION_OF_PLAYER (the role's relationships)
    - QUEST_CHAIN_PROGRESS
    - PUBLIC_RELATIONSHIPS (NPC->NPC ties keyed by role)
* What is NOT inherited:
    - Personal memories (entity_memory)
    - Personal goals (npc_goals)
    - Personality vector (mob_personality)

When the named NPC dies, succession picks the first available
heir (alive + bound to the same faction). The heir inherits a
new entity_id but the ROLE_ID persists, so other systems still
look up by role.

Public surface
--------------
    InheritKind enum
    HeirCandidate dataclass
    SuccessionPlan dataclass
    SuccessionResult dataclass
    NPCSuccessionRegistry
        .register_plan(plan)
        .declare_dead(npc_id, now)
        .recover_heir(role_id) -> SuccessionResult
        .role_holder(role_id) -> Optional[str]
        .history(role_id) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class InheritKind(str, enum.Enum):
    SHOP_INVENTORY = "shop_inventory"
    FACTION_REPUTATION_OF_PLAYER = "faction_reputation_of_player"
    QUEST_CHAIN_PROGRESS = "quest_chain_progress"
    PUBLIC_RELATIONSHIPS = "public_relationships"


# Default inheritance set when none is specified.
DEFAULT_INHERIT: frozenset[InheritKind] = frozenset(InheritKind)


@dataclasses.dataclass(frozen=True)
class HeirCandidate:
    npc_id: str
    is_alive: bool = True
    faction_id: str = ""
    relationship_to_predecessor: str = ""    # apprentice, child, etc
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class SuccessionPlan:
    role_id: str
    role_label: str
    incumbent_npc_id: str
    faction_id: str
    heir_order: tuple[HeirCandidate, ...]
    inherits: frozenset[InheritKind] = DEFAULT_INHERIT
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class SuccessionResult:
    accepted: bool
    role_id: str
    new_holder_id: t.Optional[str] = None
    inherited: frozenset[InheritKind] = frozenset()
    reason: t.Optional[str] = None


class _RoleState:
    """Internal: tracks who currently holds the role and
    what's left in the heir queue."""
    def __init__(
        self, plan: SuccessionPlan,
    ) -> None:
        self.plan = plan
        self.current_holder: str = plan.incumbent_npc_id
        self.dead: set[str] = set()
        # Mutable: heir queue is reduced as we go
        self.remaining_heirs: list[HeirCandidate] = list(
            plan.heir_order,
        )
        self.history: list[str] = [plan.incumbent_npc_id]


@dataclasses.dataclass
class NPCSuccessionRegistry:
    _roles: dict[str, _RoleState] = dataclasses.field(
        default_factory=dict,
    )
    # incumbent or heir npc_id -> role_id
    _npc_to_role: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_plan(
        self, plan: SuccessionPlan,
    ) -> SuccessionPlan:
        state = _RoleState(plan)
        self._roles[plan.role_id] = state
        self._npc_to_role[plan.incumbent_npc_id] = plan.role_id
        for heir in plan.heir_order:
            self._npc_to_role.setdefault(
                heir.npc_id, plan.role_id,
            )
        return plan

    def declare_dead(
        self, *, npc_id: str, now_seconds: float = 0.0,
    ) -> bool:
        role_id = self._npc_to_role.get(npc_id)
        if role_id is None:
            return False
        state = self._roles[role_id]
        state.dead.add(npc_id)
        # Mark the heir queue entry dead too if applicable
        new_heirs: list[HeirCandidate] = []
        for h in state.remaining_heirs:
            if h.npc_id == npc_id:
                new_heirs.append(dataclasses.replace(
                    h, is_alive=False,
                ))
            else:
                new_heirs.append(h)
        state.remaining_heirs = new_heirs
        return True

    def role_holder(
        self, role_id: str,
    ) -> t.Optional[str]:
        state = self._roles.get(role_id)
        if state is None:
            return None
        if state.current_holder in state.dead:
            return None
        return state.current_holder

    def history(self, role_id: str) -> tuple[str, ...]:
        state = self._roles.get(role_id)
        return tuple(state.history) if state else ()

    def recover_heir(
        self, *, role_id: str,
    ) -> SuccessionResult:
        state = self._roles.get(role_id)
        if state is None:
            return SuccessionResult(
                accepted=False, role_id=role_id,
                reason="no such role",
            )
        if state.current_holder not in state.dead:
            return SuccessionResult(
                accepted=False, role_id=role_id,
                reason="incumbent still alive",
            )
        # Walk heir queue until we find an alive heir of the
        # right faction.
        new_holder: t.Optional[str] = None
        new_remaining: list[HeirCandidate] = []
        found = False
        for heir in state.remaining_heirs:
            if found or not heir.is_alive:
                new_remaining.append(heir)
                continue
            if (
                state.plan.faction_id
                and heir.faction_id
                and heir.faction_id != state.plan.faction_id
            ):
                # Wrong faction — skip
                new_remaining.append(heir)
                continue
            new_holder = heir.npc_id
            found = True
            # don't append — heir consumed
        state.remaining_heirs = new_remaining
        if new_holder is None:
            return SuccessionResult(
                accepted=False, role_id=role_id,
                reason="no eligible heirs remain",
            )
        state.current_holder = new_holder
        state.history.append(new_holder)
        return SuccessionResult(
            accepted=True, role_id=role_id,
            new_holder_id=new_holder,
            inherited=state.plan.inherits,
        )

    def total_roles(self) -> int:
        return len(self._roles)


__all__ = [
    "InheritKind", "DEFAULT_INHERIT",
    "HeirCandidate", "SuccessionPlan", "SuccessionResult",
    "NPCSuccessionRegistry",
]
