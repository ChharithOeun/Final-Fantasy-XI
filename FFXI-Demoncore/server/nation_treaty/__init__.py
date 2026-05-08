"""Nation treaty — formal agreements between nations.

Two or more nations can sign a TREATY governing their
relationship: peace, trade, mutual defense, extradition.
Treaties have signatory parties, ratification status,
expiry dates, and termination clauses.

Lifecycle:
    DRAFTED        treaty text exists; signatories
                   not yet locked in
    SIGNED         all required signatories have
                   signed
    RATIFIED       activated and binding
    BREACHED       at least one party broke a clause
                   (caller decides; module records)
    TERMINATED     formally ended (expiry, mutual
                   dissolution, or post-breach)

TreatyKind classifies the agreement:
    PEACE           non-aggression pact
    TRADE           tariff reductions, market access
    MUTUAL_DEFENSE  attack one, attack all
    EXTRADITION     hand over fugitives
    NON_AGGRESSION  weaker than PEACE; just no
                    declared war
    CULTURAL        joint festivals, embassy exchange
    NEUTRALITY     declared neutrality in others' wars

Public surface
--------------
    TreatyKind enum
    TreatyState enum
    Treaty dataclass (frozen)
    NationTreatySystem
        .draft(treaty_id, kind, parties, terms,
               drafted_day, expiry_day) -> bool
        .sign(treaty_id, party, now_day) -> bool
        .ratify(treaty_id, now_day) -> bool
        .declare_breach(treaty_id, breaching_party,
                        now_day, evidence) -> bool
        .terminate(treaty_id, now_day, reason) -> bool
        .tick(now_day) -> list[(treaty_id, TreatyState)]
        .treaty(treaty_id) -> Optional[Treaty]
        .active_between(party_a, party_b,
                        now_day) -> list[Treaty]
        .all_treaties() -> list[Treaty]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TreatyKind(str, enum.Enum):
    PEACE = "peace"
    TRADE = "trade"
    MUTUAL_DEFENSE = "mutual_defense"
    EXTRADITION = "extradition"
    NON_AGGRESSION = "non_aggression"
    CULTURAL = "cultural"
    NEUTRALITY = "neutrality"


class TreatyState(str, enum.Enum):
    DRAFTED = "drafted"
    SIGNED = "signed"
    RATIFIED = "ratified"
    BREACHED = "breached"
    TERMINATED = "terminated"


@dataclasses.dataclass(frozen=True)
class Treaty:
    treaty_id: str
    kind: TreatyKind
    parties: tuple[str, ...]
    terms: str
    drafted_day: int
    expiry_day: int
    signed_by: tuple[str, ...]
    ratified_day: t.Optional[int]
    breaching_party: str
    breach_evidence: str
    terminated_day: t.Optional[int]
    termination_reason: str
    state: TreatyState


@dataclasses.dataclass
class NationTreatySystem:
    _treaties: dict[str, Treaty] = dataclasses.field(
        default_factory=dict,
    )

    def draft(
        self, *, treaty_id: str, kind: TreatyKind,
        parties: t.Sequence[str], terms: str,
        drafted_day: int, expiry_day: int,
    ) -> bool:
        if not treaty_id:
            return False
        if treaty_id in self._treaties:
            return False
        if len(parties) < 2:
            return False
        if len(set(parties)) != len(parties):
            return False
        if not terms:
            return False
        if drafted_day < 0:
            return False
        if expiry_day <= drafted_day:
            return False
        self._treaties[treaty_id] = Treaty(
            treaty_id=treaty_id, kind=kind,
            parties=tuple(parties), terms=terms,
            drafted_day=drafted_day,
            expiry_day=expiry_day, signed_by=(),
            ratified_day=None, breaching_party="",
            breach_evidence="", terminated_day=None,
            termination_reason="",
            state=TreatyState.DRAFTED,
        )
        return True

    def sign(
        self, *, treaty_id: str, party: str,
        now_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.DRAFTED:
            return False
        if party not in t_.parties:
            return False
        if party in t_.signed_by:
            return False
        new_signed = t_.signed_by + (party,)
        new_state = (
            TreatyState.SIGNED
            if set(new_signed) == set(t_.parties)
            else TreatyState.DRAFTED
        )
        self._treaties[treaty_id] = (
            dataclasses.replace(
                t_, signed_by=new_signed,
                state=new_state,
            )
        )
        return True

    def ratify(
        self, *, treaty_id: str, now_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.SIGNED:
            return False
        self._treaties[treaty_id] = (
            dataclasses.replace(
                t_, state=TreatyState.RATIFIED,
                ratified_day=now_day,
            )
        )
        return True

    def declare_breach(
        self, *, treaty_id: str,
        breaching_party: str, now_day: int,
        evidence: str,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.RATIFIED:
            return False
        if breaching_party not in t_.parties:
            return False
        if not evidence:
            return False
        self._treaties[treaty_id] = (
            dataclasses.replace(
                t_, state=TreatyState.BREACHED,
                breaching_party=breaching_party,
                breach_evidence=evidence,
            )
        )
        return True

    def terminate(
        self, *, treaty_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state == TreatyState.TERMINATED:
            return False
        if not reason:
            return False
        self._treaties[treaty_id] = (
            dataclasses.replace(
                t_, state=TreatyState.TERMINATED,
                terminated_day=now_day,
                termination_reason=reason,
            )
        )
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, TreatyState]]:
        changes: list[tuple[str, TreatyState]] = []
        for tid, t_ in list(self._treaties.items()):
            if t_.state == TreatyState.TERMINATED:
                continue
            if now_day >= t_.expiry_day:
                self._treaties[tid] = (
                    dataclasses.replace(
                        t_,
                        state=TreatyState.TERMINATED,
                        terminated_day=now_day,
                        termination_reason="expired",
                    )
                )
                changes.append(
                    (tid, TreatyState.TERMINATED),
                )
        return changes

    def treaty(
        self, *, treaty_id: str,
    ) -> t.Optional[Treaty]:
        return self._treaties.get(treaty_id)

    def active_between(
        self, *, party_a: str, party_b: str,
        now_day: int,
    ) -> list[Treaty]:
        return [
            t_ for t_ in self._treaties.values()
            if (party_a in t_.parties
                and party_b in t_.parties
                and t_.state == TreatyState.RATIFIED
                and now_day < t_.expiry_day)
        ]

    def all_treaties(self) -> list[Treaty]:
        return list(self._treaties.values())


__all__ = [
    "TreatyKind", "TreatyState", "Treaty",
    "NationTreatySystem",
]
