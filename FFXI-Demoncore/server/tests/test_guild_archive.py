"""Tests for guild_archive."""
from __future__ import annotations

from server.guild_archive import (
    GuildArchiveSystem, ArchiveKind,
)


def test_open_happy():
    s = GuildArchiveSystem()
    assert s.open_archive(ls_id="ls_alpha") is True


def test_open_blank_blocked():
    s = GuildArchiveSystem()
    assert s.open_archive(ls_id="") is False


def test_open_dup_blocked():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    assert s.open_archive(ls_id="ls_alpha") is False


def test_record_happy():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    eid = s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="bob joined", day=1,
    )
    assert eid is not None


def test_record_unknown_ls():
    s = GuildArchiveSystem()
    eid = s.record(
        ls_id="ghost",
        kind=ArchiveKind.PROCLAMATION,
        subject="", body="hi", day=1,
    )
    assert eid is None


def test_record_blank_body():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    eid = s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.PROCLAMATION,
        subject="", body="", day=1,
    )
    assert eid is None


def test_record_negative_day():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    eid = s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.PROCLAMATION,
        subject="", body="hi", day=-1,
    )
    assert eid is None


def test_entries_count():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="x", day=1,
    )
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="cara", body="x", day=2,
    )
    assert s.count(ls_id="ls_alpha") == 2


def test_entries_of_kind():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="x", day=1,
    )
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_EXPELLED,
        subject="dave", body="x", day=2,
    )
    out = s.entries_of_kind(
        ls_id="ls_alpha", kind=ArchiveKind.MEMBER_JOINED,
    )
    assert len(out) == 1
    assert out[0].subject == "bob"


def test_entries_about_subject():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="x", day=1,
    )
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_PROMOTED,
        subject="bob", body="x", day=2,
    )
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="cara", body="x", day=3,
    )
    out = s.entries_about(
        ls_id="ls_alpha", subject="bob",
    )
    assert len(out) == 2


def test_entries_unknown_returns_empty():
    s = GuildArchiveSystem()
    assert s.entries(ls_id="ghost") == []


def test_count_unknown():
    s = GuildArchiveSystem()
    assert s.count(ls_id="ghost") == 0


def test_witnesses_preserved():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.HONOR_RECEIVED,
        subject="", body="bestowed", day=10,
        witnesses=["bob", "cara", "dave"],
    )
    out = s.entries(ls_id="ls_alpha")
    assert out[0].witnesses == ("bob", "cara", "dave")


def test_disband_recorded():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.DISBANDED,
        subject="", body="dissolved", day=999,
    )
    out = s.entries_of_kind(
        ls_id="ls_alpha", kind=ArchiveKind.DISBANDED,
    )
    assert len(out) == 1


def test_proclamation_no_subject():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    eid = s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.PROCLAMATION,
        subject="", body="onward!", day=1,
    )
    assert eid is not None


def test_entries_returns_chronological():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="x", day=1,
    )
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="cara", body="x", day=2,
    )
    out = s.entries(ls_id="ls_alpha")
    assert out[0].day == 1 and out[1].day == 2


def test_archive_isolation():
    s = GuildArchiveSystem()
    s.open_archive(ls_id="ls_alpha")
    s.open_archive(ls_id="ls_beta")
    s.record(
        ls_id="ls_alpha",
        kind=ArchiveKind.MEMBER_JOINED,
        subject="bob", body="x", day=1,
    )
    assert s.count(ls_id="ls_alpha") == 1
    assert s.count(ls_id="ls_beta") == 0


def test_enum_count():
    assert len(list(ArchiveKind)) == 13
