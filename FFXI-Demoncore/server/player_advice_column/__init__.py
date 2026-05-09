"""Player advice column — anonymous letters and rated answers.

A columnist runs an advice column. Players write in with
problems, optionally anonymously. The columnist publishes
an answer or declines the letter. Readers (other players,
not the writer or columnist) rate the answer 1..5 stars.
The running average rating is the columnist's public
craft score for advice — bad columnists become known as
bad, good ones become trusted.

Lifecycle (letter)
    AWAITING       letter submitted, awaiting columnist
    ANSWERED       columnist published response, ratable
    DECLINED       columnist passed

Public surface
--------------
    LetterState enum
    AdviceColumn dataclass (frozen)
    Letter dataclass (frozen)
    PlayerAdviceColumnSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_STARS = 1
_MAX_STARS = 5


class LetterState(str, enum.Enum):
    AWAITING = "awaiting"
    ANSWERED = "answered"
    DECLINED = "declined"


@dataclasses.dataclass(frozen=True)
class AdviceColumn:
    column_id: str
    columnist_id: str
    name: str


@dataclasses.dataclass(frozen=True)
class Letter:
    letter_id: str
    column_id: str
    writer_id: str
    anonymous: bool
    problem: str
    response: str
    state: LetterState
    average_stars: float
    rating_count: int


@dataclasses.dataclass
class _LState:
    spec: Letter
    ratings: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class _CState:
    spec: AdviceColumn
    letters: dict[str, _LState] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerAdviceColumnSystem:
    _columns: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next_column: int = 1
    _next_letter: int = 1

    def start_column(
        self, *, columnist_id: str, name: str,
    ) -> t.Optional[str]:
        if not columnist_id or not name:
            return None
        cid = f"col_{self._next_column}"
        self._next_column += 1
        self._columns[cid] = _CState(
            spec=AdviceColumn(
                column_id=cid,
                columnist_id=columnist_id,
                name=name,
            ),
        )
        return cid

    def submit_letter(
        self, *, column_id: str, writer_id: str,
        problem: str, anonymous: bool = True,
    ) -> t.Optional[str]:
        if column_id not in self._columns:
            return None
        st = self._columns[column_id]
        if not writer_id or not problem:
            return None
        if writer_id == st.spec.columnist_id:
            return None
        lid = f"letter_{self._next_letter}"
        self._next_letter += 1
        st.letters[lid] = _LState(
            spec=Letter(
                letter_id=lid, column_id=column_id,
                writer_id=writer_id,
                anonymous=anonymous,
                problem=problem, response="",
                state=LetterState.AWAITING,
                average_stars=0.0,
                rating_count=0,
            ),
        )
        return lid

    def answer_letter(
        self, *, column_id: str, letter_id: str,
        columnist_id: str, response: str,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if st.spec.columnist_id != columnist_id:
            return False
        if letter_id not in st.letters:
            return False
        ls = st.letters[letter_id]
        if ls.spec.state != LetterState.AWAITING:
            return False
        if not response:
            return False
        ls.spec = dataclasses.replace(
            ls.spec, state=LetterState.ANSWERED,
            response=response,
        )
        return True

    def decline_letter(
        self, *, column_id: str, letter_id: str,
        columnist_id: str,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if st.spec.columnist_id != columnist_id:
            return False
        if letter_id not in st.letters:
            return False
        ls = st.letters[letter_id]
        if ls.spec.state != LetterState.AWAITING:
            return False
        ls.spec = dataclasses.replace(
            ls.spec, state=LetterState.DECLINED,
        )
        return True

    def rate_response(
        self, *, column_id: str, letter_id: str,
        reader_id: str, stars: int,
    ) -> bool:
        if column_id not in self._columns:
            return False
        st = self._columns[column_id]
        if letter_id not in st.letters:
            return False
        ls = st.letters[letter_id]
        if ls.spec.state != LetterState.ANSWERED:
            return False
        if not reader_id:
            return False
        if reader_id == st.spec.columnist_id:
            return False
        if reader_id == ls.spec.writer_id:
            return False
        if not _MIN_STARS <= stars <= _MAX_STARS:
            return False
        if reader_id in ls.ratings:
            return False
        ls.ratings[reader_id] = stars
        avg = (
            sum(ls.ratings.values())
            / len(ls.ratings)
        )
        ls.spec = dataclasses.replace(
            ls.spec, average_stars=avg,
            rating_count=len(ls.ratings),
        )
        return True

    def column(
        self, *, column_id: str,
    ) -> t.Optional[AdviceColumn]:
        st = self._columns.get(column_id)
        return st.spec if st else None

    def letter(
        self, *, column_id: str, letter_id: str,
    ) -> t.Optional[Letter]:
        st = self._columns.get(column_id)
        if st is None:
            return None
        ls = st.letters.get(letter_id)
        return ls.spec if ls else None

    def public_view(
        self, *, column_id: str, letter_id: str,
    ) -> t.Optional[Letter]:
        """Public-facing view of a letter: anonymous
        letters mask the writer_id."""
        spec = self.letter(
            column_id=column_id, letter_id=letter_id,
        )
        if spec is None:
            return None
        if spec.anonymous:
            return dataclasses.replace(
                spec, writer_id="anonymous",
            )
        return spec

    def average_for_columnist(
        self, *, column_id: str,
    ) -> float:
        st = self._columns.get(column_id)
        if st is None:
            return 0.0
        ratings = []
        for ls in st.letters.values():
            if ls.spec.state == LetterState.ANSWERED:
                ratings.extend(ls.ratings.values())
        if not ratings:
            return 0.0
        return sum(ratings) / len(ratings)


__all__ = [
    "LetterState", "AdviceColumn", "Letter",
    "PlayerAdviceColumnSystem",
]
