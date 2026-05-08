"""Player petitions — citizen pressure on offices.

Edicts and treaties happen at the office level; players
who don't hold office still want a say. This module is
the petition layer — anyone can DRAFT a petition
addressed to a specific office, others SIGN it, and once
it crosses a signature threshold the office MUST address
it.

A petition has:
    petition_id, addressed_office_id, drafter_id,
    title, body, signature_target,
    drafted_day, expires_day

Lifecycle:
    OPEN            accepting signatures
    QUORUM_MET      hit signature_target — pinned to
                    office's pending list
    ADDRESSED       office holder responded
                    (response: ACCEPT | REJECT | DEFER)
    EXPIRED         past expires_day with target unmet
    WITHDRAWN       drafter pulled it before quorum

Signing rules:
    - Citizens of the addressed office's nation only
    - Cannot sign your own petition (drafter is implicit
      first signer)
    - One signature per (player, petition)
    - Signing closed once QUORUM_MET / EXPIRED / etc

Response from office:
    - ACCEPT (drafter gets a small reputation boost,
      petition closed)
    - REJECT (drafter takes a small reputation hit,
      petition closed)
    - DEFER (queue for later, can re-address later)

Public surface
--------------
    PetitionState enum
    Response enum
    Petition dataclass (frozen)
    PlayerPetitions
        .draft_petition(petition, drafter_nation) -> bool
        .sign(petition_id, signer_id, signer_nation) -> bool
        .respond(petition_id, by_holder_id, response)
            -> bool
        .withdraw(petition_id, by_drafter_id) -> bool
        .tick(now_day) -> list[str]   # ids that expired
        .state(petition_id) -> Optional[PetitionState]
        .signature_count(petition_id) -> int
        .pending_for_office(office_id) -> list[Petition]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PetitionState(str, enum.Enum):
    OPEN = "open"
    QUORUM_MET = "quorum_met"
    ADDRESSED = "addressed"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class Response(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


@dataclasses.dataclass(frozen=True)
class Petition:
    petition_id: str
    addressed_office_id: str
    drafter_id: str
    title: str
    body: str
    signature_target: int
    drafted_day: int
    expires_day: int
    nation: str  # nation the office belongs to


@dataclasses.dataclass
class _PState:
    spec: Petition
    state: PetitionState = PetitionState.OPEN
    signers: set[str] = dataclasses.field(default_factory=set)
    response: t.Optional[Response] = None
    holder_responder_id: t.Optional[str] = None


@dataclasses.dataclass
class PlayerPetitions:
    _petitions: dict[str, _PState] = dataclasses.field(
        default_factory=dict,
    )

    def draft_petition(
        self, petition: Petition,
        *, drafter_nation: str,
    ) -> bool:
        if not petition.petition_id:
            return False
        if not petition.drafter_id or not petition.title:
            return False
        if not petition.body:
            return False
        if petition.signature_target <= 0:
            return False
        if petition.expires_day <= petition.drafted_day:
            return False
        if drafter_nation != petition.nation:
            return False
        if petition.petition_id in self._petitions:
            return False
        st = _PState(spec=petition)
        st.signers.add(petition.drafter_id)  # drafter
        self._petitions[petition.petition_id] = st
        # If target is 1, immediately quorum-met
        if len(st.signers) >= petition.signature_target:
            st.state = PetitionState.QUORUM_MET
        return True

    def sign(
        self, *, petition_id: str, signer_id: str,
        signer_nation: str,
    ) -> bool:
        if petition_id not in self._petitions:
            return False
        st = self._petitions[petition_id]
        if st.state != PetitionState.OPEN:
            return False
        if signer_nation != st.spec.nation:
            return False
        if signer_id in st.signers:
            return False
        st.signers.add(signer_id)
        if len(st.signers) >= st.spec.signature_target:
            st.state = PetitionState.QUORUM_MET
        return True

    def respond(
        self, *, petition_id: str, by_holder_id: str,
        response: Response,
    ) -> bool:
        if petition_id not in self._petitions:
            return False
        st = self._petitions[petition_id]
        if st.state != PetitionState.QUORUM_MET:
            return False
        if not by_holder_id:
            return False
        st.state = PetitionState.ADDRESSED
        st.response = response
        st.holder_responder_id = by_holder_id
        return True

    def withdraw(
        self, *, petition_id: str, by_drafter_id: str,
    ) -> bool:
        if petition_id not in self._petitions:
            return False
        st = self._petitions[petition_id]
        if st.state != PetitionState.OPEN:
            return False
        if by_drafter_id != st.spec.drafter_id:
            return False
        st.state = PetitionState.WITHDRAWN
        return True

    def tick(self, *, now_day: int) -> list[str]:
        expired: list[str] = []
        for pid, st in self._petitions.items():
            if st.state != PetitionState.OPEN:
                continue
            if now_day >= st.spec.expires_day:
                st.state = PetitionState.EXPIRED
                expired.append(pid)
        return expired

    def state(
        self, *, petition_id: str,
    ) -> t.Optional[PetitionState]:
        if petition_id not in self._petitions:
            return None
        return self._petitions[petition_id].state

    def signature_count(
        self, *, petition_id: str,
    ) -> int:
        if petition_id not in self._petitions:
            return 0
        return len(self._petitions[petition_id].signers)

    def pending_for_office(
        self, *, office_id: str,
    ) -> list[Petition]:
        return sorted(
            (st.spec for st in self._petitions.values()
             if st.spec.addressed_office_id == office_id
             and st.state == PetitionState.QUORUM_MET),
            key=lambda p: p.petition_id,
        )

    def response_of(
        self, *, petition_id: str,
    ) -> t.Optional[Response]:
        if petition_id not in self._petitions:
            return None
        return self._petitions[petition_id].response


__all__ = [
    "PetitionState", "Response", "Petition",
    "PlayerPetitions",
]
