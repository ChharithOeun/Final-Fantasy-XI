"""City library — public reading rooms with collections.

Each capital city operates a LIBRARY: a building stocked
with BOOKS players can borrow, read in-place, or
research from. Reading certain books grants temporary
RESEARCH_BONUS buffs (skill xp boost, magic accuracy,
crafting hint quality). Some rare books are reference-
only (cannot leave the library); others can be loaned
out for a fixed lend_days window. Overdue borrowers
incur a fine and lose Honor (delegated to the caller).

A LibraryBook has:
    book_id
    library_id
    title
    category (HISTORY / MAGIC / COMBAT / CRAFTING /
              GEOGRAPHY / RELIGION / BESTIARY /
              FORBIDDEN)
    is_reference_only
    base_lend_days
    research_bonus_kind (str — caller routes effect)
    research_bonus_value
    available_copies

Public surface
--------------
    BookCategory enum
    LibraryBook dataclass (frozen)
    LoanRecord dataclass (frozen)
    CityLibrarySystem
        .open_library(library_id, city) -> bool
        .add_book(library_id, book) -> bool
        .borrow(library_id, book_id, player_id,
                day) -> Optional[str]
        .return_book(loan_id, day) -> tuple[bool,
                int]   # (ok, days_overdue)
        .read_in_place(library_id, book_id,
                       player_id) -> Optional[
                       tuple[str, int]]
        .books(library_id) -> list[LibraryBook]
        .loans_for(player_id) -> list[LoanRecord]
        .overdue_loans(now_day) -> list[LoanRecord]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BookCategory(str, enum.Enum):
    HISTORY = "history"
    MAGIC = "magic"
    COMBAT = "combat"
    CRAFTING = "crafting"
    GEOGRAPHY = "geography"
    RELIGION = "religion"
    BESTIARY = "bestiary"
    FORBIDDEN = "forbidden"


@dataclasses.dataclass(frozen=True)
class LibraryBook:
    book_id: str
    library_id: str
    title: str
    category: BookCategory
    is_reference_only: bool
    base_lend_days: int
    research_bonus_kind: str
    research_bonus_value: int
    available_copies: int


@dataclasses.dataclass(frozen=True)
class LoanRecord:
    loan_id: str
    library_id: str
    book_id: str
    player_id: str
    borrowed_day: int
    due_day: int
    returned_day: t.Optional[int]


@dataclasses.dataclass
class _LibState:
    library_id: str
    city: str
    books: dict[str, LibraryBook] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class CityLibrarySystem:
    _libs: dict[str, _LibState] = dataclasses.field(
        default_factory=dict,
    )
    _loans: dict[str, LoanRecord] = dataclasses.field(
        default_factory=dict,
    )
    _next_loan: int = 1

    def open_library(
        self, *, library_id: str, city: str,
    ) -> bool:
        if not library_id or not city:
            return False
        if library_id in self._libs:
            return False
        self._libs[library_id] = _LibState(
            library_id=library_id, city=city,
        )
        return True

    def add_book(
        self, *, library_id: str, book: LibraryBook,
    ) -> bool:
        if library_id not in self._libs:
            return False
        if book.library_id != library_id:
            return False
        if not book.book_id or not book.title:
            return False
        if book.available_copies < 0:
            return False
        if book.base_lend_days < 0:
            return False
        st = self._libs[library_id]
        if book.book_id in st.books:
            return False
        st.books[book.book_id] = book
        return True

    def borrow(
        self, *, library_id: str, book_id: str,
        player_id: str, day: int,
    ) -> t.Optional[str]:
        if library_id not in self._libs:
            return None
        if not player_id or day < 0:
            return None
        st = self._libs[library_id]
        if book_id not in st.books:
            return None
        book = st.books[book_id]
        if book.is_reference_only:
            return None
        if book.available_copies <= 0:
            return None
        loan_id = f"loan_{self._next_loan}"
        self._next_loan += 1
        self._loans[loan_id] = LoanRecord(
            loan_id=loan_id, library_id=library_id,
            book_id=book_id, player_id=player_id,
            borrowed_day=day,
            due_day=day + book.base_lend_days,
            returned_day=None,
        )
        st.books[book_id] = dataclasses.replace(
            book,
            available_copies=book.available_copies - 1,
        )
        return loan_id

    def return_book(
        self, *, loan_id: str, day: int,
    ) -> tuple[bool, int]:
        if loan_id not in self._loans:
            return (False, 0)
        loan = self._loans[loan_id]
        if loan.returned_day is not None:
            return (False, 0)
        if day < loan.borrowed_day:
            return (False, 0)
        st = self._libs[loan.library_id]
        book = st.books[loan.book_id]
        st.books[loan.book_id] = dataclasses.replace(
            book,
            available_copies=book.available_copies + 1,
        )
        self._loans[loan_id] = dataclasses.replace(
            loan, returned_day=day,
        )
        days_overdue = max(0, day - loan.due_day)
        return (True, days_overdue)

    def read_in_place(
        self, *, library_id: str, book_id: str,
        player_id: str,
    ) -> t.Optional[tuple[str, int]]:
        if library_id not in self._libs:
            return None
        if not player_id:
            return None
        st = self._libs[library_id]
        if book_id not in st.books:
            return None
        book = st.books[book_id]
        # Reading in place doesn't decrement copies
        return (
            book.research_bonus_kind,
            book.research_bonus_value,
        )

    def books(
        self, *, library_id: str,
    ) -> list[LibraryBook]:
        if library_id not in self._libs:
            return []
        return list(
            self._libs[library_id].books.values(),
        )

    def loans_for(
        self, *, player_id: str,
    ) -> list[LoanRecord]:
        return [
            l for l in self._loans.values()
            if l.player_id == player_id
        ]

    def overdue_loans(
        self, *, now_day: int,
    ) -> list[LoanRecord]:
        return [
            l for l in self._loans.values()
            if (l.returned_day is None
                and now_day > l.due_day)
        ]


__all__ = [
    "BookCategory", "LibraryBook", "LoanRecord",
    "CityLibrarySystem",
]
