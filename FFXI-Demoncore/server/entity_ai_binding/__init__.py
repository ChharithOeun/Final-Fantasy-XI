"""Entity-to-AI-agent binding registry.

The Demoncore doctrine: EVERY entity in the world is driven by a
real AI model. Players, mobs, NMs, bosses, beastmen tribes, NPC
shopkeepers, NPC patrol guards, even the dancing minstrels in
the inn — all of them have an AI agent on the other end. The
players are joining an AI-driven world.

This module is the registry that makes that doctrine canonical.
For every world entity, there is exactly one EntityAIBinding
that names:

* the entity (mob_id / npc_id / player_id / boss_id / faction_id)
* the kind of entity it is
* which AI agent profile is driving it (model + persona file)
* the AI tier — how much "thinking budget" the agent gets, which
  feeds into ai_density's per-zone budget allocator
* lifecycle hooks (when the binding was last activated,
  deactivated, or whose binding has gone stale)

The orchestrator (agent_orchestrator) reads this registry at
spawn time and wires the right agent profile to the entity.
ai_density consults the registry to figure out how many "live"
agents are running in a given zone and whether to demote some
to a cheaper tier under load.

Public surface
--------------
    EntityKind enum (PLAYER / MOB / NM / BOSS / NPC / BEASTMEN_FACTION /
                     PET / TRUST / FELLOW)
    AITier enum (FLAGSHIP / FULL / LITE / SCRIPTED / INERT)
    AgentProfile dataclass (agent_id, model_name, persona_path)
    EntityAIBinding dataclass (entity_id, kind, profile, tier, ...)
    EntityAIRegistry — the per-server global registry
        .bind(...) / .unbind(...)
        .get(entity_id) / .by_kind(kind) / .by_tier(tier)
        .promote(entity_id, tier) / .demote(...)
        .stale_bindings(now_seconds, max_age) — for cleanup
        .summary() — population by tier (for ai_density)

Doctrine notes
--------------
* INERT is reserved for entities that genuinely need NO AI (e.g.
  static furniture, signposts). Even those exist in the registry
  so we can audit "everything has a binding".
* SCRIPTED is the cheapest live tier — old-school FFXI-style
  scripted reactions, used as a fallback if a higher-tier agent
  fails. Even "scripted" entities are wrapped by the orchestrator
  so the same world still feels alive.
* Players use the kind PLAYER with a special profile pointer to
  the player-controlled "agent" (the human at the keyboard).
  This keeps the registry uniform and the orchestrator's APIs
  identical for player and AI input.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EntityKind(str, enum.Enum):
    PLAYER = "player"
    MOB = "mob"
    NM = "nm"                       # notorious monster
    BOSS = "boss"                   # raid / endgame boss
    NPC = "npc"                     # vendor / patrol / civilian
    BEASTMEN_FACTION = "beastmen_faction"   # faction-scope agent
    PET = "pet"                     # PUP / SMN / BST pets
    TRUST = "trust"                 # Trust NPCs
    FELLOW = "fellow"               # Fellowship NPC
    STATIC = "static"               # furniture / signpost (INERT only)


class AITier(str, enum.Enum):
    """How much compute the AI agent gets.

    FLAGSHIP — top-tier model, used for hero NPCs, named bosses,
        any entity in a player's immediate zone of focus.
    FULL — mid-tier model, sufficient for most NMs and key NPCs.
    LITE — small/local model, default for ambient mobs and
        background NPCs. Most populous tier.
    SCRIPTED — old-school FSM/scripted reaction. Used either as
        a fallback when models fail OR for entities so far from
        any player that a model is wasted.
    INERT — no AI at all. Reserved for static/decorative entities.
    """
    FLAGSHIP = "flagship"
    FULL = "full"
    LITE = "lite"
    SCRIPTED = "scripted"
    INERT = "inert"


# Canonical demotion ladder used by ai_density when the per-zone
# budget is over-subscribed. Each tier may be demoted to the next
# without losing the entity entirely; only INERT genuinely turns
# AI off.
DEMOTION_LADDER: tuple[AITier, ...] = (
    AITier.FLAGSHIP, AITier.FULL, AITier.LITE,
    AITier.SCRIPTED, AITier.INERT,
)


@dataclasses.dataclass(frozen=True)
class AgentProfile:
    """Pointer to the YAML persona + model the orchestrator wires
    into the entity. Profiles live under agents/."""
    agent_id: str
    model_name: str            # e.g. "claude-haiku-4-5", "llama3.1:8b"
    persona_path: str          # e.g. "agents/curilla.yaml"


@dataclasses.dataclass
class EntityAIBinding:
    entity_id: str
    kind: EntityKind
    profile: AgentProfile
    tier: AITier = AITier.LITE
    bound_at_seconds: float = 0.0
    last_active_at_seconds: float = 0.0
    notes: str = ""

    def is_inert(self) -> bool:
        return self.tier == AITier.INERT

    def is_live(self) -> bool:
        return self.tier != AITier.INERT


@dataclasses.dataclass(frozen=True)
class BindResult:
    accepted: bool
    binding: t.Optional[EntityAIBinding] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class EntityAIRegistry:
    _by_id: dict[str, EntityAIBinding] = dataclasses.field(
        default_factory=dict,
    )

    @property
    def total(self) -> int:
        return len(self._by_id)

    def bind(
        self, *, entity_id: str, kind: EntityKind,
        profile: AgentProfile, tier: AITier = AITier.LITE,
        now_seconds: float = 0.0,
        notes: str = "",
    ) -> BindResult:
        if entity_id in self._by_id:
            return BindResult(False, reason="already bound")
        if kind == EntityKind.STATIC and tier != AITier.INERT:
            return BindResult(
                False, reason="STATIC entities must be INERT",
            )
        binding = EntityAIBinding(
            entity_id=entity_id, kind=kind, profile=profile,
            tier=tier, bound_at_seconds=now_seconds,
            last_active_at_seconds=now_seconds, notes=notes,
        )
        self._by_id[entity_id] = binding
        return BindResult(True, binding=binding)

    def unbind(self, *, entity_id: str) -> bool:
        return self._by_id.pop(entity_id, None) is not None

    def get(self, entity_id: str) -> t.Optional[EntityAIBinding]:
        return self._by_id.get(entity_id)

    def by_kind(
        self, kind: EntityKind,
    ) -> tuple[EntityAIBinding, ...]:
        return tuple(b for b in self._by_id.values() if b.kind == kind)

    def by_tier(
        self, tier: AITier,
    ) -> tuple[EntityAIBinding, ...]:
        return tuple(b for b in self._by_id.values() if b.tier == tier)

    def all_live(self) -> tuple[EntityAIBinding, ...]:
        return tuple(b for b in self._by_id.values() if b.is_live())

    def touch(self, *, entity_id: str, now_seconds: float) -> bool:
        b = self._by_id.get(entity_id)
        if b is None:
            return False
        b.last_active_at_seconds = now_seconds
        return True

    def promote(
        self, *, entity_id: str, target_tier: AITier,
    ) -> BindResult:
        """Move an entity UP the tier ladder (closer to FLAGSHIP)."""
        b = self._by_id.get(entity_id)
        if b is None:
            return BindResult(False, reason="not bound")
        if _tier_rank(target_tier) > _tier_rank(b.tier):
            return BindResult(
                False, reason="target tier is lower than current",
            )
        b.tier = target_tier
        return BindResult(True, binding=b)

    def demote(
        self, *, entity_id: str, target_tier: AITier,
    ) -> BindResult:
        """Move an entity DOWN the tier ladder (cheaper)."""
        b = self._by_id.get(entity_id)
        if b is None:
            return BindResult(False, reason="not bound")
        if _tier_rank(target_tier) < _tier_rank(b.tier):
            return BindResult(
                False, reason="target tier is higher than current",
            )
        b.tier = target_tier
        return BindResult(True, binding=b)

    def stale_bindings(
        self, *, now_seconds: float, max_age_seconds: float,
    ) -> tuple[EntityAIBinding, ...]:
        return tuple(
            b for b in self._by_id.values()
            if (now_seconds - b.last_active_at_seconds)
            > max_age_seconds
        )

    def summary(self) -> dict[AITier, int]:
        out: dict[AITier, int] = {t: 0 for t in AITier}
        for b in self._by_id.values():
            out[b.tier] += 1
        return out


def _tier_rank(tier: AITier) -> int:
    """Lower = more compute. FLAGSHIP rank=0, INERT rank=4."""
    return DEMOTION_LADDER.index(tier)


def doctrine_audit(
    registry: EntityAIRegistry,
    expected_entity_ids: t.Iterable[str],
) -> tuple[str, ...]:
    """Verify the doctrine: every expected entity has a binding.
    Returns the IDs that have NO binding — those are the doctrine
    violations to fix."""
    bound = set(registry._by_id)
    return tuple(eid for eid in expected_entity_ids
                  if eid not in bound)


__all__ = [
    "EntityKind", "AITier", "DEMOTION_LADDER",
    "AgentProfile", "EntityAIBinding", "BindResult",
    "EntityAIRegistry",
    "doctrine_audit",
]
