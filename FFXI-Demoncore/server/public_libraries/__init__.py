"""Public libraries — searchable in-world lore archives.

Each major nation has a public library — Bastok's Metalworks
Archive, Sandy's Cathedral Library, Windy's Heavens Tower
Stacks, Norg's Manuscript Hall, Tavnazia's Cathedral Vault.
Players walk in, browse the catalog, sit at a table, and
read.

A LIBRARY is a registry of BOOKS. A BOOK has:
    book_id, library_id, title, author, body, tag set,
    rarity (COMMON/RARE/RESTRICTED), required_fame.

Players have a personal "research_notes" — books they've
read get logged. Reading a never-read book credits
research_value to the player. The first reader on the
server gets a "Discoverer" badge for the book.

A library can also be queried — search() takes a list of
tag tokens; books matching ALL tokens return. This is the
in-game equivalent of an index card catalog. Restricted
books require explicit fame_level access; otherwise
search() filters them out.

Inter-library lending: a book registered in Bastok's library
can be marked LENDABLE — Sandy's library can borrow it,
making it readable there too. We track that as a copy
(loan) record.

Public surface
--------------
    Rarity enum
    Library dataclass (frozen)
    Book dataclass (frozen)
    SearchResult dataclass (frozen)
    PublicLibraries
        .register_library(library) -> bool
        .register_book(book) -> bool
        .lend(book_id, to_library_id) -> bool
        .read(player_id, book_id, fame_levels) -> Optional[SearchResult]
        .search(library_id, tags, fame_levels) -> list[Book]
        .reading_history(player_id) -> list[str]
        .first_reader(book_id) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Rarity(str, enum.Enum):
    COMMON = "common"
    RARE = "rare"
    RESTRICTED = "restricted"


@dataclasses.dataclass(frozen=True)
class Library:
    library_id: str
    nation: str
    display_name: str


@dataclasses.dataclass(frozen=True)
class Book:
    book_id: str
    library_id: str
    title: str
    author: str
    body: str
    tags: frozenset[str]
    rarity: Rarity = Rarity.COMMON
    required_fame: t.Optional[tuple[str, int]] = None
    research_value: int = 1
    lendable: bool = False


@dataclasses.dataclass(frozen=True)
class SearchResult:
    book_id: str
    title: str
    body: str
    is_first_read: bool
    research_credited: int


@dataclasses.dataclass
class PublicLibraries:
    _libraries: dict[str, Library] = dataclasses.field(
        default_factory=dict,
    )
    _books: dict[str, Book] = dataclasses.field(
        default_factory=dict,
    )
    # extra (book_id, library_id) loan copies
    _loans: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    _read: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    _first: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_library(self, library: Library) -> bool:
        if not library.library_id or not library.nation:
            return False
        if not library.display_name:
            return False
        if library.library_id in self._libraries:
            return False
        self._libraries[library.library_id] = library
        return True

    def register_book(self, book: Book) -> bool:
        if not book.book_id or not book.title:
            return False
        if book.library_id not in self._libraries:
            return False
        if book.research_value < 0:
            return False
        if book.book_id in self._books:
            return False
        self._books[book.book_id] = book
        return True

    def lend(
        self, *, book_id: str, to_library_id: str,
    ) -> bool:
        if book_id not in self._books:
            return False
        if to_library_id not in self._libraries:
            return False
        book = self._books[book_id]
        if not book.lendable:
            return False
        if book.library_id == to_library_id:
            return False
        key = (book_id, to_library_id)
        if key in self._loans:
            return False
        self._loans.add(key)
        return True

    def _book_in_library(
        self, book_id: str, library_id: str,
    ) -> bool:
        book = self._books.get(book_id)
        if book is None:
            return False
        if book.library_id == library_id:
            return True
        return (book_id, library_id) in self._loans

    def read(
        self, *, player_id: str, book_id: str,
        fame_levels: t.Optional[dict[str, int]] = None,
    ) -> t.Optional[SearchResult]:
        if not player_id or book_id not in self._books:
            return None
        book = self._books[book_id]
        if book.required_fame is not None:
            city, needed = book.required_fame
            cur = (fame_levels or {}).get(city, 0)
            if cur < needed:
                return None
        # RESTRICTED rarity always needs fame_unlock; if
        # the book has no fame_unlock and it's RESTRICTED,
        # default-deny.
        if book.rarity == Rarity.RESTRICTED \
                and book.required_fame is None:
            return None
        key = (player_id, book_id)
        is_first = key not in self._read
        research = 0
        if is_first:
            self._read.add(key)
            research = book.research_value
            if book_id not in self._first:
                self._first[book_id] = player_id
        return SearchResult(
            book_id=book_id, title=book.title,
            body=book.body, is_first_read=is_first,
            research_credited=research,
        )

    def search(
        self, *, library_id: str,
        tags: t.Iterable[str],
        fame_levels: t.Optional[dict[str, int]] = None,
    ) -> list[Book]:
        if library_id not in self._libraries:
            return []
        wanted = set(tags)
        out = []
        for book in self._books.values():
            if not self._book_in_library(
                book.book_id, library_id,
            ):
                continue
            # Fame gate
            if book.required_fame is not None:
                city, needed = book.required_fame
                cur = (fame_levels or {}).get(city, 0)
                if cur < needed:
                    continue
            elif book.rarity == Rarity.RESTRICTED:
                continue
            # Tag match — book must contain ALL wanted tags
            if wanted and not wanted.issubset(book.tags):
                continue
            out.append(book)
        out.sort(key=lambda b: b.title)
        return out

    def reading_history(
        self, *, player_id: str,
    ) -> list[str]:
        return sorted(
            bid for (pid, bid) in self._read
            if pid == player_id
        )

    def first_reader(
        self, *, book_id: str,
    ) -> t.Optional[str]:
        return self._first.get(book_id)


__all__ = [
    "Rarity", "Library", "Book", "SearchResult",
    "PublicLibraries",
]
