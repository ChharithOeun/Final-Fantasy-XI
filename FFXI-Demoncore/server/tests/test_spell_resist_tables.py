"""Tests for spell resist resolution."""
from __future__ import annotations

import random

from server.spell_resist_tables import (
    Element,
    ResistContext,
    ResistTier,
    multiplier_for_tier,
    resolve_resist,
)


def test_tier_multipliers():
    assert multiplier_for_tier(ResistTier.NONE) == 1.0
    assert multiplier_for_tier(ResistTier.HALF) == 0.5
    assert multiplier_for_tier(ResistTier.QUARTER) == 0.25
    assert multiplier_for_tier(ResistTier.EIGHTH) == 0.125
    assert multiplier_for_tier(ResistTier.FULL_RESIST) == 0.0


def test_high_acc_low_eva_lands_no_resist():
    """Lots of accuracy, no evasion -> mostly NONE."""
    rng = random.Random(0)
    none_count = 0
    for _ in range(200):
        res = resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=300,
                target_magic_evasion=0,
            ),
            rng=rng,
        )
        if res.tier == ResistTier.NONE:
            none_count += 1
    # Almost all should land
    assert none_count >= 180


def test_low_acc_high_eva_resists_a_lot():
    """No accuracy, lots of evasion -> mostly resist."""
    rng = random.Random(0)
    full_or_eighth = 0
    for _ in range(200):
        res = resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=0,
                target_magic_evasion=300,
            ),
            rng=rng,
        )
        if res.tier in (
            ResistTier.FULL_RESIST, ResistTier.EIGHTH,
        ):
            full_or_eighth += 1
    assert full_or_eighth >= 180


def test_natural_pierce_at_roll_95_or_higher():
    """Roll >= 95 always lands NONE regardless of acc/eva."""
    # Force the rng to roll high
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 99
    res = resolve_resist(
        context=ResistContext(
            caster_magic_accuracy=0,
            target_magic_evasion=999,
        ),
        rng=_StubRng(),
    )
    assert res.tier == ResistTier.NONE


def test_natural_fizzle_at_roll_5_or_lower():
    """Roll <= 5 always FULL_RESIST."""
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 3
    res = resolve_resist(
        context=ResistContext(
            caster_magic_accuracy=999,
            target_magic_evasion=0,
        ),
        rng=_StubRng(),
    )
    assert res.tier == ResistTier.FULL_RESIST


def test_element_affinity_amplifies_resist():
    """Target with +50 fire affinity resists Fire harder."""
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    no_affinity = []
    high_affinity = []
    # Use caster acc 200 vs eva 100 -> eff_acc = 100 (no aff)
    # vs 50 (high aff). Big enough to differentiate NONE rates.
    for _ in range(200):
        no_affinity.append(resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=200,
                target_magic_evasion=100,
                spell_element=Element.FIRE,
                target_element_affinity=0,
            ),
            rng=rng_a,
        ))
        high_affinity.append(resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=200,
                target_magic_evasion=100,
                spell_element=Element.FIRE,
                target_element_affinity=50,
            ),
            rng=rng_b,
        ))
    no_aff_full = sum(
        1 for r in no_affinity
        if r.tier == ResistTier.NONE
    )
    aff_full = sum(
        1 for r in high_affinity
        if r.tier == ResistTier.NONE
    )
    assert no_aff_full > aff_full


def test_silenced_target_resists_less():
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    silenced = 0
    quiet = 0
    # caster acc 160 vs eva 100 -> eff_acc 60 baseline; silenced
    # bumps to 80. NONE-band rolls scale meaningfully different.
    for _ in range(200):
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=160,
                target_magic_evasion=100,
                target_silenced=True,
            ),
            rng=rng_a,
        ).tier == ResistTier.NONE:
            silenced += 1
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=160,
                target_magic_evasion=100,
                target_silenced=False,
            ),
            rng=rng_b,
        ).tier == ResistTier.NONE:
            quiet += 1
    assert silenced > quiet


def test_dispelled_buffs_drop_resist():
    """Each dispelled buff = +5 effective accuracy."""
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    no_dispel_full = 0
    dispel_full = 0
    # caster acc 160 vs eva 100 -> eff_acc 60. With 4 buffs
    # dispelled, +20 -> eff_acc 80. Differentiates NONE-band.
    for _ in range(200):
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=160,
                target_magic_evasion=100,
                target_dispelled_buffs=0,
            ),
            rng=rng_a,
        ).tier == ResistTier.NONE:
            no_dispel_full += 1
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=160,
                target_magic_evasion=100,
                target_dispelled_buffs=4,
            ),
            rng=rng_b,
        ).tier == ResistTier.NONE:
            dispel_full += 1
    assert dispel_full > no_dispel_full


def test_enfeeble_stricter_than_damage_spell():
    rng_a = random.Random(0)
    rng_b = random.Random(0)
    dmg = 0
    enf = 0
    # eff_acc 50 -> damage spell NONE band rolls 6..50; enfeeble
    # NONE band rolls 6..40 (margin >= 10).
    for _ in range(200):
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=150,
                target_magic_evasion=100,
                spell_is_enfeeble=False,
            ),
            rng=rng_a,
        ).tier == ResistTier.NONE:
            dmg += 1
        if resolve_resist(
            context=ResistContext(
                caster_magic_accuracy=150,
                target_magic_evasion=100,
                spell_is_enfeeble=True,
            ),
            rng=rng_b,
        ).tier == ResistTier.NONE:
            enf += 1
    assert dmg > enf


def test_resolution_includes_diagnostics():
    res = resolve_resist(
        context=ResistContext(
            caster_magic_accuracy=120,
            target_magic_evasion=80,
        ),
        rng=random.Random(42),
    )
    assert res.effective_magic_accuracy == 40
    assert 1 <= res.roll <= 100


def test_full_resist_zero_damage():
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 1
    res = resolve_resist(
        context=ResistContext(
            caster_magic_accuracy=999,
            target_magic_evasion=0,
        ),
        rng=_StubRng(),
    )
    assert res.multiplier == 0.0


def test_close_call_lands_half():
    """Margin in [-10, 0) -> HALF resist."""
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 75
    # effective_acc = 70, roll 75, margin -5 -> HALF
    res = resolve_resist(
        context=ResistContext(
            caster_magic_accuracy=170,
            target_magic_evasion=100,
        ),
        rng=_StubRng(),
    )
    assert res.tier == ResistTier.HALF


def test_full_lifecycle_undead_vs_fire():
    """Undead with very high fire weakness (-50 affinity) -> Fire
    spells almost never resisted."""
    rng = random.Random(11)
    weakness = ResistContext(
        caster_magic_accuracy=200,
        target_magic_evasion=80,
        spell_element=Element.FIRE,
        target_element_affinity=-50,    # weak to fire
    )
    full_lands = 0
    for _ in range(200):
        if resolve_resist(
            context=weakness, rng=rng,
        ).tier == ResistTier.NONE:
            full_lands += 1
    assert full_lands >= 180


def test_full_lifecycle_strong_resist_target():
    """Boss with +75 affinity, high MEva -> resists most spells."""
    rng = random.Random(0)
    boss = ResistContext(
        caster_magic_accuracy=100,
        target_magic_evasion=180,
        target_element_affinity=75,
    )
    none_lands = 0
    for _ in range(200):
        if resolve_resist(
            context=boss, rng=rng,
        ).tier == ResistTier.NONE:
            none_lands += 1
    # Should rarely land cleanly
    assert none_lands < 30
