"""Tests for gearswap_apprentice."""
from __future__ import annotations

from server.gearswap_apprentice import (
    ApprenticeStatus, GearswapApprentice,
)
from server.gearswap_publisher import GearswapPublisher


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    a = GearswapApprentice(_publisher=p)
    return p, a


def test_accept_happy():
    _, a = _seed()
    out = a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    assert out is True
    assert a.mentor_of(apprentice_id="bob") == "chharith"


def test_accept_blank_mentor_blocked():
    _, a = _seed()
    assert a.accept(
        mentor_id="", apprentice_id="bob", started_at=1000,
    ) is False


def test_accept_blank_apprentice_blocked():
    _, a = _seed()
    assert a.accept(
        mentor_id="chharith", apprentice_id="",
        started_at=1000,
    ) is False


def test_accept_self_blocked():
    _, a = _seed()
    assert a.accept(
        mentor_id="bob", apprentice_id="bob",
        started_at=1000,
    ) is False


def test_accept_non_mentor_blocked():
    _, a = _seed()
    out = a.accept(
        mentor_id="someone_unverified",
        apprentice_id="bob", started_at=1000,
    )
    assert out is False


def test_accept_apprentice_already_taken():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    out = a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=2000,
    )
    assert out is False


def test_apprentice_cap_5():
    _, a = _seed()
    for i in range(5):
        a.accept(
            mentor_id="chharith",
            apprentice_id=f"app{i}", started_at=1000,
        )
    out = a.accept(
        mentor_id="chharith", apprentice_id="overflow",
        started_at=2000,
    )
    assert out is False


def test_open_slots_starts_at_5():
    _, a = _seed()
    assert a.open_slots(mentor_id="chharith") == 5


def test_open_slots_decrements():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    assert a.open_slots(mentor_id="chharith") == 4


def test_release_by_mentor_marks_graduated():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    out = a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=True, ended_at=2000,
    )
    assert out is True
    assert a.mentor_of(apprentice_id="bob") is None


def test_release_by_apprentice_marks_quit():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=False, ended_at=2000,
    )
    # Quit doesn't count toward graduates_taught
    assert a.graduates_taught(mentor_id="chharith") == 0


def test_release_unknown_blocked():
    _, a = _seed()
    out = a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=True, ended_at=2000,
    )
    assert out is False


def test_release_frees_slot():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=True,
    )
    assert a.open_slots(mentor_id="chharith") == 5


def test_record_graduation_returns_mentor():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    out = a.record_graduation(
        apprentice_id="bob", graduated_at=5000,
    )
    assert out == "chharith"


def test_record_graduation_increments_taught():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.record_graduation(
        apprentice_id="bob", graduated_at=5000,
    )
    assert a.graduates_taught(mentor_id="chharith") == 1


def test_record_graduation_no_active_returns_none():
    _, a = _seed()
    out = a.record_graduation(
        apprentice_id="ghost", graduated_at=5000,
    )
    assert out is None


def test_record_graduation_already_graduated_no_dup():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.record_graduation(
        apprentice_id="bob", graduated_at=5000,
    )
    # No active record now; second graduation call no-ops
    out = a.record_graduation(
        apprentice_id="bob", graduated_at=6000,
    )
    assert out is None
    assert a.graduates_taught(mentor_id="chharith") == 1


def test_apprentices_of_lists_active_only():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.accept(
        mentor_id="chharith", apprentice_id="cara",
        started_at=2000,
    )
    a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=True,
    )
    out = a.apprentices_of(mentor_id="chharith")
    assert len(out) == 1
    assert out[0].apprentice_id == "cara"


def test_re_accept_after_quit_allowed():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.release(
        mentor_id="chharith", apprentice_id="bob",
        by_mentor=False,
    )
    out = a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=3000,
    )
    assert out is True


def test_total_active():
    _, a = _seed()
    a.accept(
        mentor_id="chharith", apprentice_id="bob",
        started_at=1000,
    )
    a.accept(
        mentor_id="chharith", apprentice_id="cara",
        started_at=1000,
    )
    assert a.total_active() == 2


def test_three_apprentice_statuses():
    assert len(list(ApprenticeStatus)) == 3
