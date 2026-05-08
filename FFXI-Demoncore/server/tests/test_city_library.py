"""Tests for city_library."""
from __future__ import annotations

from server.city_library import (
    CityLibrarySystem, LibraryBook, BookCategory,
)


def _book(library_id="bastok_lib", **overrides):
    args = dict(
        book_id="bk_history", library_id=library_id,
        title="History of Bastok",
        category=BookCategory.HISTORY,
        is_reference_only=False,
        base_lend_days=7,
        research_bonus_kind="history_xp",
        research_bonus_value=10,
        available_copies=2,
    )
    args.update(overrides)
    return LibraryBook(**args)


def test_open_library():
    s = CityLibrarySystem()
    assert s.open_library(
        library_id="bastok_lib", city="bastok",
    ) is True


def test_open_blank_blocked():
    s = CityLibrarySystem()
    assert s.open_library(
        library_id="", city="bastok",
    ) is False


def test_open_dup_blocked():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    assert s.open_library(
        library_id="bastok_lib", city="bastok",
    ) is False


def test_add_book():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    assert s.add_book(
        library_id="bastok_lib", book=_book(),
    ) is True


def test_add_book_unknown_lib():
    s = CityLibrarySystem()
    assert s.add_book(
        library_id="ghost", book=_book(),
    ) is False


def test_add_book_mismatched_lib():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    bad = _book(library_id="windy_lib")
    assert s.add_book(
        library_id="bastok_lib", book=bad,
    ) is False


def test_add_book_dup_id():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib", book=_book(),
    )
    assert s.add_book(
        library_id="bastok_lib", book=_book(),
    ) is False


def test_borrow_happy():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib", book=_book(),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    assert lid is not None


def test_borrow_decrements_copies():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(available_copies=1),
    )
    s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    # Second borrow blocked - 0 copies
    assert s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="cara", day=1,
    ) is None


def test_borrow_reference_only_blocked():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(is_reference_only=True),
    )
    assert s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    ) is None


def test_borrow_unknown_book():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    assert s.borrow(
        library_id="bastok_lib", book_id="ghost",
        player_id="bob", day=1,
    ) is None


def test_return_happy():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib", book=_book(),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    ok, overdue = s.return_book(loan_id=lid, day=5)
    assert ok and overdue == 0


def test_return_overdue_calculated():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(base_lend_days=7),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    # due day = 8; return at day 12 -> 4 overdue
    ok, overdue = s.return_book(loan_id=lid, day=12)
    assert ok and overdue == 4


def test_return_unknown():
    s = CityLibrarySystem()
    ok, _ = s.return_book(loan_id="ghost", day=5)
    assert ok is False


def test_return_double_blocked():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib", book=_book(),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    s.return_book(loan_id=lid, day=5)
    ok, _ = s.return_book(loan_id=lid, day=6)
    assert ok is False


def test_return_restores_copies():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(available_copies=1),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    s.return_book(loan_id=lid, day=5)
    # Available again
    lid2 = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="cara", day=6,
    )
    assert lid2 is not None


def test_read_in_place():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(research_bonus_kind="magic_acc",
                   research_bonus_value=15),
    )
    out = s.read_in_place(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob",
    )
    assert out == ("magic_acc", 15)


def test_read_in_place_doesnt_decrement():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(available_copies=1),
    )
    s.read_in_place(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob",
    )
    out = s.books(library_id="bastok_lib")
    assert out[0].available_copies == 1


def test_loans_for_player():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib", book=_book(),
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(book_id="bk2", title="Book 2"),
    )
    s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    s.borrow(
        library_id="bastok_lib", book_id="bk2",
        player_id="bob", day=2,
    )
    out = s.loans_for(player_id="bob")
    assert len(out) == 2


def test_overdue_loans():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(base_lend_days=3),
    )
    s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    out = s.overdue_loans(now_day=10)
    assert len(out) == 1


def test_overdue_excludes_returned():
    s = CityLibrarySystem()
    s.open_library(
        library_id="bastok_lib", city="bastok",
    )
    s.add_book(
        library_id="bastok_lib",
        book=_book(base_lend_days=3),
    )
    lid = s.borrow(
        library_id="bastok_lib",
        book_id="bk_history", player_id="bob", day=1,
    )
    s.return_book(loan_id=lid, day=5)
    out = s.overdue_loans(now_day=10)
    assert out == []


def test_books_unknown_lib():
    s = CityLibrarySystem()
    assert s.books(library_id="ghost") == []


def test_enum_count():
    assert len(list(BookCategory)) == 8
