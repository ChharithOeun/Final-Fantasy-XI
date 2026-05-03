"""Per-entity persistent memory.

Every AI-driven entity in Demoncore — players, mobs, NMs, bosses,
NPCs, beastmen factions — has a memory store. The store persists
across sessions and across the entity's individual lifetime
(when an NM despawns and respawns the next ToD window, the
NEW instance inherits the memory of the prior one if the AI
deems it the same persona).

Memory shapes the way the AI plays the entity: an NPC remembers
the player who returned the lost necklace and greets them warmly;
a fomor warlord remembers the adventurer who slaughtered his
party last week and opens with Mighty Strikes; a Trust-NPC
remembers being abandoned during a fight and is reluctant to
follow.

Memory model
------------
A `Memory` is one event the entity has filed. It carries:
* what happened (a tagged kind: HELPED / HURT / WITNESSED / etc)
* who else was involved (other_entity_id)
* a salience score [0, 100] for how strongly it weighs in
  decisions
* a created_at timestamp for decay
* free-form `details` for orchestrator prompt assembly

Each entity has an `EntityMemoryStore` that:
* enforces a per-entity capacity (oldest low-salience memories
  fall out first)
* decays salience over time (HALF_LIFE_SECONDS controls the
  rate; severe events decay slower)
* exposes filtered queries by other entity, by kind, since N
  seconds ago, etc.

The orchestrator's prompt assembly does:
    relevant = store.about(other_entity_id=player_id, top_n=5)
    prompt += "Memories:\\n" + format_memories(relevant)

Public surface
--------------
    MemoryKind enum
    Memory dataclass (frozen)
    EntityMemoryStore
        .remember(...) / .about(other_entity_id=..., top_n=...)
        .by_kind(...) / .since(now_seconds, max_age_seconds)
        .salience_at(memory_id, now_seconds)
        .compact(now_seconds, capacity)
    MemoryRegistry — global, holds one store per entity
        .store_for(entity_id) -> EntityMemoryStore
        .remember(entity_id=..., ...) — convenience pass-through
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default capacity; entities can override per-store.
DEFAULT_CAPACITY = 200
# After this many seconds of game-time, salience halves.
DEFAULT_HALF_LIFE_SECONDS = 60 * 60 * 24 * 7    # 1 week game-time
# Max salience the system permits. 0 = totally forgotten.
SALIENCE_MAX = 100
SALIENCE_FORGOTTEN = 0


class MemoryKind(str, enum.Enum):
    """Tag describing what kind of event was filed.

    PRO/CON-flavored tags carry the AI's "is this person on my
    side?" inference; UTILITY tags are factual notes."""
    # PRO — the other entity helped or pleased
    HELPED = "helped"                   # gave gift, returned item
    SAVED = "saved"                     # rescued from death
    DEFENDED = "defended"               # took aggro / blocked
    GIFTED = "gifted"
    QUEST_COMPLETED = "quest_completed"
    PARDONED = "pardoned"

    # CON — the other entity hurt or angered
    HURT = "hurt"
    KILLED = "killed"
    BETRAYED = "betrayed"               # broke an oath / contract
    ABANDONED = "abandoned"             # left during fight
    INSULTED = "insulted"
    STOLE_FROM = "stole_from"

    # UTILITY — factual, non-emotional notes
    WITNESSED = "witnessed"
    HEARD_RUMOR = "heard_rumor"
    OBSERVED_LOCATION = "observed_location"
    LEARNED_FACT = "learned_fact"
    ENCOUNTERED = "encountered"


# Some memory kinds are TRAUMA — they decay much slower because
# the entity will not soon forget. The half-life multiplier here
# is applied to the base half-life.
_DECAY_MULTIPLIER: dict[MemoryKind, float] = {
    MemoryKind.KILLED: 8.0,            # essentially permanent
    MemoryKind.SAVED: 6.0,
    MemoryKind.BETRAYED: 5.0,
    MemoryKind.PARDONED: 4.0,
    MemoryKind.QUEST_COMPLETED: 3.0,
    MemoryKind.ABANDONED: 3.0,
    # Default = 1.0 (everything else)
}


def _half_life_for(kind: MemoryKind, base: float) -> float:
    return base * _DECAY_MULTIPLIER.get(kind, 1.0)


@dataclasses.dataclass(frozen=True)
class Memory:
    memory_id: str
    kind: MemoryKind
    other_entity_id: t.Optional[str]
    initial_salience: int
    created_at_seconds: float
    details: str = ""

    def __post_init__(self) -> None:
        if not (
            SALIENCE_FORGOTTEN
            <= self.initial_salience
            <= SALIENCE_MAX
        ):
            raise ValueError(
                f"initial_salience {self.initial_salience} out of "
                f"range 0-{SALIENCE_MAX}",
            )


