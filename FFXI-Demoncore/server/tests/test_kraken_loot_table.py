"""Tests for kraken loot table."""
from __future__ import annotations

from server.kraken_loot_table import KrakenLootTable, KrakenLootTier
from server.kraken_world_boss import KrakenPhase


def test_record_damage_happy():
    t = KrakenLootTable()
    ok = t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.SUBMERGED,
        dmg=1_000,
    )
    assert ok is True
    assert t.damage_for(
        party_id="alpha", phase=KrakenPhase.SUBMERGED,
    ) == 1_000


def test_record_damage_accumulates():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha", phase=KrakenPhase.INK_CLOUD, dmg=100,
    )
    t.record_phase_damage(
        party_id="alpha", phase=KrakenPhase.INK_CLOUD, dmg=250,
    )
    assert t.damage_for(
        party_id="alpha", phase=KrakenPhase.INK_CLOUD,
    ) == 350


def test_record_rejects_blank_party():
    t = KrakenLootTable()
    ok = t.record_phase_damage(
        party_id="", phase=KrakenPhase.SUBMERGED, dmg=10,
    )
    assert ok is False


def test_record_rejects_zero_dmg():
    t = KrakenLootTable()
    ok = t.record_phase_damage(
        party_id="x", phase=KrakenPhase.SUBMERGED, dmg=0,
    )
    assert ok is False


def test_distribution_empty():
    t = KrakenLootTable()
    assert t.resolve_distribution() == ()


def test_fragment_for_every_contributing_party():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.SUBMERGED, dmg=100,
    )
    t.record_phase_damage(
        party_id="beta",
        phase=KrakenPhase.SUBMERGED, dmg=200,
    )
    drops = t.resolve_distribution()
    fragments = [
        d for d in drops
        if d.tier == KrakenLootTier.ABYSSAL_FRAGMENT
    ]
    party_ids = {d.party_id for d in fragments}
    assert party_ids == {"alpha", "beta"}


def test_kraken_ink_to_top_ink_cloud_party():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.INK_CLOUD, dmg=100,
    )
    t.record_phase_damage(
        party_id="beta",
        phase=KrakenPhase.INK_CLOUD, dmg=500,
    )
    drops = t.resolve_distribution()
    ink = next(
        d for d in drops if d.tier == KrakenLootTier.KRAKEN_INK
    )
    assert ink.party_id == "beta"


def test_hollow_pearl_to_top_enrage_deep_party():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.ENRAGE_DEEP, dmg=300,
    )
    t.record_phase_damage(
        party_id="beta",
        phase=KrakenPhase.ENRAGE_DEEP, dmg=200,
    )
    drops = t.resolve_distribution()
    pearl = next(
        d for d in drops if d.tier == KrakenLootTier.HOLLOW_PEARL
    )
    assert pearl.party_id == "alpha"


def test_drowned_crown_only_to_bleeding_god_party():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.SUBMERGED, dmg=10_000,
    )
    t.record_phase_damage(
        party_id="beta",
        phase=KrakenPhase.BLEEDING_GOD, dmg=5_000,
    )
    drops = t.resolve_distribution()
    crowns = [
        d for d in drops if d.tier == KrakenLootTier.DROWNED_CROWN
    ]
    assert len(crowns) == 1
    assert crowns[0].party_id == "beta"


def test_no_crown_when_no_phase_4_damage():
    t = KrakenLootTable()
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.INK_CLOUD, dmg=1_000,
    )
    drops = t.resolve_distribution()
    crowns = [
        d for d in drops if d.tier == KrakenLootTier.DROWNED_CROWN
    ]
    assert len(crowns) == 0


def test_ink_falls_back_to_enrage_when_no_ink_cloud():
    t = KrakenLootTable()
    # only ENRAGE_DEEP recorded, no INK_CLOUD
    t.record_phase_damage(
        party_id="alpha",
        phase=KrakenPhase.ENRAGE_DEEP, dmg=500,
    )
    drops = t.resolve_distribution()
    ink = next(
        d for d in drops if d.tier == KrakenLootTier.KRAKEN_INK
    )
    assert ink.party_id == "alpha"


def test_single_party_clears_all_phases():
    t = KrakenLootTable()
    for phase in KrakenPhase:
        t.record_phase_damage(
            party_id="solo", phase=phase, dmg=1_000,
        )
    drops = t.resolve_distribution()
    tiers = {d.tier for d in drops}
    assert KrakenLootTier.ABYSSAL_FRAGMENT in tiers
    assert KrakenLootTier.KRAKEN_INK in tiers
    assert KrakenLootTier.HOLLOW_PEARL in tiers
    assert KrakenLootTier.DROWNED_CROWN in tiers


def test_damage_for_unknown_party_zero():
    t = KrakenLootTable()
    assert t.damage_for(
        party_id="ghost", phase=KrakenPhase.SUBMERGED,
    ) == 0
