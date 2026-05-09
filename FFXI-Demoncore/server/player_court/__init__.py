"""Player court — judicial body with named jurisdiction.

A chief justice founds a court with a stated jurisdiction
(set of crime kinds it has authority to hear). They enroll
associate justices to share the bench. Lawsuits filed
against defendants must specify a kind that falls within
the court's jurisdiction. Disbanding the court ends its
authority but preserves the historical record.

Lifecycle
    ACTIVE       hearing cases
    DISBANDED    no longer hearing

Public surface
--------------
    CourtState enum
    Court dataclass (frozen)
    PlayerCourtSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CourtState(str, enum.Enum):
    ACTIVE = "active"
    DISBANDED = "disbanded"


@dataclasses.dataclass(frozen=True)
class Court:
    court_id: str
    chief_justice_id: str
    name: str
    state: CourtState


@dataclasses.dataclass
class _CState:
    spec: Court
    jurisdiction: set[str] = dataclasses.field(
        default_factory=set,
    )
    associates: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerCourtSystem:
    _courts: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def found_court(
        self, *, chief_justice_id: str, name: str,
        jurisdiction: list[str],
    ) -> t.Optional[str]:
        if not chief_justice_id or not name:
            return None
        if not jurisdiction:
            return None
        cid = f"court_{self._next}"
        self._next += 1
        st = _CState(
            spec=Court(
                court_id=cid,
                chief_justice_id=chief_justice_id,
                name=name, state=CourtState.ACTIVE,
            ),
        )
        st.jurisdiction = set(jurisdiction)
        self._courts[cid] = st
        return cid

    def enroll_associate(
        self, *, court_id: str,
        chief_justice_id: str, justice_id: str,
    ) -> bool:
        if court_id not in self._courts:
            return False
        st = self._courts[court_id]
        if st.spec.state != CourtState.ACTIVE:
            return False
        if (
            st.spec.chief_justice_id
            != chief_justice_id
        ):
            return False
        if not justice_id:
            return False
        if justice_id == st.spec.chief_justice_id:
            return False
        if justice_id in st.associates:
            return False
        st.associates.add(justice_id)
        return True

    def has_jurisdiction(
        self, *, court_id: str, kind: str,
    ) -> bool:
        st = self._courts.get(court_id)
        if st is None:
            return False
        if st.spec.state != CourtState.ACTIVE:
            return False
        return kind in st.jurisdiction

    def is_justice(
        self, *, court_id: str, person_id: str,
    ) -> bool:
        st = self._courts.get(court_id)
        if st is None:
            return False
        if st.spec.chief_justice_id == person_id:
            return True
        return person_id in st.associates

    def disband(
        self, *, court_id: str,
        chief_justice_id: str,
    ) -> bool:
        if court_id not in self._courts:
            return False
        st = self._courts[court_id]
        if st.spec.state != CourtState.ACTIVE:
            return False
        if (
            st.spec.chief_justice_id
            != chief_justice_id
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, state=CourtState.DISBANDED,
        )
        return True

    def court(
        self, *, court_id: str,
    ) -> t.Optional[Court]:
        st = self._courts.get(court_id)
        return st.spec if st else None

    def jurisdiction(
        self, *, court_id: str,
    ) -> list[str]:
        st = self._courts.get(court_id)
        if st is None:
            return []
        return sorted(st.jurisdiction)

    def justices(
        self, *, court_id: str,
    ) -> list[str]:
        st = self._courts.get(court_id)
        if st is None:
            return []
        return sorted(
            {st.spec.chief_justice_id} | st.associates
        )


__all__ = [
    "CourtState", "Court", "PlayerCourtSystem",
]
