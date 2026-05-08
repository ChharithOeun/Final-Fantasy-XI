"""Diplomatic treaties — formal pacts between nations.

Beyond the conquest_tally war state, nations can sign
TREATIES that change how their borders, economies, and
military commitments interact.

Treaty kinds:
    NON_AGGRESSION      both sides forbid PvP attacks
                        between citizens; outlaw_system
                        treats cross-border kills with
                        bonus penalty
    MUTUAL_DEFENSE      a third-party attack on either
                        nation triggers the other to
                        defend (siege_system reads this
                        and assigns guard NPCs to assist)
    TRADE_TARIFF_REDUCED auction-house listing fees
                        between the two nations halve
    REFUGEE_PERMIT      players from one nation can
                        homepoint in the other's town
    EXTRADITION         outlaws committed in one nation
                        get transferred to that nation's
                        adjudicator if found in the other
    SHARED_RESOURCE     mining/harvesting nodes in shared
                        zones can be worked by either
                        nation without faction penalty

A treaty is between EXACTLY TWO nations. Both signatories
must agree (sign() called by each). It enters force when
both have signed; it has a duration (in_force from
ratified_day to expires_day). Either party can terminate
early with a penalty event.

Public surface
--------------
    TreatyKind enum
    TreatyState enum
    Treaty dataclass (frozen)
    DiplomaticTreaties
        .draft_treaty(treaty) -> bool
        .sign(treaty_id, nation, now_day) -> bool
        .terminate(treaty_id, by_nation, now_day) -> bool
        .tick(now_day) -> list[str]   # ids that expired
        .state(treaty_id) -> Optional[TreatyState]
        .active_treaties_for(nation) -> list[Treaty]
        .have_treaty(nation_a, nation_b, kind) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TreatyKind(str, enum.Enum):
    NON_AGGRESSION = "non_aggression"
    MUTUAL_DEFENSE = "mutual_defense"
    TRADE_TARIFF_REDUCED = "trade_tariff_reduced"
    REFUGEE_PERMIT = "refugee_permit"
    EXTRADITION = "extradition"
    SHARED_RESOURCE = "shared_resource"


class TreatyState(str, enum.Enum):
    DRAFTED = "drafted"
    HALF_SIGNED = "half_signed"
    IN_FORCE = "in_force"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclasses.dataclass(frozen=True)
class Treaty:
    treaty_id: str
    nation_a: str
    nation_b: str
    kind: TreatyKind
    drafted_day: int
    duration_days: int


def _key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclasses.dataclass
class _TState:
    spec: Treaty
    state: TreatyState = TreatyState.DRAFTED
    signed_by: set[str] = dataclasses.field(default_factory=set)
    ratified_day: t.Optional[int] = None


@dataclasses.dataclass
class DiplomaticTreaties:
    _treaties: dict[str, _TState] = dataclasses.field(
        default_factory=dict,
    )

    def draft_treaty(self, treaty: Treaty) -> bool:
        if not treaty.treaty_id:
            return False
        if not treaty.nation_a or not treaty.nation_b:
            return False
        if treaty.nation_a == treaty.nation_b:
            return False
        if treaty.duration_days <= 0:
            return False
        if treaty.treaty_id in self._treaties:
            return False
        self._treaties[treaty.treaty_id] = _TState(
            spec=treaty,
        )
        return True

    def sign(
        self, *, treaty_id: str, nation: str, now_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        st = self._treaties[treaty_id]
        if st.state not in (
            TreatyState.DRAFTED, TreatyState.HALF_SIGNED,
        ):
            return False
        if nation not in (
            st.spec.nation_a, st.spec.nation_b,
        ):
            return False
        if nation in st.signed_by:
            return False
        st.signed_by.add(nation)
        if len(st.signed_by) == 1:
            st.state = TreatyState.HALF_SIGNED
        else:
            st.state = TreatyState.IN_FORCE
            st.ratified_day = now_day
        return True

    def terminate(
        self, *, treaty_id: str, by_nation: str,
        now_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        st = self._treaties[treaty_id]
        if st.state not in (
            TreatyState.IN_FORCE, TreatyState.HALF_SIGNED,
        ):
            return False
        if by_nation not in (
            st.spec.nation_a, st.spec.nation_b,
        ):
            return False
        st.state = TreatyState.TERMINATED
        return True

    def tick(self, *, now_day: int) -> list[str]:
        expired: list[str] = []
        for tid, st in self._treaties.items():
            if st.state != TreatyState.IN_FORCE:
                continue
            assert st.ratified_day is not None
            end = st.ratified_day + st.spec.duration_days
            if now_day >= end:
                st.state = TreatyState.EXPIRED
                expired.append(tid)
        return expired

    def state(
        self, *, treaty_id: str,
    ) -> t.Optional[TreatyState]:
        if treaty_id not in self._treaties:
            return None
        return self._treaties[treaty_id].state

    def active_treaties_for(
        self, *, nation: str,
    ) -> list[Treaty]:
        return sorted(
            (st.spec for st in self._treaties.values()
             if st.state == TreatyState.IN_FORCE
             and (
                 st.spec.nation_a == nation
                 or st.spec.nation_b == nation
             )),
            key=lambda tr: tr.treaty_id,
        )

    def have_treaty(
        self, *, nation_a: str, nation_b: str,
        kind: TreatyKind,
    ) -> bool:
        wanted = _key(nation_a, nation_b)
        for st in self._treaties.values():
            if st.state != TreatyState.IN_FORCE:
                continue
            if st.spec.kind != kind:
                continue
            actual = _key(st.spec.nation_a, st.spec.nation_b)
            if actual == wanted:
                return True
        return False


__all__ = [
    "TreatyKind", "TreatyState", "Treaty",
    "DiplomaticTreaties",
]
