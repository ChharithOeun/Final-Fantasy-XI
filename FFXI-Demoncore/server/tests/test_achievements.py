"""Tests for the achievements board."""
from __future__ import annotations

import pytest

from server.achievements import (
    Achievement,
    AchievementBoard,
    AchievementType,
    ClaimResult,
)


# -- basic claim acceptance -------------------------------------------

def test_first_claim_accepted():
    board = AchievementBoard(world_id="alpha")
    res = board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="alice",
        timestamp=1000,
    )
    assert res.accepted is True
    assert res.achievement is not None
    assert res.achievement.player_id == "alice"
    assert res.reason is None


def test_repeatable_claim_allows_multiple_holders():
    board = AchievementBoard(world_id="alpha")
    res_a = board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior",
        player_id="alice",
        timestamp=1000,
    )
    res_b = board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior",
        player_id="bob",
        timestamp=2000,
    )
    assert res_a.accepted is True
    assert res_b.accepted is True
    assert board.count() == 2


def test_metadata_round_trips():
    board = AchievementBoard(world_id="alpha")
    res = board.claim(
        type=AchievementType.MYTHOLOGICAL_TROPHY,
        key="alice_fomor",
        player_id="bob",
        timestamp=42,
        metadata={"trophy_name": "Mythril Fang", "rarity": "unique"},
    )
    assert res.accepted
    assert res.achievement.metadata["trophy_name"] == "Mythril Fang"


# -- uniqueness rules -------------------------------------------------

def test_server_first_kill_only_one_winner():
    board = AchievementBoard(world_id="alpha")
    first = board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="alice",
        timestamp=1000,
    )
    second = board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="bob",
        timestamp=1500,
    )
    assert first.accepted is True
    assert second.accepted is False
    assert "alice" in (second.reason or "")


def test_server_first_kill_different_key_is_separate():
    board = AchievementBoard(world_id="alpha")
    a = board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="alice",
        timestamp=1000,
    )
    b = board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="nidhogg",
        player_id="bob",
        timestamp=1100,
    )
    assert a.accepted is True
    assert b.accepted is True


def test_server_first_genkai_unique():
    board = AchievementBoard(world_id="alpha")
    a = board.claim(
        type=AchievementType.SERVER_FIRST_GENKAI,
        key="genkai_5",
        player_id="alice",
        timestamp=1000,
    )
    b = board.claim(
        type=AchievementType.SERVER_FIRST_GENKAI,
        key="genkai_5",
        player_id="bob",
        timestamp=1500,
    )
    assert a.accepted
    assert not b.accepted


# -- input validation -------------------------------------------------

def test_empty_key_rejected():
    board = AchievementBoard(world_id="alpha")
    res = board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="",
        player_id="alice",
        timestamp=1,
    )
    assert res.accepted is False
    assert res.reason == "empty key"


def test_empty_player_id_rejected():
    board = AchievementBoard(world_id="alpha")
    res = board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior",
        player_id="",
        timestamp=1,
    )
    assert res.accepted is False
    assert res.reason == "empty player_id"


# -- read helpers -----------------------------------------------------

def test_has_with_player_filter():
    board = AchievementBoard(world_id="alpha")
    board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior",
        player_id="alice",
        timestamp=1,
    )
    assert board.has(
        type=AchievementType.JOB_MASTERY_5, key="warrior",
        player_id="alice",
    )
    assert not board.has(
        type=AchievementType.JOB_MASTERY_5, key="warrior",
        player_id="bob",
    )


def test_has_without_player_returns_any():
    board = AchievementBoard(world_id="alpha")
    board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="alice",
        timestamp=1,
    )
    assert board.has(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
    )
    assert not board.has(
        type=AchievementType.SERVER_FIRST_KILL, key="nidhogg",
    )


def test_holders_returns_distinct_players_in_claim_order():
    board = AchievementBoard(world_id="alpha")
    for ts, who, key in [
        (1, "alice", "warrior"),
        (2, "bob", "monk"),
        (3, "alice", "thief"),     # alice already in list
        (4, "carol", "white_mage"),
    ]:
        board.claim(
            type=AchievementType.JOB_MASTERY_5,
            key=key,
            player_id=who,
            timestamp=ts,
        )
    assert board.holders(AchievementType.JOB_MASTERY_5) == \
           ("alice", "bob", "carol")


