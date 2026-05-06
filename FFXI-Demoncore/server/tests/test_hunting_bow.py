"""Tests for hunting_bow."""
from __future__ import annotations

from server.hunting_bow import (
    ArrowHead, BowKind, HuntingBowRegistry,
)


def test_craft_happy():
    r = HuntingBowRegistry()
    ok = r.craft(
        bow_id="b1", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    assert ok is True


def test_craft_blank_id_blocked():
    r = HuntingBowRegistry()
    out = r.craft(
        bow_id="", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    assert out is False


def test_craft_blank_owner_blocked():
    r = HuntingBowRegistry()
    out = r.craft(
        bow_id="b", owner_id="",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    assert out is False


def test_craft_duplicate_blocked():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    out = r.craft(
        bow_id="b", owner_id="bob",
        kind=BowKind.GREATBOW, crafted_at=20,
    )
    assert out is False


def test_optimal_draw_full_damage():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    # LONGBOW base 35, broadhead 1.0, draw=3 (optimal), AC=0,
    # pierce=5 → dmg=35-(-5 floored to 0)=35
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=3, target_armor_class=0,
    )
    assert out.damage == 35


def test_underdrawn_halves_damage():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    # min_draw=2, draw=1 → 0.5 factor
    # 35 * 1.0 * 0.5 = 17, AC 0, pierce 5 → 17
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=1, target_armor_class=0,
    )
    assert out.damage == 17


def test_overdrawn_falls_off():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    # optimal=3, max=5, draw=5 → factor 0.6
    # 35 * 1.0 * 0.6 = 21
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=5, target_armor_class=0,
    )
    assert out.damage == 21


def test_way_overdrawn_minimal():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=10,
    )
    # past max_useful → 0.4 factor
    # 35 * 0.4 = 14
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=20, target_armor_class=0,
    )
    assert out.damage == 14


def test_armor_blocks_damage():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    # SHORT_BOW base 20, broadhead 1.0, draw=2 optimal,
    # pierce=0, AC=15 → dmg = 20 - 15 = 5
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=2, target_armor_class=15,
    )
    assert out.damage == 5


def test_bodkin_pierces_armor():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    # SHORT_BOW base 20, bodkin 1.1 = 22, pierce 15, AC 15 → 0
    # → dmg = 22 - 0 = 22
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BODKIN,
        draw_seconds=2, target_armor_class=15,
    )
    assert out.damage == 22


def test_blunt_lower_damage():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    # blunt 0.7 → 14
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BLUNT,
        draw_seconds=2, target_armor_class=0,
    )
    assert out.damage == 14


def test_min_damage_floor():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    # huge AC should still leave min 1 damage
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BLUNT,
        draw_seconds=2, target_armor_class=999,
    )
    assert out.damage == 1


def test_broadhead_ruins_small_hide():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=2, target_armor_class=0,
        target_is_small=True,
    )
    assert out.ruined_hide is True


def test_blunt_preserves_hide():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BLUNT,
        draw_seconds=2, target_armor_class=0,
        target_is_small=True,
    )
    assert out.ruined_hide is False


def test_barbed_breaks():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BARBED,
        draw_seconds=2, target_armor_class=0,
    )
    assert out.broke_arrow is True


def test_broadhead_doesnt_break():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    out = r.resolve_shot(
        bow_id="b", arrow=ArrowHead.BROADHEAD,
        draw_seconds=2, target_armor_class=0,
    )
    assert out.broke_arrow is False


def test_unknown_bow_returns_none():
    r = HuntingBowRegistry()
    out = r.resolve_shot(
        bow_id="ghost", arrow=ArrowHead.BROADHEAD,
        draw_seconds=2, target_armor_class=0,
    )
    assert out is None


def test_profile_for():
    r = HuntingBowRegistry()
    p = r.profile_for(kind=BowKind.GREATBOW)
    assert p.base_damage == 80
    assert p.optimal_draw == 6


def test_get_unknown():
    r = HuntingBowRegistry()
    assert r.get(bow_id="ghost") is None


def test_four_bow_kinds():
    assert len(list(BowKind)) == 4


def test_five_arrow_heads():
    assert len(list(ArrowHead)) == 5


def test_total_bows():
    r = HuntingBowRegistry()
    r.craft(
        bow_id="a", owner_id="alice",
        kind=BowKind.SHORT_BOW, crafted_at=10,
    )
    r.craft(
        bow_id="b", owner_id="alice",
        kind=BowKind.LONGBOW, crafted_at=20,
    )
    assert r.total_bows() == 2
