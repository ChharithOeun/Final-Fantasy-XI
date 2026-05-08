"""Edict system — passed laws that change gameplay.

Once political_offices have an executive in seat, that
executive can pass EDICTS — durations laws with
gameplay-affecting effects. Examples:

    TAX_REDUCTION         lower auction-house listing fees
                          server-wide-bastok by 30% for
                          14 days
    HUNTING_SEASON_OPEN   double XP from one mob family
                          for 7 days
    CURFEW                guards aggressive at night
                          to non-citizens for 30 days
    BOUNTY_INCREASE       +50% bounty payouts in this
                          nation's territory for 7 days
    FESTIVAL_DECREE       schedules a one-off festival
    CONSCRIPTION          force linkshells to provide
                          combatants for siege defense

An edict has:
    edict_id, nation, kind, parameters (kind-specific
    JSON-shaped dict), effective_day, sunset_day,
    proposer (the office holder), proposing_office_id

State machine:
    PROPOSED        announced, not yet active
    IN_FORCE        active; effects apply
    EXPIRED         past sunset_day
    REPEALED        manually killed before sunset

Repeal requires the SAME office that proposed it (or a
successor in that office). The legislature can override
by passing a "repeal_edict" of their own.

Public surface
--------------
    EdictKind enum
    EdictState enum
    Edict dataclass (frozen)
    EdictSystem
        .propose_edict(edict) -> bool
        .activate(edict_id, now_day) -> bool
        .repeal(edict_id, by_office_id) -> bool
        .tick(now_day) -> list[str]   # ids transitioned to expired
        .state(edict_id) -> Optional[EdictState]
        .active_edicts(nation) -> list[Edict]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EdictKind(str, enum.Enum):
    TAX_REDUCTION = "tax_reduction"
    HUNTING_SEASON_OPEN = "hunting_season_open"
    CURFEW = "curfew"
    BOUNTY_INCREASE = "bounty_increase"
    FESTIVAL_DECREE = "festival_decree"
    CONSCRIPTION = "conscription"


class EdictState(str, enum.Enum):
    PROPOSED = "proposed"
    IN_FORCE = "in_force"
    EXPIRED = "expired"
    REPEALED = "repealed"


@dataclasses.dataclass(frozen=True)
class Edict:
    edict_id: str
    nation: str
    kind: EdictKind
    parameters: t.Mapping[str, t.Any]
    proposer_id: str
    proposing_office_id: str
    proposed_day: int
    effective_day: int
    sunset_day: int


@dataclasses.dataclass
class _EdictState:
    spec: Edict
    state: EdictState = EdictState.PROPOSED


@dataclasses.dataclass
class EdictSystem:
    _edicts: dict[str, _EdictState] = dataclasses.field(
        default_factory=dict,
    )

    def propose_edict(self, edict: Edict) -> bool:
        if not edict.edict_id or not edict.nation:
            return False
        if not edict.proposer_id:
            return False
        if not edict.proposing_office_id:
            return False
        if edict.effective_day < edict.proposed_day:
            return False
        if edict.sunset_day <= edict.effective_day:
            return False
        if edict.edict_id in self._edicts:
            return False
        self._edicts[edict.edict_id] = _EdictState(
            spec=edict,
        )
        return True

    def activate(
        self, *, edict_id: str, now_day: int,
    ) -> bool:
        if edict_id not in self._edicts:
            return False
        st = self._edicts[edict_id]
        if st.state != EdictState.PROPOSED:
            return False
        if now_day < st.spec.effective_day:
            return False
        st.state = EdictState.IN_FORCE
        return True

    def repeal(
        self, *, edict_id: str, by_office_id: str,
    ) -> bool:
        if edict_id not in self._edicts:
            return False
        st = self._edicts[edict_id]
        if st.state not in (
            EdictState.PROPOSED, EdictState.IN_FORCE,
        ):
            return False
        if by_office_id != st.spec.proposing_office_id:
            return False
        st.state = EdictState.REPEALED
        return True

    def tick(self, *, now_day: int) -> list[str]:
        expired_ids: list[str] = []
        for eid, st in self._edicts.items():
            if st.state == EdictState.IN_FORCE:
                if now_day >= st.spec.sunset_day:
                    st.state = EdictState.EXPIRED
                    expired_ids.append(eid)
            elif st.state == EdictState.PROPOSED:
                # Auto-activate at effective day
                if now_day >= st.spec.effective_day:
                    st.state = EdictState.IN_FORCE
                # Plus check if it's already past sunset
                # — propose-then-late activation expires
                # immediately
                if now_day >= st.spec.sunset_day:
                    st.state = EdictState.EXPIRED
                    expired_ids.append(eid)
        return expired_ids

    def state(
        self, *, edict_id: str,
    ) -> t.Optional[EdictState]:
        if edict_id not in self._edicts:
            return None
        return self._edicts[edict_id].state

    def active_edicts(
        self, *, nation: str,
    ) -> list[Edict]:
        return sorted(
            (st.spec for st in self._edicts.values()
             if st.spec.nation == nation
             and st.state == EdictState.IN_FORCE),
            key=lambda e: e.edict_id,
        )

    def edicts_of_kind(
        self, *, nation: str, kind: EdictKind,
    ) -> list[Edict]:
        return [
            e for e in self.active_edicts(nation=nation)
            if e.kind == kind
        ]


__all__ = [
    "EdictKind", "EdictState", "Edict", "EdictSystem",
]
