"""Tests for landmark_naming."""
from __future__ import annotations

from server.landmark_naming import (
    LandmarkNamingRegistry,
    NamingOutcome,
    MAX_NAME_LENGTH,
)


def _setup():
    r = LandmarkNamingRegistry()
    r.register_discovery(
        landmark_id="cave_001", zone_id="ronfaure",
        discoverer_id="alice", discovered_at=10,
    )
    return r


def test_register_discovery_happy():
    r = _setup()
    assert r.name_for(landmark_id="cave_001") is None


def test_register_blank_blocked():
    r = LandmarkNamingRegistry()
    out = r.register_discovery(
        landmark_id="", zone_id="z",
        discoverer_id="a", discovered_at=10,
    )
    assert out is False


def test_duplicate_register_blocked():
    r = _setup()
    again = r.register_discovery(
        landmark_id="cave_001", zone_id="z2",
        discoverer_id="b", discovered_at=20,
    )
    assert again is False


def test_propose_name_happy():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001",
        proposed_name="The Hollow of Whispers",
        proposer_id="alice", proposed_at=20,
    )
    assert out == NamingOutcome.ACCEPTED
    assert r.name_for(landmark_id="cave_001") == (
        "The Hollow of Whispers"
    )


def test_propose_unknown_landmark():
    r = _setup()
    out = r.propose_name(
        landmark_id="ghost", proposed_name="X",
        proposer_id="alice", proposed_at=20,
    )
    assert out == NamingOutcome.REJECT_UNKNOWN_LANDMARK


def test_propose_blank_name():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001", proposed_name="   ",
        proposer_id="alice", proposed_at=20,
    )
    assert out == NamingOutcome.REJECT_BLANK


def test_propose_too_long():
    r = _setup()
    long_name = "x" * (MAX_NAME_LENGTH + 1)
    out = r.propose_name(
        landmark_id="cave_001", proposed_name=long_name,
        proposer_id="alice", proposed_at=20,
    )
    assert out == NamingOutcome.REJECT_TOO_LONG


def test_propose_profanity():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001",
        proposed_name="The BadWord Cave",
        proposer_id="alice", proposed_at=20,
        profanity_filter=["badword"],
    )
    assert out == NamingOutcome.REJECT_PROFANITY


def test_propose_profanity_case_insensitive():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001",
        proposed_name="BAD-things Hollow",
        proposer_id="alice", proposed_at=20,
        profanity_filter=["bad-things"],
    )
    assert out == NamingOutcome.REJECT_PROFANITY


def test_propose_not_discoverer():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001",
        proposed_name="Bob's Cave",
        proposer_id="bob", proposed_at=20,
    )
    assert out == NamingOutcome.REJECT_NOT_DISCOVERER


def test_propose_already_named():
    r = _setup()
    r.propose_name(
        landmark_id="cave_001", proposed_name="First Try",
        proposer_id="alice", proposed_at=20,
    )
    out = r.propose_name(
        landmark_id="cave_001", proposed_name="Second Try",
        proposer_id="alice", proposed_at=30,
    )
    assert out == NamingOutcome.REJECT_ALREADY_NAMED


def test_propose_duplicate_name():
    r = _setup()
    r.register_discovery(
        landmark_id="cave_002", zone_id="ronfaure",
        discoverer_id="bob", discovered_at=15,
    )
    r.propose_name(
        landmark_id="cave_001",
        proposed_name="The Hollow",
        proposer_id="alice", proposed_at=20,
    )
    out = r.propose_name(
        landmark_id="cave_002",
        proposed_name="THE HOLLOW",   # same after lower
        proposer_id="bob", proposed_at=25,
    )
    assert out == NamingOutcome.REJECT_DUPLICATE


def test_landmarks_named_by():
    r = _setup()
    r.register_discovery(
        landmark_id="cave_002", zone_id="z",
        discoverer_id="alice", discovered_at=15,
    )
    r.register_discovery(
        landmark_id="cave_003", zone_id="z",
        discoverer_id="bob", discovered_at=20,
    )
    r.propose_name(
        landmark_id="cave_001", proposed_name="A",
        proposer_id="alice", proposed_at=30,
    )
    r.propose_name(
        landmark_id="cave_002", proposed_name="B",
        proposer_id="alice", proposed_at=40,
    )
    out = r.landmarks_named_by(player_id="alice")
    assert len(out) == 2


def test_unnamed_landmarks_excluded():
    r = _setup()
    r.register_discovery(
        landmark_id="cave_002", zone_id="z",
        discoverer_id="alice", discovered_at=15,
    )
    # only cave_001 gets named
    r.propose_name(
        landmark_id="cave_001", proposed_name="A",
        proposer_id="alice", proposed_at=30,
    )
    out = r.landmarks_named_by(player_id="alice")
    assert len(out) == 1


def test_total_named():
    r = _setup()
    r.register_discovery(
        landmark_id="cave_002", zone_id="z",
        discoverer_id="alice", discovered_at=15,
    )
    r.propose_name(
        landmark_id="cave_001", proposed_name="A",
        proposer_id="alice", proposed_at=30,
    )
    assert r.total_named() == 1


def test_name_trimmed():
    r = _setup()
    r.propose_name(
        landmark_id="cave_001",
        proposed_name="  The Whispers  ",
        proposer_id="alice", proposed_at=20,
    )
    assert r.name_for(landmark_id="cave_001") == "The Whispers"


def test_empty_profanity_filter_ignored():
    r = _setup()
    out = r.propose_name(
        landmark_id="cave_001",
        proposed_name="Clean Name",
        proposer_id="alice", proposed_at=20,
        profanity_filter=["", " "],
    )
    assert out == NamingOutcome.ACCEPTED


def test_eight_outcome_kinds():
    assert len(list(NamingOutcome)) == 8
