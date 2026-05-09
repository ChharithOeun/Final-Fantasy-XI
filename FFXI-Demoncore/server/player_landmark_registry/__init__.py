"""Player landmark registry — named places at known coordinates.

Players survey zones and register landmarks (waystones,
sacred trees, hidden cave entrances, killed-NM sites).
Each landmark has a name, kind, zone, and (x, y) coords.
Other players can confirm a landmark (independent witness)
or dispute it (saw something different). A landmark with
3+ confirmations becomes VERIFIED; with 3+ disputes it
becomes DISPUTED. Disputes can be cleared by the original
discoverer revisiting and re-registering with current coords.

Lifecycle (landmark)
    UNVERIFIED   freshly registered, awaiting witnesses
    VERIFIED     3+ independent confirmations
    DISPUTED     3+ disputes outweigh confirmations

Public surface
--------------
    LandmarkState enum
    LandmarkKind enum
    Landmark dataclass (frozen)
    PlayerLandmarkRegistrySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_VERIFY_THRESHOLD = 3


class LandmarkState(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class LandmarkKind(str, enum.Enum):
    WAYSTONE = "waystone"
    SHRINE = "shrine"
    CAVE_ENTRANCE = "cave_entrance"
    NM_SITE = "nm_site"
    LANDMARK_TREE = "landmark_tree"
    BRIDGE = "bridge"
    RUIN = "ruin"


@dataclasses.dataclass(frozen=True)
class Landmark:
    landmark_id: str
    discoverer_id: str
    zone: str
    name: str
    kind: LandmarkKind
    x: int
    y: int
    state: LandmarkState
    confirmations: int
    disputes: int


@dataclasses.dataclass
class _LState:
    spec: Landmark
    confirmers: set[str] = dataclasses.field(
        default_factory=set,
    )
    disputers: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerLandmarkRegistrySystem:
    _landmarks: dict[str, _LState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register(
        self, *, discoverer_id: str, zone: str,
        name: str, kind: LandmarkKind,
        x: int, y: int,
    ) -> t.Optional[str]:
        if not discoverer_id or not zone or not name:
            return None
        lid = f"land_{self._next}"
        self._next += 1
        self._landmarks[lid] = _LState(
            spec=Landmark(
                landmark_id=lid,
                discoverer_id=discoverer_id,
                zone=zone, name=name, kind=kind,
                x=x, y=y,
                state=LandmarkState.UNVERIFIED,
                confirmations=0, disputes=0,
            ),
        )
        return lid

    def confirm(
        self, *, landmark_id: str, witness_id: str,
    ) -> bool:
        if landmark_id not in self._landmarks:
            return False
        st = self._landmarks[landmark_id]
        if not witness_id:
            return False
        if witness_id == st.spec.discoverer_id:
            return False
        if witness_id in st.confirmers:
            return False
        if witness_id in st.disputers:
            return False
        st.confirmers.add(witness_id)
        self._update_state(st)
        return True

    def dispute(
        self, *, landmark_id: str, witness_id: str,
    ) -> bool:
        if landmark_id not in self._landmarks:
            return False
        st = self._landmarks[landmark_id]
        if not witness_id:
            return False
        if witness_id == st.spec.discoverer_id:
            return False
        if witness_id in st.confirmers:
            return False
        if witness_id in st.disputers:
            return False
        st.disputers.add(witness_id)
        self._update_state(st)
        return True

    @staticmethod
    def _update_state(st: _LState) -> None:
        c = len(st.confirmers)
        d = len(st.disputers)
        if d >= _VERIFY_THRESHOLD and d > c:
            new_state = LandmarkState.DISPUTED
        elif c >= _VERIFY_THRESHOLD and c > d:
            new_state = LandmarkState.VERIFIED
        else:
            new_state = LandmarkState.UNVERIFIED
        st.spec = dataclasses.replace(
            st.spec, state=new_state,
            confirmations=c, disputes=d,
        )

    def re_register(
        self, *, landmark_id: str,
        discoverer_id: str, x: int, y: int,
    ) -> bool:
        """Discoverer revisits and re-pegs coordinates;
        clears disputes only (confirmations preserved)
        and resets state to UNVERIFIED."""
        if landmark_id not in self._landmarks:
            return False
        st = self._landmarks[landmark_id]
        if st.spec.discoverer_id != discoverer_id:
            return False
        if st.spec.state != LandmarkState.DISPUTED:
            return False
        st.disputers.clear()
        st.spec = dataclasses.replace(
            st.spec, x=x, y=y,
            state=LandmarkState.UNVERIFIED,
            disputes=0,
        )
        self._update_state(st)
        return True

    def landmark(
        self, *, landmark_id: str,
    ) -> t.Optional[Landmark]:
        st = self._landmarks.get(landmark_id)
        return st.spec if st else None

    def landmarks_in_zone(
        self, *, zone: str,
    ) -> list[Landmark]:
        return [
            st.spec for st in self._landmarks.values()
            if st.spec.zone == zone
        ]

    def verified_in_zone(
        self, *, zone: str,
    ) -> list[Landmark]:
        return [
            st.spec for st in self._landmarks.values()
            if (
                st.spec.zone == zone
                and st.spec.state == LandmarkState.VERIFIED
            )
        ]


__all__ = [
    "LandmarkState", "LandmarkKind", "Landmark",
    "PlayerLandmarkRegistrySystem",
]
