"""Tests for public_libraries."""
from __future__ import annotations

from server.public_libraries import (
    Book, Library, PublicLibraries, Rarity,
)


def _bastok():
    return Library(
        library_id="bastok_lib", nation="bastok",
        display_name="Metalworks Archive",
    )


def _sandy():
    return Library(
        library_id="sandy_lib", nation="sandy",
        display_name="Cathedral Library",
    )


def _book(bid="ironworks_history", lib="bastok_lib",
          title="History of the Ironworks",
          author="Cid", body="A century of forging.",
          tags=("history", "bastok"),
          rarity=Rarity.COMMON, fame=None,
          value=2, lendable=False):
    return Book(
        book_id=bid, library_id=lib, title=title,
        author=author, body=body,
        tags=frozenset(tags), rarity=rarity,
        required_fame=fame, research_value=value,
        lendable=lendable,
    )


def test_register_library():
    p = PublicLibraries()
    assert p.register_library(_bastok()) is True


def test_register_library_blank_blocked():
    p = PublicLibraries()
    bad = Library(
        library_id="", nation="bastok", display_name="x",
    )
    assert p.register_library(bad) is False


def test_register_library_dup_blocked():
    p = PublicLibraries()
    p.register_library(_bastok())
    assert p.register_library(_bastok()) is False


def test_register_book():
    p = PublicLibraries()
    p.register_library(_bastok())
    assert p.register_book(_book()) is True


def test_register_book_unknown_library():
    p = PublicLibraries()
    assert p.register_book(_book()) is False


def test_register_book_blank_id():
    p = PublicLibraries()
    p.register_library(_bastok())
    bad = _book(bid="")
    assert p.register_book(bad) is False


def test_register_book_dup_blocked():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book())
    assert p.register_book(_book()) is False


def test_read_credits_first():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(value=3))
    out = p.read(
        player_id="bob", book_id="ironworks_history",
    )
    assert out.is_first_read is True
    assert out.research_credited == 3


def test_read_second_no_credit():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(value=3))
    p.read(
        player_id="bob", book_id="ironworks_history",
    )
    out = p.read(
        player_id="bob", book_id="ironworks_history",
    )
    assert out.is_first_read is False
    assert out.research_credited == 0


def test_read_fame_locked():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(fame=("bastok", 5)))
    blocked = p.read(
        player_id="bob", book_id="ironworks_history",
        fame_levels={"bastok": 3},
    )
    assert blocked is None


def test_read_fame_unlocked():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(fame=("bastok", 5)))
    out = p.read(
        player_id="bob", book_id="ironworks_history",
        fame_levels={"bastok": 6},
    )
    assert out is not None


def test_read_restricted_no_fame_blocked():
    """RESTRICTED with no fame gate is default-deny."""
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(
        _book(rarity=Rarity.RESTRICTED, fame=None),
    )
    out = p.read(
        player_id="bob", book_id="ironworks_history",
    )
    assert out is None


def test_search_by_tag():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(
        bid="a", title="A", tags=("history", "bastok"),
    ))
    p.register_book(_book(
        bid="b", title="B", tags=("magic", "bastok"),
    ))
    p.register_book(_book(
        bid="c", title="C", tags=("history", "sandy"),
    ))
    out = p.search(
        library_id="bastok_lib", tags=["history"],
    )
    pids = {b.book_id for b in out}
    assert pids == {"a", "c"}


def test_search_must_match_all_tags():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(
        bid="a", title="A", tags=("history", "bastok"),
    ))
    p.register_book(_book(
        bid="b", title="B", tags=("magic", "bastok"),
    ))
    out = p.search(
        library_id="bastok_lib",
        tags=["history", "bastok"],
    )
    pids = {b.book_id for b in out}
    assert pids == {"a"}


def test_search_empty_tags_lists_all():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(bid="a", title="A"))
    p.register_book(_book(bid="b", title="B"))
    out = p.search(library_id="bastok_lib", tags=[])
    assert len(out) == 2


def test_search_unknown_library():
    p = PublicLibraries()
    out = p.search(library_id="ghost", tags=[])
    assert out == []


def test_search_fame_locked_hidden():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(bid="a"))
    p.register_book(_book(
        bid="b", title="B", fame=("bastok", 9),
    ))
    out = p.search(
        library_id="bastok_lib", tags=[],
        fame_levels={"bastok": 1},
    )
    pids = {b.book_id for b in out}
    assert pids == {"a"}


def test_lend_book():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_library(_sandy())
    p.register_book(_book(lendable=True))
    assert p.lend(
        book_id="ironworks_history",
        to_library_id="sandy_lib",
    ) is True


def test_lend_non_lendable_blocked():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_library(_sandy())
    p.register_book(_book(lendable=False))
    assert p.lend(
        book_id="ironworks_history",
        to_library_id="sandy_lib",
    ) is False


def test_lend_self_blocked():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(lendable=True))
    assert p.lend(
        book_id="ironworks_history",
        to_library_id="bastok_lib",
    ) is False


def test_lent_book_searchable_in_loaner():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_library(_sandy())
    p.register_book(_book(lendable=True))
    p.lend(
        book_id="ironworks_history",
        to_library_id="sandy_lib",
    )
    out = p.search(
        library_id="sandy_lib", tags=[],
    )
    assert any(
        b.book_id == "ironworks_history" for b in out
    )


def test_reading_history():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book(bid="a"))
    p.register_book(_book(bid="b", title="B"))
    p.read(player_id="bob", book_id="a")
    p.read(player_id="bob", book_id="b")
    history = p.reading_history(player_id="bob")
    assert history == ["a", "b"]


def test_first_reader():
    p = PublicLibraries()
    p.register_library(_bastok())
    p.register_book(_book())
    p.read(
        player_id="bob", book_id="ironworks_history",
    )
    p.read(
        player_id="cara", book_id="ironworks_history",
    )
    assert p.first_reader(
        book_id="ironworks_history",
    ) == "bob"


def test_three_rarities():
    assert len(list(Rarity)) == 3