def test_first_holder_unique_type():
    board = AchievementBoard(world_id="alpha")
    board.claim(
        type=AchievementType.SERVER_FIRST_KILL,
        key="fafnir",
        player_id="alice",
        timestamp=1000,
    )
    fh = board.first_holder(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
    )
    assert fh is not None
    assert fh.player_id == "alice"


def test_first_holder_repeatable_returns_earliest_timestamp():
    """For repeatable types, first_holder picks the earliest by
    timestamp, not by claim order."""
    board = AchievementBoard(world_id="alpha")
    # Bob claims first chronologically (ts=1) but alice claims earlier
    # in insertion order (ts=2). Earliest timestamp wins.
    board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior", player_id="alice", timestamp=2,
    )
    board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior", player_id="bob", timestamp=1,
    )
    fh = board.first_holder(
        type=AchievementType.JOB_MASTERY_5, key="warrior",
    )
    assert fh is not None
    assert fh.player_id == "bob"


def test_first_holder_missing_returns_none():
    board = AchievementBoard(world_id="alpha")
    assert board.first_holder(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
    ) is None


def test_achievements_of_returns_player_entries_in_order():
    board = AchievementBoard(world_id="alpha")
    board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="warrior", player_id="alice", timestamp=1,
    )
    board.claim(
        type=AchievementType.JOB_MASTERY_5,
        key="monk", player_id="bob", timestamp=2,
    )
    board.claim(
        type=AchievementType.PERSONAL_GENKAI,
        key="genkai_5", player_id="alice", timestamp=3,
    )
    a_ach = board.achievements_of("alice")
    assert len(a_ach) == 2
    assert {a.key for a in a_ach} == {"warrior", "genkai_5"}


def test_achievements_of_empty_for_unknown_player():
    board = AchievementBoard(world_id="alpha")
    assert board.achievements_of("nobody") == ()


def test_count_and_all_entries_in_sync():
    board = AchievementBoard(world_id="alpha")
    for i in range(5):
        board.claim(
            type=AchievementType.MYTHOLOGICAL_TROPHY,
            key=f"fomor_{i}", player_id="alice", timestamp=i,
        )
    assert board.count() == 5
    assert len(board.all_entries()) == 5


# -- composition ------------------------------------------------------

def test_full_lifecycle_demoncore_player_journey():
    """Alice's journey through the achievement system:
    masters WAR (lvl), clears Genkai 5, kills server-first Fafnir,
    later her own +5 fomor mythological-trophies a kill on bob."""
    board = AchievementBoard(world_id="alpha")

    r1 = board.claim(
        type=AchievementType.JOB_MASTERY_5, key="warrior",
        player_id="alice", timestamp=100,
    )
    r2 = board.claim(
        type=AchievementType.PERSONAL_GENKAI, key="genkai_5",
        player_id="alice", timestamp=200,
    )
    r3 = board.claim(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
        player_id="alice", timestamp=300,
    )
    r4 = board.claim(
        type=AchievementType.FOMOR_PLUS_FIVE, key="alice_fomor",
        player_id="alice", timestamp=400,
    )
    # Bob's fomor (alice's own kill came back) drops a trophy on bob.
    r5 = board.claim(
        type=AchievementType.MYTHOLOGICAL_TROPHY, key="alice_fomor",
        player_id="bob", timestamp=500,
        metadata={"trophy": "Phantom Tabard"},
    )

    assert all(r.accepted for r in (r1, r2, r3, r4, r5))
    # Alice has 4 claims; bob has 1.
    assert len(board.achievements_of("alice")) == 4
    assert len(board.achievements_of("bob")) == 1
    # Alice owns the world-first Fafnir.
    fh = board.first_holder(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
    )
    assert fh.player_id == "alice"
    # World cannot have a second Fafnir world-first.
    contender = board.claim(
        type=AchievementType.SERVER_FIRST_KILL, key="fafnir",
        player_id="carol", timestamp=999,
    )
    assert not contender.accepted
