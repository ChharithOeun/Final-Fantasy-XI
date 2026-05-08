"""Tests for family_lineage."""
from __future__ import annotations

from server.family_lineage import FamilyLineage


def test_register_founder():
    f = FamilyLineage()
    assert f.register_founder(
        player_id="bob", family_name="Stoneforge",
        home_city="bastok",
    ) is True
    assert f.generation(player_id="bob") == 1
    assert f.family_name(player_id="bob") == "Stoneforge"


def test_register_blank_blocked():
    f = FamilyLineage()
    assert f.register_founder(
        player_id="", family_name="x",
    ) is False


def test_register_blank_name_blocked():
    f = FamilyLineage()
    assert f.register_founder(
        player_id="bob", family_name="",
    ) is False


def test_register_dup_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    assert f.register_founder(
        player_id="bob", family_name="Whatever",
    ) is False


def test_designate_heir():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    assert f.designate_heir(
        parent="bob", heir_candidate="bob_jr",
    ) is True


def test_designate_heir_self_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    assert f.designate_heir(
        parent="bob", heir_candidate="bob",
    ) is False


def test_designate_heir_already_in_lineage_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.register_founder(
        player_id="cara", family_name="Other",
    )
    # Can't make Cara your heir — she's a founder elsewhere
    assert f.designate_heir(
        parent="bob", heir_candidate="cara",
    ) is False


def test_disinherit():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.designate_heir(
        parent="bob", heir_candidate="bob_jr",
    )
    assert f.disinherit(parent="bob") is True


def test_disinherit_no_heir_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    assert f.disinherit(parent="bob") is False


def test_record_death_creates_heir():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.designate_heir(
        parent="bob", heir_candidate="bob_jr",
    )
    f.record_death(parent="bob")
    assert f.generation(player_id="bob_jr") == 2
    assert f.family_name(
        player_id="bob_jr",
    ) == "Stoneforge"


def test_record_death_no_heir_line_ends():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    out = f.record_death(parent="bob")
    assert out is None
    # Bob is dead but no heir
    assert f.node(player_id="bob").is_alive is False


def test_record_death_with_heirloom():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.designate_heir(
        parent="bob", heir_candidate="bob_jr",
    )
    h = f.record_death(
        parent="bob", heirloom_item_id="ancestral_sword",
    )
    assert h is not None
    assert h.to_heir == "bob_jr"
    assert h.item_id == "ancestral_sword"


def test_record_death_already_dead_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.record_death(parent="bob")
    assert f.record_death(parent="bob") is None


def test_designate_heir_after_death_blocked():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    f.record_death(parent="bob")
    assert f.designate_heir(
        parent="bob", heir_candidate="bob_jr",
    ) is False


def test_three_generation_chain():
    f = FamilyLineage()
    f.register_founder(
        player_id="g1", family_name="House",
    )
    f.designate_heir(parent="g1", heir_candidate="g2")
    f.record_death(parent="g1")
    f.designate_heir(parent="g2", heir_candidate="g3")
    f.record_death(parent="g2")
    assert f.generation(player_id="g3") == 3


def test_lineage_bonus_caps():
    f = FamilyLineage()
    f.register_founder(
        player_id="g1", family_name="House",
    )
    f.designate_heir(parent="g1", heir_candidate="g2")
    f.record_death(parent="g1")
    f.designate_heir(parent="g2", heir_candidate="g3")
    f.record_death(parent="g2")
    f.designate_heir(parent="g3", heir_candidate="g4")
    f.record_death(parent="g3")
    f.designate_heir(parent="g4", heir_candidate="g5")
    f.record_death(parent="g4")
    # G5 is generation 5; bonus caps at 3
    assert f.lineage_bonus(player_id="g5") == 3


def test_ancestors_chain():
    f = FamilyLineage()
    f.register_founder(
        player_id="g1", family_name="House",
    )
    f.designate_heir(parent="g1", heir_candidate="g2")
    f.record_death(parent="g1")
    f.designate_heir(parent="g2", heir_candidate="g3")
    f.record_death(parent="g2")
    ancestors = f.ancestors(player_id="g3")
    assert ancestors == ["g2", "g1"]


def test_ancestors_founder():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    assert f.ancestors(player_id="bob") == []


def test_lineage_known_in_home_city():
    f = FamilyLineage()
    f.register_founder(
        player_id="g1", family_name="House",
        home_city="bastok",
    )
    f.designate_heir(parent="g1", heir_candidate="g2")
    f.record_death(parent="g1")
    assert f.lineage_known(
        player_id="g2", city_id="bastok",
    ) is True


def test_lineage_unknown_other_city():
    f = FamilyLineage()
    f.register_founder(
        player_id="g1", family_name="House",
        home_city="bastok",
    )
    f.designate_heir(parent="g1", heir_candidate="g2")
    f.record_death(parent="g1")
    assert f.lineage_known(
        player_id="g2", city_id="sandy",
    ) is False


def test_lineage_unknown_for_founder():
    """Founder isn't 'known' yet — gen 1 = no famous line."""
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
        home_city="bastok",
    )
    assert f.lineage_known(
        player_id="bob", city_id="bastok",
    ) is False


def test_node_returns_full():
    f = FamilyLineage()
    f.register_founder(
        player_id="bob", family_name="Stoneforge",
    )
    n = f.node(player_id="bob")
    assert n.family_name == "Stoneforge"
    assert n.is_alive is True
    assert n.parent_id is None


def test_node_unknown():
    f = FamilyLineage()
    assert f.node(player_id="ghost") is None


def test_family_name_unknown():
    f = FamilyLineage()
    assert f.family_name(player_id="ghost") is None