def decay_salience(
    memory: Memory, *, now_seconds: float,
    half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS,
) -> int:
    """Compute current salience after exponential decay."""
    age = now_seconds - memory.created_at_seconds
    if age < 0:
        age = 0
    hl = _half_life_for(memory.kind, half_life_seconds)
    if hl <= 0:
        return memory.initial_salience
    decayed = memory.initial_salience * (0.5 ** (age / hl))
    return max(SALIENCE_FORGOTTEN, int(round(decayed)))


@dataclasses.dataclass
class EntityMemoryStore:
    entity_id: str
    capacity: int = DEFAULT_CAPACITY
    half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS
    _memories: list[Memory] = dataclasses.field(default_factory=list)
    _next_id: int = 0

    def remember(
        self, *, kind: MemoryKind,
        other_entity_id: t.Optional[str] = None,
        salience: int = 50, now_seconds: float = 0.0,
        details: str = "",
    ) -> Memory:
        mem = Memory(
            memory_id=f"{self.entity_id}_mem_{self._next_id}",
            kind=kind,
            other_entity_id=other_entity_id,
            initial_salience=salience,
            created_at_seconds=now_seconds,
            details=details,
        )
        self._next_id += 1
        self._memories.append(mem)
        # Capacity guard.
        if len(self._memories) > self.capacity:
            self._memories.pop(0)   # drop oldest
        return mem

    @property
    def memories(self) -> tuple[Memory, ...]:
        return tuple(self._memories)

    def by_kind(self, kind: MemoryKind) -> tuple[Memory, ...]:
        return tuple(m for m in self._memories if m.kind == kind)

    def about(
        self, *, other_entity_id: str, now_seconds: float = 0.0,
        top_n: t.Optional[int] = None,
    ) -> tuple[Memory, ...]:
        """All memories involving the named other entity, ranked
        by current (decayed) salience descending."""
        candidates = [
            m for m in self._memories
            if m.other_entity_id == other_entity_id
        ]
        candidates.sort(
            key=lambda m: decay_salience(
                m, now_seconds=now_seconds,
                half_life_seconds=self.half_life_seconds,
            ),
            reverse=True,
        )
        if top_n is not None:
            candidates = candidates[:top_n]
        return tuple(candidates)

    def since(
        self, *, now_seconds: float, max_age_seconds: float,
    ) -> tuple[Memory, ...]:
        cutoff = now_seconds - max_age_seconds
        return tuple(
            m for m in self._memories
            if m.created_at_seconds >= cutoff
        )

    def salience_at(
        self, *, memory_id: str, now_seconds: float,
    ) -> t.Optional[int]:
        for m in self._memories:
            if m.memory_id == memory_id:
                return decay_salience(
                    m, now_seconds=now_seconds,
                    half_life_seconds=self.half_life_seconds,
                )
        return None

    def compact(self, *, now_seconds: float) -> int:
        """Drop memories whose decayed salience is 0. Returns
        number dropped."""
        before = len(self._memories)
        self._memories = [
            m for m in self._memories
            if decay_salience(
                m, now_seconds=now_seconds,
                half_life_seconds=self.half_life_seconds,
            ) > SALIENCE_FORGOTTEN
        ]
        return before - len(self._memories)

    def total_with(self, other_entity_id: str) -> int:
        return sum(
            1 for m in self._memories
            if m.other_entity_id == other_entity_id
        )


@dataclasses.dataclass
class MemoryRegistry:
    """Global registry: one EntityMemoryStore per entity."""
    _stores: dict[str, EntityMemoryStore] = dataclasses.field(
        default_factory=dict,
    )

    def store_for(
        self, entity_id: str, *,
        capacity: int = DEFAULT_CAPACITY,
        half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS,
    ) -> EntityMemoryStore:
        s = self._stores.get(entity_id)
        if s is None:
            s = EntityMemoryStore(
                entity_id=entity_id, capacity=capacity,
                half_life_seconds=half_life_seconds,
            )
            self._stores[entity_id] = s
        return s

    def remember(
        self, *, entity_id: str, kind: MemoryKind,
        other_entity_id: t.Optional[str] = None,
        salience: int = 50, now_seconds: float = 0.0,
        details: str = "",
    ) -> Memory:
        return self.store_for(entity_id).remember(
            kind=kind, other_entity_id=other_entity_id,
            salience=salience, now_seconds=now_seconds,
            details=details,
        )

    def total_entities(self) -> int:
        return len(self._stores)


__all__ = [
    "DEFAULT_CAPACITY", "DEFAULT_HALF_LIFE_SECONDS",
    "SALIENCE_MAX", "SALIENCE_FORGOTTEN",
    "MemoryKind", "Memory",
    "decay_salience",
    "EntityMemoryStore", "MemoryRegistry",
]
