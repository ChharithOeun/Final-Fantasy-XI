"""Tests for player_advice_column."""
from __future__ import annotations

from server.player_advice_column import (
    PlayerAdviceColumnSystem, LetterState,
)


def _start(s: PlayerAdviceColumnSystem) -> str:
    return s.start_column(
        columnist_id="naji", name="Dear Naji",
    )


def test_start_happy():
    s = PlayerAdviceColumnSystem()
    assert _start(s) is not None


def test_start_empty_blocked():
    s = PlayerAdviceColumnSystem()
    assert s.start_column(
        columnist_id="", name="x",
    ) is None


def test_submit_letter_happy():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob",
        problem="my friend stole my cardian",
    )
    assert lid is not None


def test_submit_letter_columnist_self_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    assert s.submit_letter(
        column_id=cid, writer_id="naji", problem="x",
    ) is None


def test_submit_letter_empty_problem_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    assert s.submit_letter(
        column_id=cid, writer_id="bob", problem="",
    ) is None


def test_answer_letter_happy():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    assert s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="Talk to them.",
    ) is True
    assert s.letter(
        column_id=cid, letter_id=lid,
    ).state == LetterState.ANSWERED


def test_answer_letter_wrong_columnist_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    assert s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="bob", response="r",
    ) is False


def test_answer_letter_empty_response_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    assert s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="",
    ) is False


def test_answer_letter_twice_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r2",
    ) is False


def test_decline_letter_happy():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    assert s.decline_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji",
    ) is True


def test_decline_already_answered_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.decline_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji",
    ) is False


def test_rate_response_happy():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=5,
    ) is True


def test_rate_unanswered_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=5,
    ) is False


def test_rate_writer_self_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="bob", stars=5,
    ) is False


def test_rate_columnist_self_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="naji", stars=5,
    ) is False


def test_rate_invalid_stars_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=10,
    ) is False


def test_rate_same_reader_twice_blocked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=5,
    )
    assert s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=3,
    ) is False


def test_average_stars_computed():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    s.answer_letter(
        column_id=cid, letter_id=lid,
        columnist_id="naji", response="r",
    )
    s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="cara", stars=4,
    )
    s.rate_response(
        column_id=cid, letter_id=lid,
        reader_id="dax", stars=2,
    )
    assert s.letter(
        column_id=cid, letter_id=lid,
    ).average_stars == 3.0


def test_anonymous_letter_masked():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
        anonymous=True,
    )
    assert s.public_view(
        column_id=cid, letter_id=lid,
    ).writer_id == "anonymous"


def test_non_anon_letter_visible():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    lid = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
        anonymous=False,
    )
    assert s.public_view(
        column_id=cid, letter_id=lid,
    ).writer_id == "bob"


def test_average_for_columnist_global():
    s = PlayerAdviceColumnSystem()
    cid = _start(s)
    l1 = s.submit_letter(
        column_id=cid, writer_id="bob", problem="x",
    )
    l2 = s.submit_letter(
        column_id=cid, writer_id="cara", problem="y",
    )
    s.answer_letter(
        column_id=cid, letter_id=l1,
        columnist_id="naji", response="r",
    )
    s.answer_letter(
        column_id=cid, letter_id=l2,
        columnist_id="naji", response="r",
    )
    s.rate_response(
        column_id=cid, letter_id=l1,
        reader_id="dax", stars=4,
    )
    s.rate_response(
        column_id=cid, letter_id=l2,
        reader_id="dax", stars=2,
    )
    assert s.average_for_columnist(
        column_id=cid,
    ) == 3.0


def test_enum_count():
    assert len(list(LetterState)) == 3
