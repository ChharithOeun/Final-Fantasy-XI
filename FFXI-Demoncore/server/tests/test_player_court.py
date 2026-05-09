"""Tests for player_court."""
from __future__ import annotations

from server.player_court import (
    PlayerCourtSystem, CourtState,
)


def _found(s: PlayerCourtSystem) -> str:
    return s.found_court(
        chief_justice_id="naji",
        name="Bastok Tribunal",
        jurisdiction=["theft", "assault", "fraud"],
    )


def test_found_happy():
    s = PlayerCourtSystem()
    assert _found(s) is not None


def test_found_empty_chief_blocked():
    s = PlayerCourtSystem()
    assert s.found_court(
        chief_justice_id="", name="x",
        jurisdiction=["theft"],
    ) is None


def test_found_empty_jurisdiction_blocked():
    s = PlayerCourtSystem()
    assert s.found_court(
        chief_justice_id="naji", name="x",
        jurisdiction=[],
    ) is None


def test_chief_is_justice():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.is_justice(
        court_id=cid, person_id="naji",
    ) is True


def test_enroll_associate_happy():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    ) is True


def test_enroll_associate_wrong_chief_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.enroll_associate(
        court_id=cid, chief_justice_id="bob",
        justice_id="alice",
    ) is False


def test_enroll_associate_chief_self_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="naji",
    ) is False


def test_enroll_associate_dup_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    )
    assert s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    ) is False


def test_associate_is_justice():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    )
    assert s.is_justice(
        court_id=cid, person_id="alice",
    ) is True


def test_non_justice_not_a_justice():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.is_justice(
        court_id=cid, person_id="stranger",
    ) is False


def test_has_jurisdiction_match():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.has_jurisdiction(
        court_id=cid, kind="theft",
    ) is True


def test_has_jurisdiction_miss():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.has_jurisdiction(
        court_id=cid, kind="treason",
    ) is False


def test_disband_happy():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.disband(
        court_id=cid, chief_justice_id="naji",
    ) is True
    assert s.court(
        court_id=cid,
    ).state == CourtState.DISBANDED


def test_disband_wrong_chief_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.disband(
        court_id=cid, chief_justice_id="alice",
    ) is False


def test_disband_already_disbanded_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.disband(
        court_id=cid, chief_justice_id="naji",
    )
    assert s.disband(
        court_id=cid, chief_justice_id="naji",
    ) is False


def test_jurisdiction_after_disband_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.disband(
        court_id=cid, chief_justice_id="naji",
    )
    assert s.has_jurisdiction(
        court_id=cid, kind="theft",
    ) is False


def test_enroll_after_disband_blocked():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.disband(
        court_id=cid, chief_justice_id="naji",
    )
    assert s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    ) is False


def test_jurisdiction_listing():
    s = PlayerCourtSystem()
    cid = _found(s)
    assert s.jurisdiction(
        court_id=cid,
    ) == ["assault", "fraud", "theft"]


def test_justices_listing():
    s = PlayerCourtSystem()
    cid = _found(s)
    s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="alice",
    )
    s.enroll_associate(
        court_id=cid, chief_justice_id="naji",
        justice_id="bob",
    )
    assert s.justices(
        court_id=cid,
    ) == ["alice", "bob", "naji"]


def test_unknown_court():
    s = PlayerCourtSystem()
    assert s.court(court_id="ghost") is None


def test_enum_count():
    assert len(list(CourtState)) == 2
