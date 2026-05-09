"""Player petition — signature drive for a public cause.

A founder launches a petition with a stated cause and a
goal_signatures threshold. Players sign once each. Once
the signature count reaches the goal, the petition auto-
resolves to RESOLVED — proof that there is enough public
support behind the cause to take to a magistrate or
legislative body. Founders can withdraw before resolution
if they change their mind.

Lifecycle
    OPEN          accepting signatures
    RESOLVED      goal reached
    WITHDRAWN     founder pulled it before goal

Public surface
--------------
    PetitionState enum
    Petition dataclass (frozen)
    PlayerPetitionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PetitionState(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    WITHDRAWN = "withdrawn"


@dataclasses.dataclass(frozen=True)
class Petition:
    petition_id: str
    founder_id: str
    cause: str
    goal_signatures: int
    state: PetitionState
    signature_count: int
    resolved_day: int


@dataclasses.dataclass
class _PState:
    spec: Petition
    signers: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerPetitionSystem:
    _petitions: dict[str, _PState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def launch(
        self, *, founder_id: str, cause: str,
        goal_signatures: int,
    ) -> t.Optional[str]:
        if not founder_id or not cause:
            return None
        if goal_signatures <= 0:
            return None
        pid = f"pet_{self._next}"
        self._next += 1
        self._petitions[pid] = _PState(
            spec=Petition(
                petition_id=pid,
                founder_id=founder_id, cause=cause,
                goal_signatures=goal_signatures,
                state=PetitionState.OPEN,
                signature_count=0, resolved_day=0,
            ),
        )
        return pid

    def sign(
        self, *, petition_id: str, signer_id: str,
        current_day: int,
    ) -> bool:
        if petition_id not in self._petitions:
            return False
        st = self._petitions[petition_id]
        if st.spec.state != PetitionState.OPEN:
            return False
        if not signer_id:
            return False
        if signer_id in st.signers:
            return False
        st.signers.add(signer_id)
        new_count = st.spec.signature_count + 1
        new_state = st.spec.state
        new_day = st.spec.resolved_day
        if new_count >= st.spec.goal_signatures:
            new_state = PetitionState.RESOLVED
            new_day = current_day
        st.spec = dataclasses.replace(
            st.spec, signature_count=new_count,
            state=new_state, resolved_day=new_day,
        )
        return True

    def withdraw(
        self, *, petition_id: str, founder_id: str,
    ) -> bool:
        if petition_id not in self._petitions:
            return False
        st = self._petitions[petition_id]
        if st.spec.state != PetitionState.OPEN:
            return False
        if st.spec.founder_id != founder_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=PetitionState.WITHDRAWN,
        )
        return True

    def petition(
        self, *, petition_id: str,
    ) -> t.Optional[Petition]:
        st = self._petitions.get(petition_id)
        return st.spec if st else None

    def signers(
        self, *, petition_id: str,
    ) -> list[str]:
        st = self._petitions.get(petition_id)
        if st is None:
            return []
        return sorted(st.signers)


__all__ = [
    "PetitionState", "Petition",
    "PlayerPetitionSystem",
]
