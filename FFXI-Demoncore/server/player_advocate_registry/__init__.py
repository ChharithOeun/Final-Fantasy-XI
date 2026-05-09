"""Player advocate registry — registered legal advocates.

A bar association registers advocates qualified to represent
parties in court. Each advocate has a specialty (a kind they
specialize in) and a track record of cases. Clients hire
advocates by paying a retainer; advocates can drop a client
for cause (returns half the retainer) or be discharged by
the client (no refund — penalty for switching mid-case).
The registry tracks lifetime case counts and win rates.

Lifecycle (retainer)
    ACTIVE        currently representing
    DROPPED       advocate left for cause (50% refund)
    DISCHARGED    client fired advocate (no refund)
    COMPLETED    case finished; advocate paid out

Public surface
--------------
    RetainerState enum
    Advocate dataclass (frozen)
    Retainer dataclass (frozen)
    PlayerAdvocateRegistrySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RetainerState(str, enum.Enum):
    ACTIVE = "active"
    DROPPED = "dropped"
    DISCHARGED = "discharged"
    COMPLETED = "completed"


@dataclasses.dataclass(frozen=True)
class Advocate:
    advocate_id: str
    name: str
    specialty: str
    retainer_fee_gil: int
    cases_taken: int
    cases_won: int


@dataclasses.dataclass(frozen=True)
class Retainer:
    retainer_id: str
    advocate_id: str
    client_id: str
    paid_gil: int
    state: RetainerState


@dataclasses.dataclass
class _AState:
    spec: Advocate
    # client_id -> active retainer_id
    active_retainers: dict[str, str] = (
        dataclasses.field(default_factory=dict)
    )
    retainers: dict[str, Retainer] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerAdvocateRegistrySystem:
    _advocates: dict[str, _AState] = dataclasses.field(
        default_factory=dict,
    )
    _next_adv: int = 1
    _next_ret: int = 1

    def register_advocate(
        self, *, advocate_id: str, name: str,
        specialty: str, retainer_fee_gil: int,
    ) -> bool:
        if not advocate_id or not name:
            return False
        if not specialty:
            return False
        if retainer_fee_gil <= 0:
            return False
        if advocate_id in self._advocates:
            return False
        self._advocates[advocate_id] = _AState(
            spec=Advocate(
                advocate_id=advocate_id, name=name,
                specialty=specialty,
                retainer_fee_gil=retainer_fee_gil,
                cases_taken=0, cases_won=0,
            ),
        )
        return True

    def hire(
        self, *, advocate_id: str, client_id: str,
    ) -> t.Optional[str]:
        if advocate_id not in self._advocates:
            return None
        st = self._advocates[advocate_id]
        if not client_id:
            return None
        if client_id == advocate_id:
            return None
        if client_id in st.active_retainers:
            return None
        rid = f"ret_{self._next_ret}"
        self._next_ret += 1
        fee = st.spec.retainer_fee_gil
        st.retainers[rid] = Retainer(
            retainer_id=rid, advocate_id=advocate_id,
            client_id=client_id, paid_gil=fee,
            state=RetainerState.ACTIVE,
        )
        st.active_retainers[client_id] = rid
        st.spec = dataclasses.replace(
            st.spec,
            cases_taken=st.spec.cases_taken + 1,
        )
        return rid

    def drop_client(
        self, *, advocate_id: str, client_id: str,
    ) -> t.Optional[int]:
        """Advocate drops client for cause; returns
        50% refund. None on failure."""
        if advocate_id not in self._advocates:
            return None
        st = self._advocates[advocate_id]
        if client_id not in st.active_retainers:
            return None
        rid = st.active_retainers[client_id]
        ret = st.retainers[rid]
        if ret.state != RetainerState.ACTIVE:
            return None
        refund = ret.paid_gil // 2
        st.retainers[rid] = dataclasses.replace(
            ret, state=RetainerState.DROPPED,
        )
        del st.active_retainers[client_id]
        return refund

    def discharge(
        self, *, advocate_id: str, client_id: str,
    ) -> bool:
        """Client fires advocate; no refund."""
        if advocate_id not in self._advocates:
            return False
        st = self._advocates[advocate_id]
        if client_id not in st.active_retainers:
            return False
        rid = st.active_retainers[client_id]
        ret = st.retainers[rid]
        if ret.state != RetainerState.ACTIVE:
            return False
        st.retainers[rid] = dataclasses.replace(
            ret, state=RetainerState.DISCHARGED,
        )
        del st.active_retainers[client_id]
        return True

    def complete_case(
        self, *, advocate_id: str, client_id: str,
        won: bool,
    ) -> bool:
        """Case ended; mark retainer COMPLETED and
        update advocate's win record if won."""
        if advocate_id not in self._advocates:
            return False
        st = self._advocates[advocate_id]
        if client_id not in st.active_retainers:
            return False
        rid = st.active_retainers[client_id]
        ret = st.retainers[rid]
        if ret.state != RetainerState.ACTIVE:
            return False
        st.retainers[rid] = dataclasses.replace(
            ret, state=RetainerState.COMPLETED,
        )
        del st.active_retainers[client_id]
        if won:
            st.spec = dataclasses.replace(
                st.spec,
                cases_won=st.spec.cases_won + 1,
            )
        return True

    def advocate(
        self, *, advocate_id: str,
    ) -> t.Optional[Advocate]:
        st = self._advocates.get(advocate_id)
        return st.spec if st else None

    def retainer(
        self, *, advocate_id: str, retainer_id: str,
    ) -> t.Optional[Retainer]:
        st = self._advocates.get(advocate_id)
        if st is None:
            return None
        return st.retainers.get(retainer_id)

    def win_rate(
        self, *, advocate_id: str,
    ) -> t.Optional[float]:
        st = self._advocates.get(advocate_id)
        if st is None:
            return None
        if st.spec.cases_taken == 0:
            return None
        return (
            st.spec.cases_won / st.spec.cases_taken
        )

    def find_by_specialty(
        self, *, specialty: str,
    ) -> list[Advocate]:
        return [
            st.spec for st in self._advocates.values()
            if st.spec.specialty == specialty
        ]


__all__ = [
    "RetainerState", "Advocate", "Retainer",
    "PlayerAdvocateRegistrySystem",
]
