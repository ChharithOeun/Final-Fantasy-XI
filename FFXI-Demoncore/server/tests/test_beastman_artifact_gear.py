"""Tests for the beastman artifact gear ladders."""
from __future__ import annotations

from server.beastman_artifact_gear import (
    BeastmanArtifactGear,
    GearLadder,
    GearSlotKind,
)
from server.beastman_job_availability import JobCode
from server.beastman_playable_races import BeastmanRace


def _seed_yagudo_whm_af(g: BeastmanArtifactGear):
    return g.register_item(
        item_id="yag_whm_af_robe",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.AF,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="cleric_robe",
        label="Yagudo Cleric Robe",
    )


def test_register_item():
    g = BeastmanArtifactGear()
    item = _seed_yagudo_whm_af(g)
    assert item is not None


def test_register_double_id_rejected():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    res = g.register_item(
        item_id="yag_whm_af_robe",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.AF,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="x",
        label="x",
    )
    assert res is None


def test_register_empty_label_rejected():
    g = BeastmanArtifactGear()
    res = g.register_item(
        item_id="x",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.AF,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="y",
        label="",
    )
    assert res is None


def test_register_mythic_must_be_weapon():
    g = BeastmanArtifactGear()
    res = g.register_item(
        item_id="x",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.MYTHIC,
        slot=GearSlotKind.HEAD,
        canon_equivalent_item_id="y",
        label="y",
    )
    assert res is None


def test_register_ultimate_must_be_weapon():
    g = BeastmanArtifactGear()
    res = g.register_item(
        item_id="x",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.ULTIMATE,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="y",
        label="y",
    )
    assert res is None


def test_register_mythic_weapon_succeeds():
    g = BeastmanArtifactGear()
    res = g.register_item(
        item_id="yag_whm_mythic",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.MYTHIC,
        slot=GearSlotKind.WEAPON_MAIN,
        canon_equivalent_item_id="yagrush",
        label="Yagudo Mythic Cudgel",
    )
    assert res is not None


def test_unlock_af_first():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    assert res.accepted


def test_unlock_unknown_item():
    g = BeastmanArtifactGear()
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="ghost",
    )
    assert not res.accepted


def test_unlock_race_mismatch():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.ORC,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    assert not res.accepted


def test_unlock_job_mismatch():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.SAM,
        item_id="yag_whm_af_robe",
    )
    assert not res.accepted


def test_unlock_relic_without_af_rejected():
    g = BeastmanArtifactGear()
    g.register_item(
        item_id="relic_robe",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.RELIC,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="dynamis_robe",
        label="Dynamic robe",
    )
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="relic_robe",
    )
    assert not res.accepted
    assert "prior ladder" in res.reason


def test_unlock_relic_with_af_succeeds():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.register_item(
        item_id="relic_robe",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.RELIC,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="dynamis_robe",
        label="Dynamic robe",
    )
    g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="relic_robe",
    )
    assert res.accepted


def test_unlock_double_rejected():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    res = g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    assert not res.accepted


def test_ladder_for_sorts_by_tier():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.register_item(
        item_id="relic_robe",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        ladder=GearLadder.RELIC,
        slot=GearSlotKind.BODY,
        canon_equivalent_item_id="x",
        label="x",
    )
    rows = g.ladder_for(
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )
    assert rows[0].ladder == GearLadder.AF
    assert rows[1].ladder == GearLadder.RELIC


def test_next_ladder_for_new_player():
    g = BeastmanArtifactGear()
    nl = g.next_ladder_for_player(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )
    assert nl == GearLadder.AF


def test_next_ladder_after_af():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    nl = g.next_ladder_for_player(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )
    assert nl == GearLadder.RELIC


def test_next_ladder_at_top():
    g = BeastmanArtifactGear()
    # Walk up the ladder fully
    items = [
        ("af", GearLadder.AF, GearSlotKind.BODY),
        ("relic", GearLadder.RELIC, GearSlotKind.BODY),
        ("empy", GearLadder.EMPYREAN, GearSlotKind.BODY),
        (
            "mythic", GearLadder.MYTHIC,
            GearSlotKind.WEAPON_MAIN,
        ),
        (
            "ult", GearLadder.ULTIMATE,
            GearSlotKind.WEAPON_MAIN,
        ),
    ]
    for iid, lad, sl in items:
        g.register_item(
            item_id=iid,
            race=BeastmanRace.YAGUDO,
            job=JobCode.WHM,
            ladder=lad, slot=sl,
            canon_equivalent_item_id="x",
            label="x",
        )
        g.unlock(
            player_id="alice",
            race=BeastmanRace.YAGUDO,
            job=JobCode.WHM,
            item_id=iid,
        )
    nl = g.next_ladder_for_player(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )
    assert nl is None


def test_canon_equiv_propagates():
    g = BeastmanArtifactGear()
    item = _seed_yagudo_whm_af(g)
    assert item.canon_equivalent_item_id == "cleric_robe"


def test_per_player_isolation():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.unlock(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
        item_id="yag_whm_af_robe",
    )
    bob_unlocks = g.unlocked_for(
        player_id="bob",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )
    assert bob_unlocks == ()


def test_total_items():
    g = BeastmanArtifactGear()
    _seed_yagudo_whm_af(g)
    g.register_item(
        item_id="orc_war_af",
        race=BeastmanRace.ORC,
        job=JobCode.WAR,
        ladder=GearLadder.AF,
        slot=GearSlotKind.WEAPON_MAIN,
        canon_equivalent_item_id="warrior_axe",
        label="Orc Warrior Axe",
    )
    assert g.total_items() == 2
