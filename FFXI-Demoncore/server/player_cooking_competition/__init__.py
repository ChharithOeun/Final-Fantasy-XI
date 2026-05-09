"""Player cooking competition — judged dish-off with prize purse.

Run by an organizer who deposits a prize purse. Contestants
register and present a dish; judges score each dish 0..10.
On resolve, contestant scores are totaled across judges and
ranked. The purse splits 60/30/10 between gold/silver/bronze.

Lifecycle
    REGISTRATION    accepting contestants and judges
    JUDGING         registration closed, judges scoring
    CONCLUDED       resolved; rankings and purse paid

Public surface
--------------
    CompState enum
    Competition dataclass (frozen)
    Contestant dataclass (frozen)
    PlayerCookingCompetitionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_CONTESTANTS = 2
_MAX_JUDGES = 5
_MIN_SCORE = 0
_MAX_SCORE = 10
# Purse split: 1st 60%, 2nd 30%, 3rd 10%
_GOLD_PCT = 60
_SILVER_PCT = 30
_BRONZE_PCT = 10


class CompState(str, enum.Enum):
    REGISTRATION = "registration"
    JUDGING = "judging"
    CONCLUDED = "concluded"


@dataclasses.dataclass(frozen=True)
class Competition:
    competition_id: str
    organizer_id: str
    name: str
    purse_gil: int
    state: CompState
    winner_id: str
    runner_up_id: str
    third_place_id: str


@dataclasses.dataclass(frozen=True)
class Contestant:
    contestant_id: str
    dish_name: str
    total_score: int


@dataclasses.dataclass
class _CState:
    spec: Competition
    judges: list[str] = dataclasses.field(
        default_factory=list,
    )
    contestants: dict[str, Contestant] = (
        dataclasses.field(default_factory=dict)
    )
    # (contestant_id, judge_id) -> score
    scores: dict[tuple[str, str], int] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerCookingCompetitionSystem:
    _comps: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def announce(
        self, *, organizer_id: str, name: str,
        purse_gil: int,
    ) -> t.Optional[str]:
        if not organizer_id or not name:
            return None
        if purse_gil <= 0:
            return None
        cid = f"comp_{self._next}"
        self._next += 1
        self._comps[cid] = _CState(
            spec=Competition(
                competition_id=cid,
                organizer_id=organizer_id, name=name,
                purse_gil=purse_gil,
                state=CompState.REGISTRATION,
                winner_id="", runner_up_id="",
                third_place_id="",
            ),
        )
        return cid

    def add_judge(
        self, *, competition_id: str, judge_id: str,
    ) -> bool:
        if competition_id not in self._comps:
            return False
        st = self._comps[competition_id]
        if st.spec.state != CompState.REGISTRATION:
            return False
        if not judge_id:
            return False
        if judge_id == st.spec.organizer_id:
            return False
        if judge_id in st.judges:
            return False
        if judge_id in st.contestants:
            return False
        if len(st.judges) >= _MAX_JUDGES:
            return False
        st.judges.append(judge_id)
        return True

    def enter_contestant(
        self, *, competition_id: str,
        contestant_id: str, dish_name: str,
    ) -> bool:
        if competition_id not in self._comps:
            return False
        st = self._comps[competition_id]
        if st.spec.state != CompState.REGISTRATION:
            return False
        if not contestant_id or not dish_name:
            return False
        if contestant_id == st.spec.organizer_id:
            return False
        if contestant_id in st.judges:
            return False
        if contestant_id in st.contestants:
            return False
        st.contestants[contestant_id] = Contestant(
            contestant_id=contestant_id,
            dish_name=dish_name, total_score=0,
        )
        return True

    def begin_judging(
        self, *, competition_id: str,
        organizer_id: str,
    ) -> bool:
        if competition_id not in self._comps:
            return False
        st = self._comps[competition_id]
        if st.spec.state != CompState.REGISTRATION:
            return False
        if st.spec.organizer_id != organizer_id:
            return False
        if len(st.contestants) < _MIN_CONTESTANTS:
            return False
        if not st.judges:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=CompState.JUDGING,
        )
        return True

    def submit_score(
        self, *, competition_id: str, judge_id: str,
        contestant_id: str, score: int,
    ) -> bool:
        if competition_id not in self._comps:
            return False
        st = self._comps[competition_id]
        if st.spec.state != CompState.JUDGING:
            return False
        if judge_id not in st.judges:
            return False
        if contestant_id not in st.contestants:
            return False
        if not _MIN_SCORE <= score <= _MAX_SCORE:
            return False
        key = (contestant_id, judge_id)
        if key in st.scores:
            return False
        st.scores[key] = score
        c = st.contestants[contestant_id]
        st.contestants[contestant_id] = (
            dataclasses.replace(
                c, total_score=c.total_score + score,
            )
        )
        return True

    def resolve(
        self, *, competition_id: str,
        organizer_id: str,
    ) -> t.Optional[dict[str, int]]:
        """Returns {contestant_id: prize_gil} for
        the top placings. None if not ready."""
        if competition_id not in self._comps:
            return None
        st = self._comps[competition_id]
        if st.spec.state != CompState.JUDGING:
            return None
        if st.spec.organizer_id != organizer_id:
            return None
        # Every judge must have scored every contestant
        expected = (
            len(st.judges) * len(st.contestants)
        )
        if len(st.scores) != expected:
            return None
        ranked = sorted(
            st.contestants.values(),
            key=lambda c: -c.total_score,
        )
        purse = st.spec.purse_gil
        payouts: dict[str, int] = {}
        winner = ranked[0].contestant_id
        payouts[winner] = purse * _GOLD_PCT // 100
        runner = ""
        third = ""
        if len(ranked) >= 2:
            runner = ranked[1].contestant_id
            payouts[runner] = (
                purse * _SILVER_PCT // 100
            )
        if len(ranked) >= 3:
            third = ranked[2].contestant_id
            payouts[third] = (
                purse * _BRONZE_PCT // 100
            )
        st.spec = dataclasses.replace(
            st.spec, state=CompState.CONCLUDED,
            winner_id=winner, runner_up_id=runner,
            third_place_id=third,
        )
        return payouts

    def competition(
        self, *, competition_id: str,
    ) -> t.Optional[Competition]:
        st = self._comps.get(competition_id)
        return st.spec if st else None

    def contestants(
        self, *, competition_id: str,
    ) -> list[Contestant]:
        st = self._comps.get(competition_id)
        if st is None:
            return []
        return list(st.contestants.values())

    def judges(
        self, *, competition_id: str,
    ) -> list[str]:
        st = self._comps.get(competition_id)
        if st is None:
            return []
        return list(st.judges)


__all__ = [
    "CompState", "Competition", "Contestant",
    "PlayerCookingCompetitionSystem",
]
