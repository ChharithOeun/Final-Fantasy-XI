"""Player gossip column — published rumor with hush option.

A columnist runs a gossip column. Tipsters submit rumors
about other players. The columnist reviews each tip, then
publishes (printing it for renown damage to the subject) or
rejects it. Subjects who get wind of an incoming tip can pay
a hush fee directly to the columnist before publication —
the tip moves to SUPPRESSED, the gil is paid, and the rumor
is killed. This creates a small adversarial economy: tip in
hand is leverage, and a rich subject can sometimes buy
silence, but a poor or proud one cannot.

Lifecycle (tip)
    SUBMITTED      awaiting columnist decision
    PUBLISHED      printed; renown damage to subject
    REJECTED       columnist passed on it
    SUPPRESSED     subject paid hush fee; killed pre-press

Public surface
--------------
    TipState enum
    GossipColumn dataclass (frozen)
    Tip dataclass (frozen)
    PlayerGossipColumnSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_HUSH_FLOOR = 500


class TipState(str, enum.Enum):
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"


@dataclasses.dataclass(frozen=True)
class GossipColumn:
    column_id: str
    columnist_id: str
    name: str
    byline: str
    earnings_gil: int


@dataclasses.dataclass(frozen=True)
class Tip:
    tip_id: str
    column_id: str
    tipster_id: str
    subject_id: str
    claim: str
    state: TipState
    hush_paid_gil: int


@dataclasses.dataclass
class _CState:
    spec: GossipColumn
    tips: dict[str, Tip] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerGossipColumnSystem:
    _columns: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next_column: int = 1
    _next_tip: int = 1

    def start_column(
        self, *, columnist_id: str, name: str,
        byline: str,
    ) -> t.Optional[str]:
        if not columnist_id or not name or not byline:
            return None
        cid = f"col_{self._next_column}"
        self._next_column += 1
        self._columns[cid] = _CState(
            spec=GossipColumn(
                column_id=cid,
                columnist_id=columnist_id,
                name=name, byline=byline,
                earnings_gil=0,
            ),
        )
        return cid

    def submit_tip(
        self, *, column_id: str, tipster_id: str,
        subject_id: str, claim: str,
    ) -> t.Optional[str]:
        if column_id not in self._columns:
            return None
        st = self._columns[column_id]
        if not tipster_id or not subject_id or not claim:
            return None
        if tipster_id == st.spec.columnist_id:
            return None
        if subject_id == tipster_id:
            return None
        if subject_id == st.spec.columnist_id:
            return None
        tid = f"tip_{self._next_tip}"
        self._next_tip += 1
        st.tips[tid] = Tip(
            tip_id=tid, column_id=column_id,
            tipster_id=tipster_id,
            subject_id=subject_id, claim=claim,
            state=TipState.SUBMITTED, hush_paid_gil=0,
        )
        return tid

    def publish_tip(
        self, *, column_id: str, tip_id: str,
        columnist_id: str,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if st.spec.columnist_id != columnist_id:
            return False
        if tip_id not in st.tips:
            return False
        tip = st.tips[tip_id]
        if tip.state != TipState.SUBMITTED:
            return False
        st.tips[tip_id] = dataclasses.replace(
            tip, state=TipState.PUBLISHED,
        )
        return True

    def reject_tip(
        self, *, column_id: str, tip_id: str,
        columnist_id: str,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if st.spec.columnist_id != columnist_id:
            return False
        if tip_id not in st.tips:
            return False
        tip = st.tips[tip_id]
        if tip.state != TipState.SUBMITTED:
            return False
        st.tips[tip_id] = dataclasses.replace(
            tip, state=TipState.REJECTED,
        )
        return True

    def offer_hush(
        self, *, column_id: str, tip_id: str,
        subject_id: str, gil_offered: int,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if tip_id not in st.tips:
            return False
        tip = st.tips[tip_id]
        if tip.state != TipState.SUBMITTED:
            return False
        if tip.subject_id != subject_id:
            return False
        if gil_offered < _HUSH_FLOOR:
            return False
        st.tips[tip_id] = dataclasses.replace(
            tip, state=TipState.SUPPRESSED,
            hush_paid_gil=gil_offered,
        )
        st.spec = dataclasses.replace(
            st.spec,
            earnings_gil=(
                st.spec.earnings_gil + gil_offered
            ),
        )
        return True

    def column(
        self, *, column_id: str,
    ) -> t.Optional[GossipColumn]:
        st = self._columns.get(column_id)
        return st.spec if st else None

    def tip(
        self, *, column_id: str, tip_id: str,
    ) -> t.Optional[Tip]:
        st = self._columns.get(column_id)
        if st is None:
            return None
        return st.tips.get(tip_id)

    def tips_by_subject(
        self, *, column_id: str, subject_id: str,
    ) -> list[Tip]:
        st = self._columns.get(column_id)
        if st is None:
            return []
        return [
            t for t in st.tips.values()
            if t.subject_id == subject_id
        ]

    def published_count(
        self, *, column_id: str,
    ) -> int:
        st = self._columns.get(column_id)
        if st is None:
            return 0
        return sum(
            1 for t in st.tips.values()
            if t.state == TipState.PUBLISHED
        )


__all__ = [
    "TipState", "GossipColumn", "Tip",
    "PlayerGossipColumnSystem",
]
