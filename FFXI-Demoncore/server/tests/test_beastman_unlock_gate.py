"""Tests for the beastman unlock gate."""
from __future__ import annotations

from server.beastman_unlock_gate import BeastmanUnlockGate


def _seed(g: BeastmanUnlockGate):
    for x in ("base", "rotz", "cop", "toau", "wotg",
              "soa", "rov", "demoncore"):
        g.register_required_expansion(expansion_id=x)
    for q in (
        "shadowlands_proof_1",
        "shadowlands_proof_2",
        "shadowlands_proof_3",
    ):
        g.register_required_endgame_quest(quest_id=q)


def test_default_locked():
    g = BeastmanUnlockGate()
    _seed(g)
    res = g.is_unlocked(account_id="alice")
    assert not res.unlocked
    assert len(res.missing_expansion_msqs) == 8
    assert res.needs_level_99


def test_register_empty_expansion_rejected():
    g = BeastmanUnlockGate()
    assert not g.register_required_expansion(
        expansion_id="",
    )


def test_register_empty_quest_rejected():
    g = BeastmanUnlockGate()
    assert not g.register_required_endgame_quest(
        quest_id="",
    )


def test_register_double_expansion_rejected():
    g = BeastmanUnlockGate()
    g.register_required_expansion(expansion_id="rotz")
    assert not g.register_required_expansion(
        expansion_id="rotz",
    )


def test_register_double_quest_rejected():
    g = BeastmanUnlockGate()
    g.register_required_endgame_quest(quest_id="q1")
    assert not g.register_required_endgame_quest(
        quest_id="q1",
    )


def test_mark_msq_complete():
    g = BeastmanUnlockGate()
    _seed(g)
    assert g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="rotz",
    )


def test_mark_msq_double_returns_false():
    g = BeastmanUnlockGate()
    _seed(g)
    g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="rotz",
    )
    assert not g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="rotz",
    )


def test_mark_msq_empty_rejected():
    g = BeastmanUnlockGate()
    assert not g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="",
    )


def test_mark_endgame_quest_complete():
    g = BeastmanUnlockGate()
    _seed(g)
    assert g.mark_account_endgame_quest_complete(
        account_id="alice",
        quest_id="shadowlands_proof_1",
    )


def test_mark_endgame_double_returns_false():
    g = BeastmanUnlockGate()
    _seed(g)
    g.mark_account_endgame_quest_complete(
        account_id="alice",
        quest_id="shadowlands_proof_1",
    )
    assert not g.mark_account_endgame_quest_complete(
        account_id="alice",
        quest_id="shadowlands_proof_1",
    )


def test_mark_lvl99():
    g = BeastmanUnlockGate()
    _seed(g)
    assert g.mark_account_level_99(account_id="alice")
    assert not g.mark_account_level_99(
        account_id="alice",
    )


def test_full_unlock_sequence():
    g = BeastmanUnlockGate()
    _seed(g)
    for x in ("base", "rotz", "cop", "toau", "wotg",
              "soa", "rov", "demoncore"):
        g.mark_account_canon_msq_complete(
            account_id="alice", expansion_id=x,
        )
    for q in (
        "shadowlands_proof_1",
        "shadowlands_proof_2",
        "shadowlands_proof_3",
    ):
        g.mark_account_endgame_quest_complete(
            account_id="alice", quest_id=q,
        )
    g.mark_account_level_99(account_id="alice")
    res = g.is_unlocked(account_id="alice")
    assert res.unlocked
    assert res.missing_expansion_msqs == ()
    assert res.missing_endgame_quests == ()


def test_can_create_beastman_character():
    g = BeastmanUnlockGate()
    _seed(g)
    assert not g.can_create_beastman_character(
        account_id="alice",
    )


def test_partial_msq_still_locked():
    g = BeastmanUnlockGate()
    _seed(g)
    g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="rotz",
    )
    g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="cop",
    )
    res = g.is_unlocked(account_id="alice")
    assert not res.unlocked
    assert "base" in res.missing_expansion_msqs


def test_account_isolation():
    g = BeastmanUnlockGate()
    _seed(g)
    g.mark_account_canon_msq_complete(
        account_id="alice", expansion_id="rotz",
    )
    res_a = g.is_unlocked(account_id="alice")
    res_b = g.is_unlocked(account_id="bob")
    # Alice has 1 msq done, Bob has 0
    assert (
        len(res_a.missing_expansion_msqs)
        < len(res_b.missing_expansion_msqs)
    )


def test_unlocked_at_seconds_recorded():
    g = BeastmanUnlockGate()
    _seed(g)
    for x in ("base", "rotz", "cop", "toau", "wotg",
              "soa", "rov", "demoncore"):
        g.mark_account_canon_msq_complete(
            account_id="alice", expansion_id=x,
        )
    for q in (
        "shadowlands_proof_1",
        "shadowlands_proof_2",
        "shadowlands_proof_3",
    ):
        g.mark_account_endgame_quest_complete(
            account_id="alice", quest_id=q,
        )
    g.mark_account_level_99(account_id="alice")
    g.is_unlocked(
        account_id="alice", now_seconds=1234.0,
    )
    assert (
        g._states["alice"].unlocked_at_seconds == 1234.0
    )


def test_unlock_idempotent_timestamp():
    g = BeastmanUnlockGate()
    _seed(g)
    for x in ("base", "rotz", "cop", "toau", "wotg",
              "soa", "rov", "demoncore"):
        g.mark_account_canon_msq_complete(
            account_id="alice", expansion_id=x,
        )
    for q in (
        "shadowlands_proof_1",
        "shadowlands_proof_2",
        "shadowlands_proof_3",
    ):
        g.mark_account_endgame_quest_complete(
            account_id="alice", quest_id=q,
        )
    g.mark_account_level_99(account_id="alice")
    g.is_unlocked(
        account_id="alice", now_seconds=100.0,
    )
    # Second check shouldn't overwrite the timestamp
    g.is_unlocked(
        account_id="alice", now_seconds=2000.0,
    )
    assert (
        g._states["alice"].unlocked_at_seconds == 100.0
    )


def test_total_counts():
    g = BeastmanUnlockGate()
    _seed(g)
    assert g.total_required_expansions() == 8
    assert g.total_required_endgame_quests() == 3


def test_lvl99_only_no_msq_still_locked():
    g = BeastmanUnlockGate()
    _seed(g)
    g.mark_account_level_99(account_id="alice")
    res = g.is_unlocked(account_id="alice")
    assert not res.unlocked
