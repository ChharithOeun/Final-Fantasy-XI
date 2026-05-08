"""Tests for courtship_system."""
from __future__ import annotations

from server.courtship_system import (
    CourtshipSystem, Stage,
)


def _ready_to_propose(c, a="bob", b="cara"):
    """Push state to all-requirements-met."""
    c.declare_dating(player_a=a, player_b=b)
    for _ in range(7):
        c.record_gift(from_player=a, to_player=b)
        c.record_gift(from_player=b, to_player=a)
    for _ in range(5):
        c.record_date(player_a=a, player_b=b)
    c.set_mutual_confidant(player_a=a, player_b=b)


def test_declare_dating():
    c = CourtshipSystem()
    assert c.declare_dating(
        player_a="bob", player_b="cara",
    ) is True
    assert c.stage(
        player_a="bob", player_b="cara",
    ) == Stage.DATING


def test_declare_dating_blank_blocked():
    c = CourtshipSystem()
    assert c.declare_dating(
        player_a="", player_b="cara",
    ) is False


def test_declare_dating_self_blocked():
    c = CourtshipSystem()
    assert c.declare_dating(
        player_a="bob", player_b="bob",
    ) is False


def test_declare_dating_dup_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    assert c.declare_dating(
        player_a="bob", player_b="cara",
    ) is False


def test_record_gift():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    assert c.record_gift(
        from_player="bob", to_player="cara",
    ) is True


def test_record_gift_unknown_courtship():
    c = CourtshipSystem()
    assert c.record_gift(
        from_player="bob", to_player="cara",
    ) is False


def test_record_date():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    assert c.record_date(
        player_a="bob", player_b="cara",
    ) is True
    p = c.progress(player_a="bob", player_b="cara")
    assert p.dates_completed == 1


def test_set_mutual_confidant_first_call():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    assert c.set_mutual_confidant(
        player_a="bob", player_b="cara",
    ) is True


def test_set_mutual_confidant_dup_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    c.set_mutual_confidant(player_a="bob", player_b="cara")
    assert c.set_mutual_confidant(
        player_a="bob", player_b="cara",
    ) is False


def test_propose_short_gifts_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    for _ in range(5):
        c.record_gift(from_player="bob", to_player="cara")
        c.record_gift(from_player="cara", to_player="bob")
    for _ in range(5):
        c.record_date(player_a="bob", player_b="cara")
    c.set_mutual_confidant(player_a="bob", player_b="cara")
    assert c.propose(
        proposer="bob", accepter="cara",
    ) is False


def test_propose_short_dates_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    for _ in range(7):
        c.record_gift(from_player="bob", to_player="cara")
        c.record_gift(from_player="cara", to_player="bob")
    for _ in range(2):
        c.record_date(player_a="bob", player_b="cara")
    c.set_mutual_confidant(player_a="bob", player_b="cara")
    assert c.propose(
        proposer="bob", accepter="cara",
    ) is False


def test_propose_no_confidant_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    for _ in range(7):
        c.record_gift(from_player="bob", to_player="cara")
        c.record_gift(from_player="cara", to_player="bob")
    for _ in range(5):
        c.record_date(player_a="bob", player_b="cara")
    # mutual_confidant NOT set
    assert c.propose(
        proposer="bob", accepter="cara",
    ) is False


def test_propose_all_requirements_met():
    c = CourtshipSystem()
    _ready_to_propose(c)
    assert c.propose(
        proposer="bob", accepter="cara",
    ) is True
    assert c.stage(
        player_a="bob", player_b="cara",
    ) == Stage.ENGAGED


def test_propose_already_engaged_blocked():
    c = CourtshipSystem()
    _ready_to_propose(c)
    c.propose(proposer="bob", accepter="cara")
    assert c.propose(
        proposer="bob", accepter="cara",
    ) is False


def test_break_off_dating():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    assert c.break_off(
        by_player="bob", other="cara",
    ) is True
    assert c.stage(
        player_a="bob", player_b="cara",
    ) == Stage.BROKEN_OFF


def test_break_off_engaged():
    c = CourtshipSystem()
    _ready_to_propose(c)
    c.propose(proposer="bob", accepter="cara")
    assert c.break_off(
        by_player="cara", other="bob",
    ) is True


def test_break_off_no_courtship():
    c = CourtshipSystem()
    assert c.break_off(
        by_player="bob", other="cara",
    ) is False


def test_re_date_after_break_off():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    c.break_off(by_player="bob", other="cara")
    assert c.declare_dating(
        player_a="bob", player_b="cara",
    ) is True
    # Fresh state
    p = c.progress(player_a="bob", player_b="cara")
    assert p.dates_completed == 0


def test_record_gift_after_breakoff_blocked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    c.break_off(by_player="bob", other="cara")
    assert c.record_gift(
        from_player="bob", to_player="cara",
    ) is False


def test_progress_unknown():
    c = CourtshipSystem()
    assert c.progress(
        player_a="bob", player_b="cara",
    ) is None


def test_record_gift_direction_tracked():
    c = CourtshipSystem()
    c.declare_dating(player_a="bob", player_b="cara")
    c.record_gift(from_player="bob", to_player="cara")
    c.record_gift(from_player="bob", to_player="cara")
    p = c.progress(player_a="bob", player_b="cara")
    # bob is sorted alphabetically before cara, so a->b
    # is bob->cara
    assert p.gifts_a_to_b == 2
    assert p.gifts_b_to_a == 0


def test_four_stages():
    assert len(list(Stage)) == 4
