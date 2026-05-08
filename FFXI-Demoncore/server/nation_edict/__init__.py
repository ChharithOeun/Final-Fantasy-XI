"""Nation edict — leadership-issued laws with effect periods.

A seated governor (or ruling council) can issue
EDICTS — formal laws that take effect for a defined
period. Edicts have categories that signal what they
modify: tax rates, gate hours, conscription quotas,
public-works funding, religious decrees, and so on.

The data layer doesn't enforce the effect — it tracks
the edict, its effective_from / effective_until window,
and its CURRENT/EXPIRED/REPEALED state. Other modules
(taxation, conscription, etc.) query active_edicts()
and apply effects as they see fit.

Edicts can be REPEALED (early termination by the same
or successor authority), AMENDED (a new edict
supersedes an old one cleanly), or simply EXPIRE.

Public surface
--------------
    EdictKind enum (10 kinds)
    EdictState enum
    Edict dataclass (frozen)
    NationEdictSystem
        .issue(nation_id, kind, title, body,
               issuer_id, effective_from,
               effective_until) -> Optional[str]
        .repeal(edict_id, repealer_id, now_day,
                reason) -> bool
        .amend(old_edict_id, new_edict_id,
               now_day) -> bool
        .tick(now_day) -> list[(edict_id, EdictState)]
        .active_for(nation_id, kind, now_day) ->
                                list[Edict]
        .edict(edict_id) -> Optional[Edict]
        .edicts_by_nation(nation_id) -> list[Edict]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EdictKind(str, enum.Enum):
    TAX_RATE = "tax_rate"
    GATE_HOURS = "gate_hours"
    CONSCRIPTION = "conscription"
    PUBLIC_WORKS = "public_works"
    RELIGIOUS_DECREE = "religious_decree"
    PARDON_AMNESTY = "pardon_amnesty"
    TRADE_TARIFF = "trade_tariff"
    CURFEW = "curfew"
    BOUNTY_INCREASE = "bounty_increase"
    HOLIDAY_DECLARATION = "holiday_declaration"


class EdictState(str, enum.Enum):
    PROPOSED = "proposed"
    CURRENT = "current"
    EXPIRED = "expired"
    REPEALED = "repealed"
    AMENDED = "amended"


@dataclasses.dataclass(frozen=True)
class Edict:
    edict_id: str
    nation_id: str
    kind: EdictKind
    title: str
    body: str
    issuer_id: str
    effective_from: int
    effective_until: int
    issued_day: int
    state: EdictState
    repealer_id: str
    repealed_day: t.Optional[int]
    repeal_reason: str
    superseded_by: t.Optional[str]


@dataclasses.dataclass
class NationEdictSystem:
    _edicts: dict[str, Edict] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def issue(
        self, *, nation_id: str, kind: EdictKind,
        title: str, body: str, issuer_id: str,
        effective_from: int, effective_until: int,
        issued_day: int = 0,
    ) -> t.Optional[str]:
        if not nation_id or not issuer_id:
            return None
        if not title or not body:
            return None
        if effective_from < 0:
            return None
        if effective_until <= effective_from:
            return None
        if issued_day < 0:
            return None
        eid = f"edict_{self._next_id}"
        self._next_id += 1
        # If issued_day already past effective_from,
        # state is CURRENT immediately; otherwise
        # PROPOSED until tick crosses effective_from.
        state = (
            EdictState.CURRENT
            if issued_day >= effective_from
            else EdictState.PROPOSED
        )
        self._edicts[eid] = Edict(
            edict_id=eid, nation_id=nation_id,
            kind=kind, title=title, body=body,
            issuer_id=issuer_id,
            effective_from=effective_from,
            effective_until=effective_until,
            issued_day=issued_day, state=state,
            repealer_id="", repealed_day=None,
            repeal_reason="", superseded_by=None,
        )
        return eid

    def repeal(
        self, *, edict_id: str, repealer_id: str,
        now_day: int, reason: str,
    ) -> bool:
        if edict_id not in self._edicts:
            return False
        if not repealer_id or not reason:
            return False
        e = self._edicts[edict_id]
        if e.state not in (
            EdictState.PROPOSED, EdictState.CURRENT,
        ):
            return False
        self._edicts[edict_id] = dataclasses.replace(
            e, state=EdictState.REPEALED,
            repealer_id=repealer_id,
            repealed_day=now_day,
            repeal_reason=reason,
        )
        return True

    def amend(
        self, *, old_edict_id: str,
        new_edict_id: str, now_day: int,
    ) -> bool:
        if old_edict_id not in self._edicts:
            return False
        if new_edict_id not in self._edicts:
            return False
        if old_edict_id == new_edict_id:
            return False
        old = self._edicts[old_edict_id]
        new = self._edicts[new_edict_id]
        if old.state not in (
            EdictState.PROPOSED, EdictState.CURRENT,
        ):
            return False
        if old.kind != new.kind:
            return False
        if old.nation_id != new.nation_id:
            return False
        self._edicts[old_edict_id] = (
            dataclasses.replace(
                old, state=EdictState.AMENDED,
                superseded_by=new_edict_id,
            )
        )
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, EdictState]]:
        changes: list[tuple[str, EdictState]] = []
        for eid, e in list(self._edicts.items()):
            if e.state == EdictState.PROPOSED:
                if now_day >= e.effective_from:
                    self._edicts[eid] = (
                        dataclasses.replace(
                            e, state=EdictState.CURRENT,
                        )
                    )
                    changes.append(
                        (eid, EdictState.CURRENT),
                    )
                    e = self._edicts[eid]
            if e.state == EdictState.CURRENT:
                if now_day >= e.effective_until:
                    self._edicts[eid] = (
                        dataclasses.replace(
                            e, state=EdictState.EXPIRED,
                        )
                    )
                    changes.append(
                        (eid, EdictState.EXPIRED),
                    )
        return changes

    def active_for(
        self, *, nation_id: str, kind: EdictKind,
        now_day: int,
    ) -> list[Edict]:
        return [
            e for e in self._edicts.values()
            if (e.nation_id == nation_id
                and e.kind == kind
                and e.state == EdictState.CURRENT
                and e.effective_from <= now_day
                < e.effective_until)
        ]

    def edict(
        self, *, edict_id: str,
    ) -> t.Optional[Edict]:
        return self._edicts.get(edict_id)

    def edicts_by_nation(
        self, *, nation_id: str,
    ) -> list[Edict]:
        return [
            e for e in self._edicts.values()
            if e.nation_id == nation_id
        ]


__all__ = [
    "EdictKind", "EdictState", "Edict",
    "NationEdictSystem",
]
