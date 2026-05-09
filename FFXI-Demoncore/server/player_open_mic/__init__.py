"""Player open mic — sign-up improv venue.

Players sign up for an open mic night, perform short pieces
(STORY / POEM / SONG / JOKE / RANT), and the audience tips
proportional to performance quality. Tips are deterministic
from performer_skill + piece_type modifier + variance.

Lifecycle (per night)
    SIGNUP_OPEN   anyone can add a slot
    PERFORMING    slots running in order, tips paid
    ENDED         night closed, no further changes

Public surface
--------------
    NightState enum
    PieceType enum
    Slot dataclass (frozen)
    Night dataclass (frozen)
    PlayerOpenMicSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_PIECE_BONUS = {
    "story": 5,
    "poem": 0,
    "song": 10,
    "joke": -5,
    "rant": -10,
}


class NightState(str, enum.Enum):
    SIGNUP_OPEN = "signup_open"
    PERFORMING = "performing"
    ENDED = "ended"


class PieceType(str, enum.Enum):
    STORY = "story"
    POEM = "poem"
    SONG = "song"
    JOKE = "joke"
    RANT = "rant"


@dataclasses.dataclass(frozen=True)
class Slot:
    slot_id: str
    night_id: str
    performer_id: str
    performer_skill: int
    piece_type: PieceType
    duration_minutes: int
    performed: bool
    tips_gil: int


@dataclasses.dataclass(frozen=True)
class Night:
    night_id: str
    venue_id: str
    audience_size: int
    state: NightState
    next_slot_index: int


@dataclasses.dataclass
class _NState:
    spec: Night
    slots: dict[str, Slot] = dataclasses.field(
        default_factory=dict,
    )
    order: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class PlayerOpenMicSystem:
    _nights: dict[str, _NState] = dataclasses.field(
        default_factory=dict,
    )
    _next_night: int = 1
    _next_slot: int = 1

    def open_night(
        self, *, venue_id: str, audience_size: int,
    ) -> t.Optional[str]:
        if not venue_id:
            return None
        if audience_size < 0:
            return None
        nid = f"night_{self._next_night}"
        self._next_night += 1
        spec = Night(
            night_id=nid, venue_id=venue_id,
            audience_size=audience_size,
            state=NightState.SIGNUP_OPEN,
            next_slot_index=0,
        )
        self._nights[nid] = _NState(spec=spec)
        return nid

    def signup(
        self, *, night_id: str, performer_id: str,
        performer_skill: int, piece_type: PieceType,
        duration_minutes: int,
    ) -> t.Optional[str]:
        if night_id not in self._nights:
            return None
        st = self._nights[night_id]
        if st.spec.state != NightState.SIGNUP_OPEN:
            return None
        if not performer_id:
            return None
        if not 1 <= performer_skill <= 100:
            return None
        if duration_minutes < 1 or duration_minutes > 30:
            return None
        # One sign-up per performer per night
        for s in st.slots.values():
            if s.performer_id == performer_id:
                return None
        sid = f"slot_{self._next_slot}"
        self._next_slot += 1
        st.slots[sid] = Slot(
            slot_id=sid, night_id=night_id,
            performer_id=performer_id,
            performer_skill=performer_skill,
            piece_type=piece_type,
            duration_minutes=duration_minutes,
            performed=False, tips_gil=0,
        )
        st.order.append(sid)
        return sid

    def begin(self, *, night_id: str) -> bool:
        if night_id not in self._nights:
            return False
        st = self._nights[night_id]
        if st.spec.state != NightState.SIGNUP_OPEN:
            return False
        if not st.order:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=NightState.PERFORMING,
        )
        return True

    def perform_next(
        self, *, night_id: str, seed: int,
    ) -> t.Optional[int]:
        """Run the next slot in line. Returns tips
        paid in gil. Score = skill + piece bonus +
        variance(-5..+5). Tips = audience_size * score
        // 100, floored at 0.
        """
        if night_id not in self._nights:
            return None
        st = self._nights[night_id]
        if st.spec.state != NightState.PERFORMING:
            return None
        idx = st.spec.next_slot_index
        if idx >= len(st.order):
            return None
        sid = st.order[idx]
        slot = st.slots[sid]
        bonus = _PIECE_BONUS[slot.piece_type.value]
        variance = (seed % 11) - 5  # -5..+5
        score = slot.performer_skill + bonus + variance
        score = max(0, score)
        tips = st.spec.audience_size * score // 100
        st.slots[sid] = dataclasses.replace(
            slot, performed=True, tips_gil=tips,
        )
        st.spec = dataclasses.replace(
            st.spec, next_slot_index=idx + 1,
        )
        return tips

    def end_night(self, *, night_id: str) -> bool:
        if night_id not in self._nights:
            return False
        st = self._nights[night_id]
        if st.spec.state != NightState.PERFORMING:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=NightState.ENDED,
        )
        return True

    def night(
        self, *, night_id: str,
    ) -> t.Optional[Night]:
        st = self._nights.get(night_id)
        return st.spec if st else None

    def slots(
        self, *, night_id: str,
    ) -> list[Slot]:
        st = self._nights.get(night_id)
        if st is None:
            return []
        return [st.slots[sid] for sid in st.order]

    def performer_tips(
        self, *, night_id: str, performer_id: str,
    ) -> int:
        st = self._nights.get(night_id)
        if st is None:
            return 0
        for slot in st.slots.values():
            if slot.performer_id == performer_id:
                return slot.tips_gil
        return 0


__all__ = [
    "NightState", "PieceType", "Slot", "Night",
    "PlayerOpenMicSystem",
]
