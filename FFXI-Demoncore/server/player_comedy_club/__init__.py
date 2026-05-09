"""Player comedy club — write jokes, perform a set, watch them go stale.

Comedians write joke material organized into a set list. Each
joke has a topic and freshness (1..100). Performing a joke
decays its freshness by FRESHNESS_DECAY; jokes told too often
bomb. Crowd score combines comedian skill, set freshness, and
heckler resistance. Hecklers can derail a comedian below the
heckle_resistance threshold.

Lifecycle (per set)
    WRITTEN     joke list assembled
    BOOKED      slot reserved at a club
    PERFORMED   set delivered, score logged
    ARCHIVED    retired from the rotation

Public surface
--------------
    SetState enum
    Joke dataclass (frozen)
    Set dataclass (frozen)
    PerformanceLog dataclass (frozen)
    PlayerComedyClubSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_FRESHNESS_DECAY = 15
_HECKLE_PENALTY = 20


class SetState(str, enum.Enum):
    WRITTEN = "written"
    BOOKED = "booked"
    PERFORMED = "performed"
    ARCHIVED = "archived"


@dataclasses.dataclass(frozen=True)
class Joke:
    joke_id: str
    topic: str
    freshness: int  # 1..100, decays per perform


@dataclasses.dataclass(frozen=True)
class PerformanceLog:
    log_id: str
    set_id: str
    crowd_score: int
    bombed: bool
    performed_day: int


@dataclasses.dataclass(frozen=True)
class Set:
    set_id: str
    comedian_id: str
    comedian_skill: int      # 1..100
    heckle_resistance: int   # 1..100
    state: SetState
    booked_club_id: str
    last_log: t.Optional[PerformanceLog]


@dataclasses.dataclass
class _SState:
    spec: Set
    jokes: dict[str, Joke] = dataclasses.field(
        default_factory=dict,
    )
    joke_order: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class PlayerComedyClubSystem:
    _sets: dict[str, _SState] = dataclasses.field(
        default_factory=dict,
    )
    _next_set: int = 1
    _next_joke: int = 1
    _next_log: int = 1

    def write_set(
        self, *, comedian_id: str, comedian_skill: int,
        heckle_resistance: int,
    ) -> t.Optional[str]:
        if not comedian_id:
            return None
        if not 1 <= comedian_skill <= 100:
            return None
        if not 1 <= heckle_resistance <= 100:
            return None
        sid = f"set_{self._next_set}"
        self._next_set += 1
        spec = Set(
            set_id=sid, comedian_id=comedian_id,
            comedian_skill=comedian_skill,
            heckle_resistance=heckle_resistance,
            state=SetState.WRITTEN, booked_club_id="",
            last_log=None,
        )
        self._sets[sid] = _SState(spec=spec)
        return sid

    def add_joke(
        self, *, set_id: str, topic: str,
        freshness: int = 100,
    ) -> t.Optional[str]:
        if set_id not in self._sets:
            return None
        st = self._sets[set_id]
        if st.spec.state != SetState.WRITTEN:
            return None
        if not topic:
            return None
        if not 1 <= freshness <= 100:
            return None
        jid = f"joke_{self._next_joke}"
        self._next_joke += 1
        st.jokes[jid] = Joke(
            joke_id=jid, topic=topic,
            freshness=freshness,
        )
        st.joke_order.append(jid)
        return jid

    def book_club(
        self, *, set_id: str, club_id: str,
    ) -> bool:
        if set_id not in self._sets:
            return False
        st = self._sets[set_id]
        if st.spec.state != SetState.WRITTEN:
            return False
        if not st.joke_order:
            return False
        if not club_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=SetState.BOOKED,
            booked_club_id=club_id,
        )
        return True

    def perform_set(
        self, *, set_id: str, audience_heckle: int,
        performed_day: int,
    ) -> t.Optional[int]:
        """Delivers the set. Returns crowd_score.

        Each joke contributes (skill + freshness) // 4
        to crowd_score. Heckler pressure subtracts the
        excess over heckle_resistance, scaled. Below
        zero score = bombed. Each joke decays.
        """
        if set_id not in self._sets:
            return None
        st = self._sets[set_id]
        if st.spec.state != SetState.BOOKED:
            return None
        if audience_heckle < 0 or performed_day < 0:
            return None
        skill = st.spec.comedian_skill
        score = 0
        new_jokes: dict[str, Joke] = {}
        for jid in st.joke_order:
            j = st.jokes[jid]
            score += (skill + j.freshness) // 4
            new_freshness = max(
                1, j.freshness - _FRESHNESS_DECAY,
            )
            new_jokes[jid] = dataclasses.replace(
                j, freshness=new_freshness,
            )
        # Heckler pressure
        if audience_heckle > st.spec.heckle_resistance:
            penalty = (
                (
                    audience_heckle
                    - st.spec.heckle_resistance
                )
                * _HECKLE_PENALTY // 10
            )
            score -= penalty
        bombed = score < 0
        log_id = f"log_{self._next_log}"
        self._next_log += 1
        log = PerformanceLog(
            log_id=log_id, set_id=set_id,
            crowd_score=score, bombed=bombed,
            performed_day=performed_day,
        )
        st.jokes = new_jokes
        st.spec = dataclasses.replace(
            st.spec, state=SetState.PERFORMED,
            last_log=log,
        )
        return score

    def archive_set(self, *, set_id: str) -> bool:
        if set_id not in self._sets:
            return False
        st = self._sets[set_id]
        if st.spec.state != SetState.PERFORMED:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=SetState.ARCHIVED,
        )
        return True

    def re_book(
        self, *, set_id: str, club_id: str,
    ) -> bool:
        """Re-book a previously performed set.
        Allows refresh-without-archiving. Resets
        state to BOOKED so jokes can be told again
        (but they'll be staler now).
        """
        if set_id not in self._sets:
            return False
        st = self._sets[set_id]
        if st.spec.state != SetState.PERFORMED:
            return False
        if not club_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=SetState.BOOKED,
            booked_club_id=club_id,
        )
        return True

    def set(
        self, *, set_id: str,
    ) -> t.Optional[Set]:
        st = self._sets.get(set_id)
        return st.spec if st else None

    def jokes(
        self, *, set_id: str,
    ) -> list[Joke]:
        st = self._sets.get(set_id)
        if st is None:
            return []
        return [st.jokes[j] for j in st.joke_order]


__all__ = [
    "SetState", "Joke", "PerformanceLog", "Set",
    "PlayerComedyClubSystem",
]
