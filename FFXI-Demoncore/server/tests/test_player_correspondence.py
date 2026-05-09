"""Tests for player_correspondence."""
from __future__ import annotations

from server.player_correspondence import (
    PlayerCorrespondenceSystem, LetterState,
)


def _send(s, **overrides):
    args = dict(
        author_id="bob", recipients=["cara"],
        subject="Greetings", body="Long letter",
        sent_day=10,
    )
    args.update(overrides)
    return s.send_letter(**args)


def test_send_happy():
    s = PlayerCorrespondenceSystem()
    assert _send(s) is not None


def test_send_blank_author():
    s = PlayerCorrespondenceSystem()
    assert _send(s, author_id="") is None


def test_send_no_recipients():
    s = PlayerCorrespondenceSystem()
    assert _send(s, recipients=[]) is None


def test_send_self_recipient_blocked():
    s = PlayerCorrespondenceSystem()
    assert _send(
        s, recipients=["bob"],
    ) is None


def test_send_dup_recipients_blocked():
    s = PlayerCorrespondenceSystem()
    assert _send(
        s, recipients=["cara", "cara"],
    ) is None


def test_send_blank_subject():
    s = PlayerCorrespondenceSystem()
    assert _send(s, subject="") is None


def test_send_unknown_parent():
    s = PlayerCorrespondenceSystem()
    assert _send(
        s, parent_letter_id="ghost",
    ) is None


def test_send_reply_to_known_parent():
    s = PlayerCorrespondenceSystem()
    pid = _send(s)
    rid = _send(
        s, author_id="cara", recipients=["bob"],
        subject="Re: Greetings",
        body="reply", parent_letter_id=pid,
        sent_day=11,
    )
    assert rid is not None


def test_state_starts_unread():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    assert s.state_for(
        letter_id=lid, recipient_id="cara",
    ) == LetterState.UNREAD


def test_mark_read():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    assert s.mark_read(
        letter_id=lid, recipient_id="cara",
    ) is True


def test_mark_read_double_blocked():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    s.mark_read(letter_id=lid, recipient_id="cara")
    assert s.mark_read(
        letter_id=lid, recipient_id="cara",
    ) is False


def test_mark_read_archived_blocked():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    s.archive(letter_id=lid, recipient_id="cara")
    assert s.mark_read(
        letter_id=lid, recipient_id="cara",
    ) is False


def test_archive():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    assert s.archive(
        letter_id=lid, recipient_id="cara",
    ) is True


def test_delete():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    assert s.delete(
        letter_id=lid, recipient_id="cara",
    ) is True


def test_inbox_excludes_deleted():
    s = PlayerCorrespondenceSystem()
    lid_a = _send(s, body="a")
    lid_b = _send(s, body="b", sent_day=11)
    s.delete(letter_id=lid_a, recipient_id="cara")
    out = s.inbox(recipient_id="cara")
    ids = [l.letter_id for l in out]
    assert lid_a not in ids
    assert lid_b in ids


def test_inbox_excludes_archived_by_default():
    s = PlayerCorrespondenceSystem()
    lid_a = _send(s, body="a")
    lid_b = _send(s, body="b", sent_day=11)
    s.archive(letter_id=lid_a, recipient_id="cara")
    out = s.inbox(recipient_id="cara")
    assert all(l.letter_id != lid_a for l in out)


def test_inbox_includes_archived_when_asked():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    s.archive(letter_id=lid, recipient_id="cara")
    out = s.inbox(
        recipient_id="cara",
        include_archived=True,
    )
    assert any(l.letter_id == lid for l in out)


def test_inbox_sorted_chronological():
    s = PlayerCorrespondenceSystem()
    _send(s, body="b", sent_day=20)
    _send(s, body="a", sent_day=10)
    out = s.inbox(recipient_id="cara")
    assert [l.sent_day for l in out] == [10, 20]


def test_thread_of():
    s = PlayerCorrespondenceSystem()
    a = _send(s, body="root", sent_day=10)
    b = _send(
        s, author_id="cara", recipients=["bob"],
        subject="Re", body="b", parent_letter_id=a,
        sent_day=11,
    )
    c = _send(
        s, body="c", parent_letter_id=b,
        sent_day=12,
    )
    chain = s.thread_of(letter_id=c)
    assert [l.letter_id for l in chain] == [a, b, c]


def test_thread_unknown():
    s = PlayerCorrespondenceSystem()
    assert s.thread_of(letter_id="ghost") == []


def test_replies_to():
    s = PlayerCorrespondenceSystem()
    a = _send(s)
    b = _send(
        s, author_id="cara", recipients=["bob"],
        subject="Re", body="b",
        parent_letter_id=a, sent_day=11,
    )
    c = _send(
        s, author_id="dave", recipients=["bob"],
        subject="Re", body="c",
        parent_letter_id=a, sent_day=12,
    )
    out = s.replies_to(letter_id=a)
    ids = sorted(l.letter_id for l in out)
    assert ids == sorted([b, c])


def test_unread_count():
    s = PlayerCorrespondenceSystem()
    _send(s, body="a")
    lid_b = _send(s, body="b", sent_day=11)
    s.mark_read(
        letter_id=lid_b, recipient_id="cara",
    )
    assert s.unread_count(
        recipient_id="cara",
    ) == 1


def test_letter_unknown():
    s = PlayerCorrespondenceSystem()
    assert s.letter(letter_id="ghost") is None


def test_state_for_unknown_recipient():
    s = PlayerCorrespondenceSystem()
    lid = _send(s)
    assert s.state_for(
        letter_id=lid, recipient_id="dave",
    ) is None


def test_multi_recipient_states_independent():
    s = PlayerCorrespondenceSystem()
    lid = _send(
        s, recipients=["cara", "dave"],
    )
    s.mark_read(letter_id=lid, recipient_id="cara")
    assert s.state_for(
        letter_id=lid, recipient_id="cara",
    ) == LetterState.READ
    assert s.state_for(
        letter_id=lid, recipient_id="dave",
    ) == LetterState.UNREAD


def test_enum_count():
    assert len(list(LetterState)) == 4
