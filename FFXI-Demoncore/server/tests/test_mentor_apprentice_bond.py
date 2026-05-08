"""Tests for mentor_apprentice_bond."""
from __future__ import annotations

from server.mentor_apprentice_bond import (
    BondStage, MentorApprenticeBond,
)


def test_propose_happy():
    m = MentorApprenticeBond()
    assert m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    ) is True


def test_propose_blank_blocked():
    m = MentorApprenticeBond()
    assert m.propose(
        mentor="", apprentice="newbie", job="WAR",
    ) is False


def test_propose_self_blocked():
    m = MentorApprenticeBond()
    assert m.propose(
        mentor="bob", apprentice="bob", job="WAR",
    ) is False


def test_propose_no_job_blocked():
    m = MentorApprenticeBond()
    assert m.propose(
        mentor="bob", apprentice="newbie", job="",
    ) is False


def test_apprentice_one_mentor_only():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    # Another mentor can't propose to same apprentice
    blocked = m.propose(
        mentor="cara", apprentice="newbie", job="MNK",
    )
    assert blocked is False


def test_mentor_three_apprentice_cap():
    m = MentorApprenticeBond()
    m.propose(mentor="bob", apprentice="a", job="WAR")
    m.accept(mentor="bob", apprentice="a")
    m.propose(mentor="bob", apprentice="b", job="WAR")
    m.accept(mentor="bob", apprentice="b")
    m.propose(mentor="bob", apprentice="c", job="WAR")
    # 4th — over cap
    out = m.propose(
        mentor="bob", apprentice="d", job="WAR",
    )
    assert out is False


def test_accept_proposed():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    assert m.accept(
        mentor="bob", apprentice="newbie",
    ) is True
    bond = m.bond(mentor="bob", apprentice="newbie")
    assert bond.stage == BondStage.ACTIVE


def test_accept_already_active_blocked():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.accept(
        mentor="bob", apprentice="newbie",
    ) is False


def test_record_session():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=20,
    ) is True
    bond = m.bond(mentor="bob", apprentice="newbie")
    assert bond.sessions_completed == 1
    assert bond.skill_transferred_pct == 20


def test_record_session_caps_at_100():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=80,
    )
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=80,
    )
    bond = m.bond(mentor="bob", apprentice="newbie")
    assert bond.skill_transferred_pct == 100


def test_record_session_proposed_blocked():
    """Sessions only count once accepted."""
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    out = m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=20,
    )
    assert out is False


def test_unlock_cap():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.unlock_cap(
        mentor="bob", apprentice="newbie",
        ability_id="rookie_provoke",
    ) is True


def test_unlock_cap_dup_blocked():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.unlock_cap(
        mentor="bob", apprentice="newbie",
        ability_id="rookie_provoke",
    )
    assert m.unlock_cap(
        mentor="bob", apprentice="newbie",
        ability_id="rookie_provoke",
    ) is False


def test_graduate_at_100_pct():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=100,
    )
    assert m.graduate(
        mentor="bob", apprentice="newbie",
    ) is True
    bond = m.bond(mentor="bob", apprentice="newbie")
    assert bond.stage == BondStage.GRADUATED


def test_graduate_under_100_blocked():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=50,
    )
    assert m.graduate(
        mentor="bob", apprentice="newbie",
    ) is False


def test_dissolve_by_mentor():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.dissolve(
        by_player="bob", other="newbie",
    ) is True
    bond = m.bond(mentor="bob", apprentice="newbie")
    assert bond.stage == BondStage.DISSOLVED


def test_dissolve_by_apprentice():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.dissolve(
        by_player="newbie", other="bob",
    ) is True


def test_dissolve_after_graduation_blocked():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=100,
    )
    m.graduate(mentor="bob", apprentice="newbie")
    assert m.dissolve(
        by_player="bob", other="newbie",
    ) is False


def test_active_apprentices():
    m = MentorApprenticeBond()
    m.propose(mentor="bob", apprentice="a", job="WAR")
    m.accept(mentor="bob", apprentice="a")
    m.propose(mentor="bob", apprentice="b", job="MNK")
    out = m.active_apprentices(mentor="bob")
    assert out == ["a", "b"]


def test_active_apprentices_excludes_graduated():
    m = MentorApprenticeBond()
    m.propose(mentor="bob", apprentice="a", job="WAR")
    m.accept(mentor="bob", apprentice="a")
    m.record_session(
        mentor="bob", apprentice="a", gain_pct=100,
    )
    m.graduate(mentor="bob", apprentice="a")
    assert m.active_apprentices(mentor="bob") == []


def test_mentor_of_returns_active_mentor():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    assert m.mentor_of(
        apprentice="newbie",
    ) == "bob"


def test_mentor_of_after_graduation_none():
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=100,
    )
    m.graduate(mentor="bob", apprentice="newbie")
    assert m.mentor_of(
        apprentice="newbie",
    ) is None


def test_can_re_propose_after_graduation():
    """Once graduated, mentor can take same apprentice on
    a new job."""
    m = MentorApprenticeBond()
    m.propose(
        mentor="bob", apprentice="newbie", job="WAR",
    )
    m.accept(mentor="bob", apprentice="newbie")
    m.record_session(
        mentor="bob", apprentice="newbie", gain_pct=100,
    )
    m.graduate(mentor="bob", apprentice="newbie")
    assert m.propose(
        mentor="bob", apprentice="newbie", job="MNK",
    ) is True


def test_four_bond_stages():
    assert len(list(BondStage)) == 4
