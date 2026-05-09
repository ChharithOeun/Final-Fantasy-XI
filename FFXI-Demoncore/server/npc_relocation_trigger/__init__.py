"""NPC relocation trigger — atomic ripple on defection.

When an NPC moves (defection, retirement, exile,
death), MULTIPLE downstream systems need to update at
once: dialogue routing, cutscene recast flags, quest
anchor location lookups, and the player-facing journal.
A relocation event that updates ONE system but misses
the others creates the wiki problem the user
identified — quest start location says Bastok but the
NPC is in Windy.

This module is the FAN-OUT POINT: caller emits a single
RelocationEvent and the system records it in an
audit log. Caller hooks (registered as callbacks) are
fired in deterministic order and any failure is
captured per-hook so partial failures are visible.

Event kinds:
    DEFECTED          NPC switched faction
    DECEASED          NPC died
    RETIRED           NPC stepped down
    EXILED            NPC banished
    APPOINTED_HOME    NPC returned home (defection
                      reverse)

Public surface
--------------
    RelocationKind enum
    RelocationEvent dataclass (frozen)
    HookResult dataclass (frozen)
    NPCRelocationTriggerSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RelocationKind(str, enum.Enum):
    DEFECTED = "defected"
    DECEASED = "deceased"
    RETIRED = "retired"
    EXILED = "exiled"
    APPOINTED_HOME = "appointed_home"


@dataclasses.dataclass(frozen=True)
class RelocationEvent:
    event_id: str
    npc_id: str
    kind: RelocationKind
    from_faction: str
    to_faction: str
    occurred_day: int
    note: str


@dataclasses.dataclass(frozen=True)
class HookResult:
    event_id: str
    hook_name: str
    succeeded: bool
    details: str


HookFn = t.Callable[[RelocationEvent], bool]


@dataclasses.dataclass
class NPCRelocationTriggerSystem:
    _hooks: list[tuple[str, HookFn]] = (
        dataclasses.field(default_factory=list)
    )
    _events: dict[str, RelocationEvent] = (
        dataclasses.field(default_factory=dict)
    )
    _hook_results: dict[
        str, list[HookResult]
    ] = dataclasses.field(default_factory=dict)
    _next_id: int = 1

    def register_hook(
        self, *, name: str, fn: HookFn,
    ) -> bool:
        if not name:
            return False
        # Block duplicate hook names
        if any(n == name for n, _ in self._hooks):
            return False
        self._hooks.append((name, fn))
        return True

    def emit(
        self, *, npc_id: str,
        kind: RelocationKind, from_faction: str,
        to_faction: str, occurred_day: int,
        note: str = "",
    ) -> t.Optional[str]:
        if not npc_id:
            return None
        if not from_faction:
            return None
        if kind == RelocationKind.DECEASED:
            # to_faction blank for death is fine
            pass
        elif not to_faction:
            return None
        if occurred_day < 0:
            return None
        eid = f"reloc_{self._next_id}"
        self._next_id += 1
        ev = RelocationEvent(
            event_id=eid, npc_id=npc_id, kind=kind,
            from_faction=from_faction,
            to_faction=to_faction,
            occurred_day=occurred_day, note=note,
        )
        self._events[eid] = ev
        results: list[HookResult] = []
        for name, fn in self._hooks:
            try:
                ok = bool(fn(ev))
                results.append(HookResult(
                    event_id=eid, hook_name=name,
                    succeeded=ok,
                    details="ok" if ok else "hook_returned_false",
                ))
            except Exception as exc:  # noqa
                results.append(HookResult(
                    event_id=eid, hook_name=name,
                    succeeded=False,
                    details=f"exception: {exc!r}",
                ))
        self._hook_results[eid] = results
        return eid

    def event(
        self, *, event_id: str,
    ) -> t.Optional[RelocationEvent]:
        return self._events.get(event_id)

    def hook_results(
        self, *, event_id: str,
    ) -> list[HookResult]:
        return list(
            self._hook_results.get(event_id, ()),
        )

    def all_events_for(
        self, *, npc_id: str,
    ) -> list[RelocationEvent]:
        return sorted(
            (e for e in self._events.values()
             if e.npc_id == npc_id),
            key=lambda e: e.occurred_day,
        )

    def failed_hooks_for(
        self, *, event_id: str,
    ) -> list[HookResult]:
        return [
            r for r in self._hook_results.get(
                event_id, (),
            ) if not r.succeeded
        ]

    def hook_count(self) -> int:
        return len(self._hooks)


__all__ = [
    "RelocationKind", "RelocationEvent",
    "HookResult", "NPCRelocationTriggerSystem",
]
