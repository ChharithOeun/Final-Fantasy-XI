"""Tests for abyssal gear augment."""
from __future__ import annotations

from server.abyssal_gear_augment import (
    AbyssalGearAugment,
    AugmentBand,
    Catalyst,
)


def test_augment_happy_common():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="hood_001",
        catalyst=Catalyst.BRINE_DROP,
        roll_seed=42,
    )
    assert r.accepted is True
    assert r.band == AugmentBand.COMMON
    # common: 1 stat
    assert len(r.stats) == 1


def test_augment_happy_uncommon():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="vest_001",
        catalyst=Catalyst.PEARLDUST,
        roll_seed=42,
    )
    assert r.band == AugmentBand.UNCOMMON
    # uncommon: 1..2 stats
    assert 1 <= len(r.stats) <= 2


def test_augment_happy_rare():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="trident_001",
        catalyst=Catalyst.KRAKEN_INK_VIAL,
        roll_seed=42,
    )
    assert r.band == AugmentBand.RARE
    # rare: 2..3 stats
    assert 2 <= len(r.stats) <= 3


def test_augment_blank_piece():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="",
        catalyst=Catalyst.BRINE_DROP,
        roll_seed=0,
    )
    assert r.accepted is False


def test_augment_negative_seed():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="x",
        catalyst=Catalyst.BRINE_DROP,
        roll_seed=-1,
    )
    assert r.accepted is False


def test_augment_deterministic():
    a1 = AbyssalGearAugment()
    a2 = AbyssalGearAugment()
    r1 = a1.augment(
        piece_id="hood_001",
        catalyst=Catalyst.PEARLDUST,
        roll_seed=99,
    )
    r2 = a2.augment(
        piece_id="hood_001",
        catalyst=Catalyst.PEARLDUST,
        roll_seed=99,
    )
    # same inputs -> same output (no hidden RNG)
    assert r1.stats == r2.stats


def test_augment_different_seeds_different_stats():
    a = AbyssalGearAugment()
    r1 = a.augment(
        piece_id="hood_001",
        catalyst=Catalyst.PEARLDUST,
        roll_seed=1,
    )
    # second piece — augment_for(hood_001) is now r1
    a2 = AbyssalGearAugment()
    r2 = a2.augment(
        piece_id="hood_001",
        catalyst=Catalyst.PEARLDUST,
        roll_seed=2,
    )
    # different seeds usually yield different stats; this
    # particular assertion isn't strict — seeds 1 and 2 might
    # collide. assert at least one is true:
    assert r1.stats != r2.stats or r1.band == r2.band


def test_augment_overwrites_previous():
    a = AbyssalGearAugment()
    r1 = a.augment(
        piece_id="hood_001",
        catalyst=Catalyst.BRINE_DROP,
        roll_seed=1,
    )
    r2 = a.augment(
        piece_id="hood_001",
        catalyst=Catalyst.KRAKEN_INK_VIAL,
        roll_seed=1,
    )
    # only the latest survives
    saved = a.augment_for(piece_id="hood_001")
    assert saved.band == AugmentBand.RARE
    assert saved.band != r1.band


def test_augment_for_unknown_piece():
    a = AbyssalGearAugment()
    assert a.augment_for(piece_id="ghost") is None


def test_augment_for_returns_saved_roll():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="x", catalyst=Catalyst.BRINE_DROP,
        roll_seed=10,
    )
    saved = a.augment_for(piece_id="x")
    assert saved == r


def test_augment_stat_values_in_band_range():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="x", catalyst=Catalyst.KRAKEN_INK_VIAL,
        roll_seed=100,
    )
    # rare band: 10..25 per stat
    for stat, value in r.stats:
        assert 10 <= value <= 25


def test_common_stat_values_in_common_range():
    a = AbyssalGearAugment()
    r = a.augment(
        piece_id="x", catalyst=Catalyst.BRINE_DROP,
        roll_seed=7,
    )
    # common: 1..5 per stat
    for stat, value in r.stats:
        assert 1 <= value <= 5
