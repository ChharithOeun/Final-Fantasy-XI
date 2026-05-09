"""Tests for entity_rivalry."""
from __future__ import annotations

from server.entity_rivalry import (
    EntityRivalrySystem, RivalryState,
)


def _decl(s: EntityRivalrySystem) -> str:
    return s.declare_rivalry(
        entity_a="goblin_smithy",
        entity_b="mythril_madame",
        description="Forge supremacy in Mythril Mines",
    )


def test_declare_happy():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert rid is not None


def test_declare_self_blocked():
    s = EntityRivalrySystem()
    assert s.declare_rivalry(
        entity_a="x", entity_b="x", description="d",
    ) is None


def test_declare_empty_description_blocked():
    s = EntityRivalrySystem()
    assert s.declare_rivalry(
        entity_a="a", entity_b="b", description="",
    ) is None


def test_declare_dup_blocked():
    s = EntityRivalrySystem()
    _decl(s)
    # Either order
    assert s.declare_rivalry(
        entity_a="mythril_madame",
        entity_b="goblin_smithy",
        description="other",
    ) is None


def test_starts_simmering():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.rivalry(
        rivalry_id=rid,
    ).state == RivalryState.SIMMERING


def test_record_incident_increments():
    s = EntityRivalrySystem()
    _decl(s)
    s.record_incident(
        entity_a="goblin_smithy",
        entity_b="mythril_madame",
    )
    assert s.rivalry(
        rivalry_id="rivalry_1",
    ).incidents_count == 1


def test_escalates_to_feuding_at_5():
    s = EntityRivalrySystem()
    rid = _decl(s)
    for _ in range(5):
        s.record_incident(
            entity_a="goblin_smithy",
            entity_b="mythril_madame",
        )
    assert s.rivalry(
        rivalry_id=rid,
    ).state == RivalryState.FEUDING


def test_record_undeclared_blocked():
    s = EntityRivalrySystem()
    assert s.record_incident(
        entity_a="a", entity_b="b",
    ) is False


def test_take_side_with_a():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="goblin_smithy",
    ) is True


def test_take_side_with_b():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="mythril_madame",
    ) is True


def test_take_side_with_third_party_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="cara",
    ) is False


def test_take_side_self_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    # Goblin Smithy can't side with himself
    assert s.take_side(
        rivalry_id=rid, supporter_id="goblin_smithy",
        side_with="mythril_madame",
    ) is False


def test_take_side_double_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="goblin_smithy",
    )
    # Can't side again with the other side
    assert s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="mythril_madame",
    ) is False


def test_supporter_recorded():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="goblin_smithy",
    )
    r = s.rivalry(rivalry_id=rid)
    assert "naji" in r.a_supporters


def test_reconcile_returns_honor_gain():
    s = EntityRivalrySystem()
    rid = _decl(s)
    gain = s.reconcile(rivalry_id=rid)
    assert gain == 25


def test_reconcile_state_set():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.reconcile(rivalry_id=rid)
    r = s.rivalry(rivalry_id=rid)
    assert r.state == RivalryState.RESOLVED
    assert r.resolution == "reconciled"


def test_reconcile_already_resolved_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.reconcile(rivalry_id=rid)
    assert s.reconcile(rivalry_id=rid) is None


def test_settle_by_victory_a_won():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.settle_by_victory(
        rivalry_id=rid, victor_id="goblin_smithy",
    ) is True
    assert s.rivalry(
        rivalry_id=rid,
    ).resolution == "a_won"


def test_settle_by_victory_b_won():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.settle_by_victory(
        rivalry_id=rid, victor_id="mythril_madame",
    )
    assert s.rivalry(
        rivalry_id=rid,
    ).resolution == "b_won"


def test_settle_third_party_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    assert s.settle_by_victory(
        rivalry_id=rid, victor_id="naji",
    ) is False


def test_record_after_resolved_blocked():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.reconcile(rivalry_id=rid)
    assert s.record_incident(
        entity_a="goblin_smithy",
        entity_b="mythril_madame",
    ) is False


def test_rivalries_of_entity():
    s = EntityRivalrySystem()
    _decl(s)
    s.declare_rivalry(
        entity_a="goblin_smithy",
        entity_b="iron_eater",
        description="Smelting territory",
    )
    rivals = s.rivalries_of(
        entity_id="goblin_smithy",
    )
    assert len(rivals) == 2


def test_supporter_lookup():
    s = EntityRivalrySystem()
    rid = _decl(s)
    s.take_side(
        rivalry_id=rid, supporter_id="naji",
        side_with="goblin_smithy",
    )
    rivals = s.supporter_lookup(supporter_id="naji")
    assert len(rivals) == 1


def test_unknown_rivalry():
    s = EntityRivalrySystem()
    assert s.rivalry(rivalry_id="ghost") is None


def test_enum_count():
    assert len(list(RivalryState)) == 3
