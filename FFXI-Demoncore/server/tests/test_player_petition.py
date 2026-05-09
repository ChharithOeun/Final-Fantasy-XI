"""Tests for player_petition."""
from __future__ import annotations

from server.player_petition import (
    PlayerPetitionSystem, PetitionState,
)


def _launch(
    s: PlayerPetitionSystem, goal: int = 3,
) -> str:
    return s.launch(
        founder_id="naji",
        cause="Repair the Bastok mines lift",
        goal_signatures=goal,
    )


def test_launch_happy():
    s = PlayerPetitionSystem()
    assert _launch(s) is not None


def test_launch_empty_cause_blocked():
    s = PlayerPetitionSystem()
    assert s.launch(
        founder_id="naji", cause="",
        goal_signatures=10,
    ) is None


def test_launch_zero_goal_blocked():
    s = PlayerPetitionSystem()
    assert _launch(s, goal=0) is None


def test_sign_happy():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    assert s.sign(
        petition_id=pid, signer_id="alice",
        current_day=10,
    ) is True


def test_sign_empty_signer_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    assert s.sign(
        petition_id=pid, signer_id="",
        current_day=10,
    ) is False


def test_sign_dup_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    s.sign(
        petition_id=pid, signer_id="alice",
        current_day=10,
    )
    assert s.sign(
        petition_id=pid, signer_id="alice",
        current_day=11,
    ) is False


def test_sign_unknown_petition_blocked():
    s = PlayerPetitionSystem()
    assert s.sign(
        petition_id="ghost", signer_id="alice",
        current_day=10,
    ) is False


def test_signature_count_advances():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=10)
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    )
    s.sign(
        petition_id=pid, signer_id="b",
        current_day=10,
    )
    assert s.petition(
        petition_id=pid,
    ).signature_count == 2


def test_auto_resolve_at_goal():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=3)
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    )
    s.sign(
        petition_id=pid, signer_id="b",
        current_day=11,
    )
    s.sign(
        petition_id=pid, signer_id="c",
        current_day=12,
    )
    p = s.petition(petition_id=pid)
    assert p.state == PetitionState.RESOLVED
    assert p.resolved_day == 12


def test_sign_after_resolve_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=2)
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    )
    s.sign(
        petition_id=pid, signer_id="b",
        current_day=10,
    )
    assert s.sign(
        petition_id=pid, signer_id="c",
        current_day=11,
    ) is False


def test_withdraw_happy():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    assert s.withdraw(
        petition_id=pid, founder_id="naji",
    ) is True
    assert s.petition(
        petition_id=pid,
    ).state == PetitionState.WITHDRAWN


def test_withdraw_wrong_founder_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    assert s.withdraw(
        petition_id=pid, founder_id="bob",
    ) is False


def test_withdraw_after_resolve_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=1)
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    )
    assert s.withdraw(
        petition_id=pid, founder_id="naji",
    ) is False


def test_sign_after_withdraw_blocked():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    s.withdraw(
        petition_id=pid, founder_id="naji",
    )
    assert s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    ) is False


def test_signers_listing():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=10)
    s.sign(
        petition_id=pid, signer_id="b",
        current_day=10,
    )
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=11,
    )
    assert s.signers(petition_id=pid) == ["a", "b"]


def test_unknown_petition():
    s = PlayerPetitionSystem()
    assert s.petition(petition_id="ghost") is None


def test_unknown_petition_signers_empty():
    s = PlayerPetitionSystem()
    assert s.signers(petition_id="ghost") == []


def test_withdraw_unknown_blocked():
    s = PlayerPetitionSystem()
    assert s.withdraw(
        petition_id="ghost", founder_id="naji",
    ) is False


def test_resolve_doesnt_advance_past_goal():
    s = PlayerPetitionSystem()
    pid = _launch(s, goal=2)
    s.sign(
        petition_id=pid, signer_id="a",
        current_day=10,
    )
    s.sign(
        petition_id=pid, signer_id="b",
        current_day=10,
    )
    # Already resolved; can't sign more
    assert s.sign(
        petition_id=pid, signer_id="c",
        current_day=11,
    ) is False
    assert s.petition(
        petition_id=pid,
    ).signature_count == 2


def test_enum_count():
    assert len(list(PetitionState)) == 3


def test_launch_empty_founder_blocked():
    s = PlayerPetitionSystem()
    assert s.launch(
        founder_id="", cause="x",
        goal_signatures=10,
    ) is None


def test_petition_lookup_open_state():
    s = PlayerPetitionSystem()
    pid = _launch(s)
    assert s.petition(
        petition_id=pid,
    ).state == PetitionState.OPEN
