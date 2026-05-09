"""Tests for player_rivalry."""
from __future__ import annotations

from server.player_rivalry import (
    PlayerRivalrySystem, RivalryState,
    EncounterOutcome,
)


def test_declare_happy():
    s = PlayerRivalrySystem()
    assert s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    ) is not None


def test_declare_self_blocked():
    s = PlayerRivalrySystem()
    assert s.declare(
        challenger="x", target="x",
        proposed_day=10,
    ) is None


def test_declare_blank():
    s = PlayerRivalrySystem()
    assert s.declare(
        challenger="", target="naji",
        proposed_day=10,
    ) is None


def test_declare_dup_pair_blocked():
    s = PlayerRivalrySystem()
    s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    assert s.declare(
        challenger="bob", target="naji",
        proposed_day=11,
    ) is None


def test_declare_reverse_pair_blocked():
    s = PlayerRivalrySystem()
    s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    assert s.declare(
        challenger="naji", target="bob",
        proposed_day=11,
    ) is None


def test_accept():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    assert s.accept(
        rivalry_id=rid, now_day=11,
    ) is True


def test_accept_double_blocked():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    assert s.accept(
        rivalry_id=rid, now_day=12,
    ) is False


def test_accept_too_early():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    assert s.accept(
        rivalry_id=rid, now_day=5,
    ) is False


def test_record_encounter_happy():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    eid = s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.CHALLENGER_WIN,
        zone="ronfaure", occurred_day=12,
    )
    assert eid is not None
    r = s.rivalry(rivalry_id=rid)
    assert r.challenger_wins == 1


def test_record_when_proposed_blocked():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    eid = s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.CHALLENGER_WIN,
        zone="x", occurred_day=12,
    )
    assert eid is None


def test_record_blank_zone():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    eid = s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.CHALLENGER_WIN,
        zone="", occurred_day=12,
    )
    assert eid is None


def test_tally_aggregates():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    for _ in range(3):
        s.record_encounter(
            rivalry_id=rid,
            outcome=EncounterOutcome.CHALLENGER_WIN,
            zone="x", occurred_day=12,
        )
    for _ in range(2):
        s.record_encounter(
            rivalry_id=rid,
            outcome=EncounterOutcome.TARGET_WIN,
            zone="x", occurred_day=13,
        )
    s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.DRAW,
        zone="x", occurred_day=14,
    )
    r = s.rivalry(rivalry_id=rid)
    assert r.challenger_wins == 3
    assert r.target_wins == 2
    assert r.draws == 1


def test_settle():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    assert s.settle(
        rivalry_id=rid, now_day=100,
    ) is True


def test_settle_after_settle_blocked():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    s.settle(rivalry_id=rid, now_day=100)
    assert s.settle(
        rivalry_id=rid, now_day=101,
    ) is False


def test_end_by_permadeath():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    assert s.end_by_permadeath(
        rivalry_id=rid, now_day=200,
    ) is True


def test_dissolve():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    assert s.dissolve(
        rivalry_id=rid, now_day=12,
    ) is True


def test_record_after_settle_blocked():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    s.settle(rivalry_id=rid, now_day=100)
    eid = s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.CHALLENGER_WIN,
        zone="x", occurred_day=101,
    )
    assert eid is None


def test_declare_after_dissolve_ok():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.dissolve(rivalry_id=rid, now_day=15)
    new_rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=20,
    )
    assert new_rid is not None


def test_encounters_listed():
    s = PlayerRivalrySystem()
    rid = s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.accept(rivalry_id=rid, now_day=11)
    s.record_encounter(
        rivalry_id=rid,
        outcome=EncounterOutcome.CHALLENGER_WIN,
        zone="x", occurred_day=12,
    )
    out = s.encounters(rivalry_id=rid)
    assert len(out) == 1


def test_rivalries_for_player():
    s = PlayerRivalrySystem()
    s.declare(
        challenger="bob", target="naji",
        proposed_day=10,
    )
    s.declare(
        challenger="cara", target="bob",
        proposed_day=11,
    )
    s.declare(
        challenger="dave", target="ed",
        proposed_day=12,
    )
    out = s.rivalries_for(player_id="bob")
    assert len(out) == 2


def test_rivalry_unknown():
    s = PlayerRivalrySystem()
    assert s.rivalry(
        rivalry_id="ghost",
    ) is None


def test_enum_counts():
    assert len(list(RivalryState)) == 5
    assert len(list(EncounterOutcome)) == 3
