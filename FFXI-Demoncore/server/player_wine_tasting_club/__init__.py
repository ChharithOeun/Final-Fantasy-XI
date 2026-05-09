"""Player wine tasting club — sommelier-led rating circle.

A sommelier founds a tasting club. Members pay annual dues
collected by the sommelier. Periodic tastings are hosted by
the sommelier; in each tasting, members score wines on a
0..100 palate scale. A wine's running average across all
tastings (weighted equally per scoring member) becomes its
public reputation. Best for sorting which Bordeaux from the
Quon airship pirates is actually drinkable.

Lifecycle (club)
    OPEN          accepting members and hosting tastings
    CLOSED        wound down

Public surface
--------------
    ClubState enum
    WineTastingClub dataclass (frozen)
    Tasting dataclass (frozen)
    PlayerWineTastingClubSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_SCORE = 0
_MAX_SCORE = 100


class ClubState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class WineTastingClub:
    club_id: str
    sommelier_id: str
    name: str
    annual_dues_gil: int
    state: ClubState
    dues_collected_gil: int


@dataclasses.dataclass(frozen=True)
class Tasting:
    tasting_id: str
    club_id: str
    held_day: int


@dataclasses.dataclass
class _TState:
    spec: Tasting
    # wine_label -> {member_id: score}
    scores: dict[str, dict[str, int]] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class _CState:
    spec: WineTastingClub
    members: set[str] = dataclasses.field(
        default_factory=set,
    )
    tastings: dict[str, _TState] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerWineTastingClubSystem:
    _clubs: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next_club: int = 1
    _next_tasting: int = 1

    def found_club(
        self, *, sommelier_id: str, name: str,
        annual_dues_gil: int,
    ) -> t.Optional[str]:
        if not sommelier_id or not name:
            return None
        if annual_dues_gil <= 0:
            return None
        cid = f"club_{self._next_club}"
        self._next_club += 1
        self._clubs[cid] = _CState(
            spec=WineTastingClub(
                club_id=cid,
                sommelier_id=sommelier_id,
                name=name,
                annual_dues_gil=annual_dues_gil,
                state=ClubState.OPEN,
                dues_collected_gil=0,
            ),
        )
        return cid

    def join(
        self, *, club_id: str, member_id: str,
    ) -> bool:
        if club_id not in self._clubs:
            return False
        st = self._clubs[club_id]
        if st.spec.state != ClubState.OPEN:
            return False
        if not member_id:
            return False
        if member_id == st.spec.sommelier_id:
            return False
        if member_id in st.members:
            return False
        st.members.add(member_id)
        st.spec = dataclasses.replace(
            st.spec,
            dues_collected_gil=(
                st.spec.dues_collected_gil
                + st.spec.annual_dues_gil
            ),
        )
        return True

    def host_tasting(
        self, *, club_id: str, sommelier_id: str,
        held_day: int,
    ) -> t.Optional[str]:
        if club_id not in self._clubs:
            return None
        st = self._clubs[club_id]
        if st.spec.state != ClubState.OPEN:
            return None
        if st.spec.sommelier_id != sommelier_id:
            return None
        if held_day < 0:
            return None
        tid = f"tast_{self._next_tasting}"
        self._next_tasting += 1
        st.tastings[tid] = _TState(
            spec=Tasting(
                tasting_id=tid, club_id=club_id,
                held_day=held_day,
            ),
        )
        return tid

    def score_wine(
        self, *, club_id: str, tasting_id: str,
        member_id: str, wine_label: str, score: int,
    ) -> bool:
        if club_id not in self._clubs:
            return False
        st = self._clubs[club_id]
        if member_id not in st.members:
            return False
        if tasting_id not in st.tastings:
            return False
        if not wine_label:
            return False
        if not _MIN_SCORE <= score <= _MAX_SCORE:
            return False
        ts = st.tastings[tasting_id]
        wine_scores = ts.scores.setdefault(
            wine_label, {},
        )
        if member_id in wine_scores:
            return False
        wine_scores[member_id] = score
        return True

    def wine_average(
        self, *, club_id: str, wine_label: str,
    ) -> t.Optional[float]:
        if club_id not in self._clubs:
            return None
        st = self._clubs[club_id]
        all_scores: list[int] = []
        for ts in st.tastings.values():
            ws = ts.scores.get(wine_label)
            if ws:
                all_scores.extend(ws.values())
        if not all_scores:
            return None
        return sum(all_scores) / len(all_scores)

    def wine_ranking(
        self, *, club_id: str,
    ) -> list[tuple[str, float]]:
        """Returns wines sorted by avg score
        descending."""
        if club_id not in self._clubs:
            return []
        st = self._clubs[club_id]
        labels: set[str] = set()
        for ts in st.tastings.values():
            labels.update(ts.scores.keys())
        ranked = []
        for label in labels:
            avg = self.wine_average(
                club_id=club_id, wine_label=label,
            )
            if avg is not None:
                ranked.append((label, avg))
        ranked.sort(key=lambda p: -p[1])
        return ranked

    def close_club(
        self, *, club_id: str, sommelier_id: str,
    ) -> bool:
        if club_id not in self._clubs:
            return False
        st = self._clubs[club_id]
        if st.spec.state != ClubState.OPEN:
            return False
        if st.spec.sommelier_id != sommelier_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ClubState.CLOSED,
        )
        return True

    def club(
        self, *, club_id: str,
    ) -> t.Optional[WineTastingClub]:
        st = self._clubs.get(club_id)
        return st.spec if st else None

    def members(
        self, *, club_id: str,
    ) -> list[str]:
        st = self._clubs.get(club_id)
        if st is None:
            return []
        return sorted(st.members)


__all__ = [
    "ClubState", "WineTastingClub", "Tasting",
    "PlayerWineTastingClubSystem",
]
