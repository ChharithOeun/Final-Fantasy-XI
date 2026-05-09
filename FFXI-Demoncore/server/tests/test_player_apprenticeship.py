"""Tests for player_apprenticeship."""
from __future__ import annotations

from server.player_apprenticeship import (
    PlayerApprenticeshipSystem, ApprenticeshipState,
)


def _propose(s: PlayerApprenticeshipSystem) -> str:
    return s.propose(
        master_id="naji", apprentice_id="bob",
        craft="alchemy", master_skill=100,
        apprentice_starting_skill=20,
        proposed_day=10,
    )


def test_propose_happy():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    assert aid is not None


def test_propose_self_blocked():
    s = PlayerApprenticeshipSystem()
    assert s.propose(
        master_id="naji", apprentice_id="naji",
        craft="alchemy", master_skill=100,
        apprentice_starting_skill=20,
        proposed_day=10,
    ) is None


def test_propose_apprentice_above_master_blocked():
    s = PlayerApprenticeshipSystem()
    assert s.propose(
        master_id="naji", apprentice_id="bob",
        craft="alchemy", master_skill=50,
        apprentice_starting_skill=80,
        proposed_day=10,
    ) is None


def test_propose_dup_active_blocked():
    s = PlayerApprenticeshipSystem()
    _propose(s)
    # Bob already in alchemy apprenticeship
    assert s.propose(
        master_id="other", apprentice_id="bob",
        craft="alchemy", master_skill=80,
        apprentice_starting_skill=20,
        proposed_day=15,
    ) is None


def test_propose_different_craft_ok():
    s = PlayerApprenticeshipSystem()
    _propose(s)
    aid2 = s.propose(
        master_id="other", apprentice_id="bob",
        craft="cooking", master_skill=80,
        apprentice_starting_skill=20,
        proposed_day=15,
    )
    assert aid2 is not None


def test_accept_happy():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    assert s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    ) is True


def test_accept_wrong_apprentice_blocked():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    assert s.accept(
        apprenticeship_id=aid, apprentice_id="cara",
    ) is False


def test_train_session_grows_skill():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    new_skill = s.train_session(
        apprenticeship_id=aid,
    )
    # gain = (100 - 20) // 5 = 16; new = 20+16 = 36
    assert new_skill == 36


def test_train_skill_capped_at_master():
    s = PlayerApprenticeshipSystem()
    aid = s.propose(
        master_id="m", apprentice_id="a",
        craft="x", master_skill=50,
        apprentice_starting_skill=49,
        proposed_day=10,
    )
    s.accept(
        apprenticeship_id=aid, apprentice_id="a",
    )
    new_skill = s.train_session(
        apprenticeship_id=aid,
    )
    # gain = max(1, 1//5) = 1, new = 50, capped at master 50
    assert new_skill == 50


def test_train_before_accept_blocked():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    assert s.train_session(
        apprenticeship_id=aid,
    ) is None


def test_graduate_requires_threshold():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    # Only one session, skill < 100
    s.train_session(apprenticeship_id=aid)
    assert s.graduate(
        apprenticeship_id=aid,
    ) is None


def test_graduate_happy():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    # Hammer through enough sessions to hit 100
    for _ in range(20):
        s.train_session(apprenticeship_id=aid)
    final = s.graduate(apprenticeship_id=aid)
    assert final == 100


def test_graduate_state_set():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    for _ in range(20):
        s.train_session(apprenticeship_id=aid)
    s.graduate(apprenticeship_id=aid)
    assert s.apprenticeship(
        apprenticeship_id=aid,
    ).state == ApprenticeshipState.GRADUATED


def test_graduate_session_count_floor():
    """Graduation requires both threshold and at
    least 5 sessions — even if you propose with
    starting_skill very close to master."""
    s = PlayerApprenticeshipSystem()
    aid = s.propose(
        master_id="m", apprentice_id="a",
        craft="x", master_skill=100,
        apprentice_starting_skill=99,
        proposed_day=10,
    )
    s.accept(
        apprenticeship_id=aid, apprentice_id="a",
    )
    # 1 session: 99 + max(1, 1//5)=1 = 100, threshold met
    s.train_session(apprenticeship_id=aid)
    # But only 1 session, less than 5 — blocked
    assert s.graduate(
        apprenticeship_id=aid,
    ) is None
    # Top up to 5 sessions
    for _ in range(4):
        s.train_session(apprenticeship_id=aid)
    assert s.graduate(
        apprenticeship_id=aid,
    ) == 100


def test_dissolve_by_master():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    assert s.dissolve(
        apprenticeship_id=aid, party_id="naji",
    ) is True


def test_dissolve_by_apprentice():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    assert s.dissolve(
        apprenticeship_id=aid, party_id="bob",
    ) is True


def test_dissolve_third_party_blocked():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    assert s.dissolve(
        apprenticeship_id=aid, party_id="cara",
    ) is False


def test_dissolve_after_graduate_blocked():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    for _ in range(20):
        s.train_session(apprenticeship_id=aid)
    s.graduate(apprenticeship_id=aid)
    assert s.dissolve(
        apprenticeship_id=aid, party_id="naji",
    ) is False


def test_apprentices_of_master():
    s = PlayerApprenticeshipSystem()
    s.propose(
        master_id="naji", apprentice_id="bob",
        craft="alchemy", master_skill=100,
        apprentice_starting_skill=20,
        proposed_day=10,
    )
    s.propose(
        master_id="naji", apprentice_id="cara",
        craft="cooking", master_skill=100,
        apprentice_starting_skill=20,
        proposed_day=10,
    )
    apps = s.apprentices_of(master_id="naji")
    assert len(apps) == 2


def test_dissolved_can_re_propose():
    s = PlayerApprenticeshipSystem()
    aid = _propose(s)
    s.accept(
        apprenticeship_id=aid, apprentice_id="bob",
    )
    s.dissolve(
        apprenticeship_id=aid, party_id="naji",
    )
    # Bob can start fresh in alchemy again
    aid2 = s.propose(
        master_id="other", apprentice_id="bob",
        craft="alchemy", master_skill=80,
        apprentice_starting_skill=20,
        proposed_day=20,
    )
    assert aid2 is not None


def test_unknown_apprenticeship():
    s = PlayerApprenticeshipSystem()
    assert s.apprenticeship(
        apprenticeship_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(ApprenticeshipState)) == 4
