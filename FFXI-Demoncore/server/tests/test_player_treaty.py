"""Tests for player_treaty."""
from __future__ import annotations

from server.player_treaty import (
    PlayerTreatySystem, TreatyState, TreatyTerm,
)


def _propose(
    s: PlayerTreatySystem,
    proposer: str = "naji", accepter: str = "volker",
    day: int = 10,
) -> str:
    return s.propose(
        proposer_id=proposer, accepter_id=accepter,
        terms=(
            TreatyTerm.NO_COMBAT,
            TreatyTerm.NO_BOUNTIES,
        ),
        proposed_day=day,
    )


def test_propose_happy():
    s = PlayerTreatySystem()
    tid = _propose(s)
    assert tid is not None


def test_propose_self_blocked():
    s = PlayerTreatySystem()
    assert s.propose(
        proposer_id="naji", accepter_id="naji",
        terms=(TreatyTerm.NO_COMBAT,),
        proposed_day=10,
    ) is None


def test_propose_empty_terms_blocked():
    s = PlayerTreatySystem()
    assert s.propose(
        proposer_id="a", accepter_id="b",
        terms=(), proposed_day=10,
    ) is None


def test_propose_dup_terms_blocked():
    s = PlayerTreatySystem()
    assert s.propose(
        proposer_id="a", accepter_id="b",
        terms=(
            TreatyTerm.NO_COMBAT, TreatyTerm.NO_COMBAT,
        ),
        proposed_day=10,
    ) is None


def test_propose_dup_pair_blocked():
    s = PlayerTreatySystem()
    _propose(s)
    # Either direction is blocked
    assert s.propose(
        proposer_id="volker", accepter_id="naji",
        terms=(TreatyTerm.NO_COMBAT,),
        proposed_day=11,
    ) is None


def test_sign_happy():
    s = PlayerTreatySystem()
    tid = _propose(s)
    assert s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    ) is True


def test_sign_wrong_signer_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s)
    # Proposer can't self-sign
    assert s.sign(
        treaty_id=tid, signer_id="naji",
        signed_day=12,
    ) is False


def test_sign_third_party_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s)
    assert s.sign(
        treaty_id=tid, signer_id="cara",
        signed_day=12,
    ) is False


def test_sign_double_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    assert s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=13,
    ) is False


def test_signed_treaty_active_between():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    assert s.is_active_between(
        player_a="naji", player_b="volker",
    ) is True
    assert s.is_active_between(
        player_a="volker", player_b="naji",
    ) is True


def test_unsigned_treaty_not_active():
    s = PlayerTreatySystem()
    _propose(s)
    assert s.is_active_between(
        player_a="naji", player_b="volker",
    ) is False


def test_unrelated_pair_not_active():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    assert s.is_active_between(
        player_a="naji", player_b="cara",
    ) is False


def test_break_treaty_returns_penalty():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    penalty = s.break_treaty(
        treaty_id=tid, breaker_id="volker",
    )
    assert penalty == 50


def test_break_treaty_state_set():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    s.break_treaty(
        treaty_id=tid, breaker_id="volker",
    )
    t = s.treaty(treaty_id=tid)
    assert t.state == TreatyState.BROKEN
    assert t.breaker_id == "volker"


def test_break_third_party_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    assert s.break_treaty(
        treaty_id=tid, breaker_id="cara",
    ) is None


def test_break_unsigned_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s)
    assert s.break_treaty(
        treaty_id=tid, breaker_id="volker",
    ) is None


def test_expire_after_term():
    s = PlayerTreatySystem()
    tid = _propose(s, day=10)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    # default term 90 days from sign — expires day 102
    assert s.expire(
        treaty_id=tid, current_day=110,
    ) is True


def test_expire_before_term_blocked():
    s = PlayerTreatySystem()
    tid = _propose(s, day=10)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    assert s.expire(
        treaty_id=tid, current_day=50,
    ) is False


def test_expired_no_longer_active():
    s = PlayerTreatySystem()
    tid = _propose(s, day=10)
    s.sign(
        treaty_id=tid, signer_id="volker",
        signed_day=12,
    )
    s.expire(treaty_id=tid, current_day=110)
    assert s.is_active_between(
        player_a="naji", player_b="volker",
    ) is False


def test_treaties_of_player():
    s = PlayerTreatySystem()
    _propose(
        s, proposer="naji", accepter="volker", day=10,
    )
    _propose(
        s, proposer="naji", accepter="cara", day=11,
    )
    _propose(
        s, proposer="bob", accepter="dave", day=12,
    )
    treaties = s.treaties_of(player_id="naji")
    assert len(treaties) == 2


def test_unknown_treaty():
    s = PlayerTreatySystem()
    assert s.treaty(treaty_id="ghost") is None


def test_enum_counts():
    assert len(list(TreatyState)) == 4
    assert len(list(TreatyTerm)) == 4
