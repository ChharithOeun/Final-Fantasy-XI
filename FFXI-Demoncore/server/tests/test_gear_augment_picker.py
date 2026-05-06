"""Tests for gear_augment_picker."""
from __future__ import annotations

from server.gear_augment_picker import (
    AugmentChoice, AugmentSchema, AugmentTier,
    GearAugmentPicker,
)


def _crocea_schema():
    return AugmentSchema(
        item_id="crocea_mors",
        legal_choices=(
            AugmentChoice(
                choice_id="path_a", tier=AugmentTier.PATH,
                canonical_string="Path: A",
            ),
            AugmentChoice(
                choice_id="path_b", tier=AugmentTier.PATH,
                canonical_string="Path: B",
            ),
            AugmentChoice(
                choice_id="path_c", tier=AugmentTier.PATH,
                canonical_string="Path: C",
            ),
        ),
        max_augment_count=0,
    )


def _cape_schema():
    """Mirrors a Sucellos's Cape with multiple stat picks."""
    return AugmentSchema(
        item_id="sucellos_cape",
        legal_choices=(
            AugmentChoice(
                choice_id="int10", tier=AugmentTier.STAT,
                canonical_string="INT+10",
            ),
            AugmentChoice(
                choice_id="mnd20", tier=AugmentTier.STAT,
                canonical_string="MND+20",
            ),
            AugmentChoice(
                choice_id="mab10", tier=AugmentTier.STAT,
                canonical_string='"Mag. Atk. Bns."+10',
            ),
            AugmentChoice(
                choice_id="dt10", tier=AugmentTier.SPECIAL,
                canonical_string="Phys. dmg. taken-10%",
            ),
        ),
        max_augment_count=5,
    )


def test_define_schema_happy():
    p = GearAugmentPicker()
    assert p.define_schema(schema=_crocea_schema()) is True


def test_define_blank_item_blocked():
    p = GearAugmentPicker()
    bad = AugmentSchema(
        item_id="", legal_choices=(
            AugmentChoice(choice_id="x", tier=AugmentTier.STAT,
                          canonical_string="INT+1"),
        ), max_augment_count=0,
    )
    assert p.define_schema(schema=bad) is False


def test_define_no_choices_blocked():
    p = GearAugmentPicker()
    bad = AugmentSchema(
        item_id="x", legal_choices=(), max_augment_count=0,
    )
    assert p.define_schema(schema=bad) is False


def test_define_duplicate_blocked():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    out = p.define_schema(schema=_crocea_schema())
    assert out is False


def test_define_duplicate_choice_id_blocked():
    p = GearAugmentPicker()
    bad = AugmentSchema(
        item_id="x",
        legal_choices=(
            AugmentChoice(choice_id="dup", tier=AugmentTier.STAT,
                          canonical_string="A"),
            AugmentChoice(choice_id="dup", tier=AugmentTier.STAT,
                          canonical_string="B"),
        ),
        max_augment_count=0,
    )
    assert p.define_schema(schema=bad) is False


def test_start_selection_known_item():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    assert sel is not None
    assert sel.selected == []


def test_start_selection_unknown():
    p = GearAugmentPicker()
    assert p.start_selection(item_id="ghost") is None


def test_toggle_path_picks_one():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    assert p.toggle(selection=sel, choice_id="path_c") is True
    assert sel.selected == ["path_c"]


def test_toggle_path_replaces_prior():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    p.toggle(selection=sel, choice_id="path_a")
    p.toggle(selection=sel, choice_id="path_c")
    # path_a removed, path_c selected
    assert sel.selected == ["path_c"]


def test_toggle_off_removes():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    p.toggle(selection=sel, choice_id="path_a")
    p.toggle(selection=sel, choice_id="path_a")
    assert sel.selected == []


def test_toggle_unknown_choice_blocked():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    assert p.toggle(selection=sel, choice_id="ghost") is False


def test_toggle_stats_stack():
    p = GearAugmentPicker()
    p.define_schema(schema=_cape_schema())
    sel = p.start_selection(item_id="sucellos_cape")
    p.toggle(selection=sel, choice_id="int10")
    p.toggle(selection=sel, choice_id="mnd20")
    p.toggle(selection=sel, choice_id="mab10")
    assert len(sel.selected) == 3


def test_max_augment_cap_enforced():
    """When cap is hit, additional adds refused."""
    schema = AugmentSchema(
        item_id="capped",
        legal_choices=(
            AugmentChoice(choice_id="a", tier=AugmentTier.STAT,
                          canonical_string="A"),
            AugmentChoice(choice_id="b", tier=AugmentTier.STAT,
                          canonical_string="B"),
            AugmentChoice(choice_id="c", tier=AugmentTier.STAT,
                          canonical_string="C"),
        ),
        max_augment_count=2,
    )
    p = GearAugmentPicker()
    p.define_schema(schema=schema)
    sel = p.start_selection(item_id="capped")
    p.toggle(selection=sel, choice_id="a")
    p.toggle(selection=sel, choice_id="b")
    out = p.toggle(selection=sel, choice_id="c")
    assert out is False
    assert sel.selected == ["a", "b"]


def test_render_returns_canonical_strings():
    p = GearAugmentPicker()
    p.define_schema(schema=_cape_schema())
    sel = p.start_selection(item_id="sucellos_cape")
    p.toggle(selection=sel, choice_id="int10")
    p.toggle(selection=sel, choice_id="mnd20")
    p.toggle(selection=sel, choice_id="dt10")
    out = p.render(selection=sel)
    assert out == ("INT+10", "MND+20", "Phys. dmg. taken-10%")


def test_render_preserves_selection_order():
    p = GearAugmentPicker()
    p.define_schema(schema=_cape_schema())
    sel = p.start_selection(item_id="sucellos_cape")
    p.toggle(selection=sel, choice_id="dt10")
    p.toggle(selection=sel, choice_id="int10")
    out = p.render(selection=sel)
    assert out == ("Phys. dmg. taken-10%", "INT+10")


def test_render_no_selections_empty():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    sel = p.start_selection(item_id="crocea_mors")
    assert p.render(selection=sel) == ()


def test_schema_for():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    s = p.schema_for(item_id="crocea_mors")
    assert s is not None
    assert len(s.legal_choices) == 3


def test_schema_for_unknown():
    p = GearAugmentPicker()
    assert p.schema_for(item_id="ghost") is None


def test_total_schemas():
    p = GearAugmentPicker()
    p.define_schema(schema=_crocea_schema())
    p.define_schema(schema=_cape_schema())
    assert p.total_schemas() == 2


def test_four_augment_tiers():
    assert len(list(AugmentTier)) == 4


def test_canonical_handles_quoted_strings():
    """Matches Tart's RDM.lua: '\"Mag. Atk. Bns.\"+10' style."""
    p = GearAugmentPicker()
    p.define_schema(schema=_cape_schema())
    sel = p.start_selection(item_id="sucellos_cape")
    p.toggle(selection=sel, choice_id="mab10")
    out = p.render(selection=sel)
    assert out == ('"Mag. Atk. Bns."+10',)
