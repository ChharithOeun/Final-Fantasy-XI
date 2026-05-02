"""Instance engine — generic timed-instance dispatcher.

Drives BCNM (Battle Council NM), ENM (Empty Notorious Monster),
KSNM (Kindred Seal NM), Salvage runs, Walks of Echoes, etc.

Lifecycle
---------
    Definition -> Reservation (queued) -> Active -> Resolved
    /                                              \\__ exit cleanup
    \\______________________________ Cancelled (timeout/abort)

Pure-function design: caller supplies *now* in seconds, no
wall-clock reads, no IO.

Public surface
--------------
    InstanceState enum
    InstanceDefinition
    InstanceRecord
    InstanceEngine
        .define(definition) -> bool
        .reserve(definition_id, party_ids, now) -> Optional[record]
        .activate(record_id, now) -> bool
        .complete(record_id, now, victory) -> ResolveResult
        .cancel(record_id, now) -> bool
        .tick(now) — auto-cancel timed-out actives
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DEFAULT_INSTANCE_TIMER_SECONDS = 30 * 60   # 30-min battlefield
DEFAULT_RESERVATION_TTL_SECONDS = 5 * 60   # how long a queued slot holds


class InstanceState(str, enum.Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


@dataclasses.dataclass(frozen=True)
class InstanceDefinition:
    definition_id: str
    label: str
    min_party_size: int = 1
    max_party_size: int = 6
    timer_seconds: int = DEFAULT_INSTANCE_TIMER_SECONDS
    reservation_ttl: int = DEFAULT_RESERVATION_TTL_SECONDS


@dataclasses.dataclass
class InstanceRecord:
    record_id: str
    definition_id: str
    party_ids: tuple[str, ...]
    state: InstanceState = InstanceState.QUEUED
    queued_at: float = 0.0
    activated_at: t.Optional[float] = None
    resolved_at: t.Optional[float] = None
    victory: bool = False


@dataclasses.dataclass(frozen=True)
class ResolveResult:
    accepted: bool
    duration_seconds: float = 0.0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class InstanceEngine:
    _defs: dict[str, InstanceDefinition] = dataclasses.field(
        default_factory=dict,
    )
    _records: dict[str, InstanceRecord] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    # ------------------------------------------------------------------
    # Definition registry
    # ------------------------------------------------------------------
    def define(self, *, definition: InstanceDefinition) -> bool:
        if definition.definition_id in self._defs:
            return False
        self._defs[definition.definition_id] = definition
        return True

    def get_definition(self, definition_id: str
                        ) -> t.Optional[InstanceDefinition]:
        return self._defs.get(definition_id)

    # ------------------------------------------------------------------
    # Reserve a slot (queue it)
    # ------------------------------------------------------------------
    def reserve(self, *, definition_id: str,
                 party_ids: t.Sequence[str],
                 now: float = 0.0,
                 record_id: t.Optional[str] = None
                 ) -> t.Optional[InstanceRecord]:
        d = self._defs.get(definition_id)
        if d is None:
            return None
        if not (d.min_party_size <= len(party_ids) <= d.max_party_size):
            return None
        rid = record_id or f"inst_{self._next_id}"
        self._next_id += 1
        rec = InstanceRecord(
            record_id=rid,
            definition_id=definition_id,
            party_ids=tuple(party_ids),
            queued_at=now,
        )
        self._records[rid] = rec
        return rec

    # ------------------------------------------------------------------
    # Activate (player crosses the entry portal)
    # ------------------------------------------------------------------
    def activate(self, *, record_id: str, now: float = 0.0) -> bool:
        rec = self._records.get(record_id)
        if rec is None or rec.state != InstanceState.QUEUED:
            return False
        d = self._defs[rec.definition_id]
        if now > rec.queued_at + d.reservation_ttl:
            rec.state = InstanceState.CANCELLED
            return False
        rec.state = InstanceState.ACTIVE
        rec.activated_at = now
        return True

    # ------------------------------------------------------------------
    # Complete (party wins or runs out of timer)
    # ------------------------------------------------------------------
    def complete(self, *, record_id: str, now: float = 0.0,
                  victory: bool = True) -> ResolveResult:
        rec = self._records.get(record_id)
        if rec is None:
            return ResolveResult(False, reason="no such record")
        if rec.state != InstanceState.ACTIVE:
            return ResolveResult(False, reason="not active")
        rec.state = InstanceState.RESOLVED
        rec.resolved_at = now
        rec.victory = victory
        duration = (now - (rec.activated_at or now))
        return ResolveResult(accepted=True,
                              duration_seconds=duration)

    def cancel(self, *, record_id: str, now: float = 0.0) -> bool:
        rec = self._records.get(record_id)
        if rec is None:
            return False
        if rec.state in (InstanceState.RESOLVED,
                          InstanceState.CANCELLED):
            return False
        rec.state = InstanceState.CANCELLED
        rec.resolved_at = now
        return True

    # ------------------------------------------------------------------
    # Time-driven sweep of expired actives + queues
    # ------------------------------------------------------------------
    def tick(self, *, now: float) -> int:
        cancelled = 0
        for rec in self._records.values():
            d = self._defs.get(rec.definition_id)
            if d is None:
                continue
            if (rec.state == InstanceState.QUEUED
                    and now > rec.queued_at + d.reservation_ttl):
                rec.state = InstanceState.CANCELLED
                rec.resolved_at = now
                cancelled += 1
            elif (rec.state == InstanceState.ACTIVE
                    and rec.activated_at is not None
                    and now > rec.activated_at + d.timer_seconds):
                rec.state = InstanceState.CANCELLED
                rec.resolved_at = now
                cancelled += 1
        return cancelled

    def get(self, record_id: str) -> t.Optional[InstanceRecord]:
        return self._records.get(record_id)


__all__ = [
    "DEFAULT_INSTANCE_TIMER_SECONDS",
    "DEFAULT_RESERVATION_TTL_SECONDS",
    "InstanceState",
    "InstanceDefinition",
    "InstanceRecord",
    "ResolveResult",
    "InstanceEngine",
]
