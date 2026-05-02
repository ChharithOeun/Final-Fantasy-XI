"""Combat log — bounded event ring buffer.

Every actor-on-actor event lands here: damage, heal, miss, parry,
ASTRAL flow, debuff applied, debuff fell off, etc. The buffer is
bounded so it doesn't grow forever; once full, old entries fall off
the back. UI subscribers slice by actor, target, kind, or time
window.

Public surface
--------------
    EventKind enum
    CombatEvent immutable record
    CombatLog
        .record(event)
        .recent(limit)
        .filter(actor=, target=, kind=, since_tick=)
        .between(from_tick, to_tick)
        .summary_for(actor) - per-target totals
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


DEFAULT_BUFFER_SIZE = 1000


class EventKind(str, enum.Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    MISS = "miss"
    PARRY = "parry"
    BLOCK = "block"
    DODGE = "dodge"
    CRIT = "crit"
    DEBUFF_APPLIED = "debuff_applied"
    DEBUFF_REMOVED = "debuff_removed"
    BUFF_APPLIED = "buff_applied"
    BUFF_REMOVED = "buff_removed"
    DEATH = "death"
    SKILLCHAIN = "skillchain"
    MAGIC_BURST = "magic_burst"


@dataclasses.dataclass(frozen=True)
class CombatEvent:
    event_id: int
    tick: int
    kind: EventKind
    actor_id: str
    target_id: str
    amount: int = 0           # damage/heal magnitude; 0 for non-numeric
    label: str = ""           # ability/spell name etc.
    metadata: tuple[tuple[str, t.Any], ...] = ()


@dataclasses.dataclass
class CombatLog:
    capacity: int = DEFAULT_BUFFER_SIZE
    _next_id: int = 1
    _buffer: t.Deque[CombatEvent] = dataclasses.field(
        default_factory=collections.deque, repr=False,
    )

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        # Re-bound the deque with maxlen
        self._buffer = collections.deque(maxlen=self.capacity)

    def record(
        self, *,
        tick: int, kind: EventKind,
        actor_id: str, target_id: str,
        amount: int = 0, label: str = "",
        metadata: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> CombatEvent:
        event = CombatEvent(
            event_id=self._next_id, tick=tick, kind=kind,
            actor_id=actor_id, target_id=target_id,
            amount=amount, label=label,
            metadata=tuple((metadata or {}).items()),
        )
        self._buffer.append(event)
        self._next_id += 1
        return event

    @property
    def size(self) -> int:
        return len(self._buffer)

    def all_events(self) -> tuple[CombatEvent, ...]:
        return tuple(self._buffer)

    def recent(self, limit: int = 20) -> tuple[CombatEvent, ...]:
        return tuple(list(self._buffer)[-limit:])

    def filter(
        self, *,
        actor: t.Optional[str] = None,
        target: t.Optional[str] = None,
        kind: t.Optional[EventKind] = None,
        since_tick: t.Optional[int] = None,
    ) -> tuple[CombatEvent, ...]:
        out = []
        for e in self._buffer:
            if actor is not None and e.actor_id != actor:
                continue
            if target is not None and e.target_id != target:
                continue
            if kind is not None and e.kind != kind:
                continue
            if since_tick is not None and e.tick < since_tick:
                continue
            out.append(e)
        return tuple(out)

    def between(
        self, *, from_tick: int, to_tick: int,
    ) -> tuple[CombatEvent, ...]:
        if to_tick < from_tick:
            raise ValueError("to_tick < from_tick")
        return tuple(
            e for e in self._buffer
            if from_tick <= e.tick <= to_tick
        )

    def summary_for(
        self, actor_id: str,
    ) -> dict[str, int]:
        """Per-target damage totals attributed to this actor."""
        out: dict[str, int] = {}
        for e in self._buffer:
            if e.actor_id != actor_id:
                continue
            if e.kind not in (EventKind.DAMAGE, EventKind.CRIT):
                continue
            out[e.target_id] = out.get(e.target_id, 0) + e.amount
        return out


__all__ = [
    "DEFAULT_BUFFER_SIZE",
    "EventKind", "CombatEvent",
    "CombatLog",
]
