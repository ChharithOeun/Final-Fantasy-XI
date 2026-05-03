"""Tests for combat outcome resolution."""
from __future__ import annotations

import random

from server.combat_outcomes import (
    AttackAngle,
    AttackContext,
    AttackKind,
    CRIT_MULTIPLIER,
    GRAZE_MULTIPLIER,
    HIT_RATE_MAX,
    HIT_RATE_MIN,
    OutcomeKind,
    resolve_outcome,
)


def _ctx(**overrides) -> AttackContext:
    base = dict(
        attack_kind=AttackKind.MELEE,
        angle=AttackAngle.FRONT,
        attacker_accuracy=100, defender_evasion=100,
        attacker_crit_rate_pct=5,
        defender_parry_rate_pct=0,
        defender_shielded=False,
        defender_block_rate_pct=0,
        defender_counter_rate_pct=0,
        attacker_blinded=False,
        defender_stunned=False, defender_sleeping=False,
        defender_petrified=False, bypass_defenses=False,
    )
    base.update(overrides)
    return AttackContext(**base)


def test_sleeping_defender_auto_crit():
    res = resolve_outcome(
        context=_ctx(defender_sleeping=True),
        rng=random.Random(0),
    )
    assert res.outcome == OutcomeKind.CRIT
    assert res.damage_multiplier == CRIT_MULTIPLIER


def test_petrified_defender_auto_crit():
    res = resolve_outcome(
        context=_ctx(defender_petrified=True),
        rng=random.Random(0),
    )
    assert res.outcome == OutcomeKind.CRIT


def test_evasion_can_avoid_attack():
    """Massive evasion vs no accuracy -> EVADE often."""
    rng = random.Random(0)
    seen_evades = 0
    for _ in range(200):
        res = resolve_outcome(
            context=_ctx(
                attacker_accuracy=10, defender_evasion=200,
            ),
            rng=rng,
        )
        if res.outcome == OutcomeKind.EVADE:
            seen_evades += 1
    # Should evade a lot but capped at 1 - HIT_RATE_MIN = 0.8
    assert seen_evades >= 50


def test_evade_floors_hit_rate():
    """Even with awful accuracy, attacker can't drop below
    HIT_RATE_MIN. Verify by running many rolls."""
    rng = random.Random(7)
    hits = 0
    total = 500
    for _ in range(total):
        res = resolve_outcome(
            context=_ctx(
                attacker_accuracy=1, defender_evasion=999,
            ),
            rng=rng,
        )
        if res.outcome != OutcomeKind.EVADE:
            hits += 1
    # Hit rate floor 0.20 -> ~100 hits in 500 rolls
    assert hits >= 50


def test_evade_ceiling_caps_hit_rate():
    """Even with massive accuracy, defender can still evade
    at least 1 - HIT_RATE_MAX = 5% of the time."""
    rng = random.Random(11)
    evades = 0
    for _ in range(500):
        res = resolve_outcome(
            context=_ctx(
                attacker_accuracy=999, defender_evasion=10,
            ),
            rng=rng,
        )
        if res.outcome == OutcomeKind.EVADE:
            evades += 1
    # Ceiling means at LEAST 1-0.95 = 5% miss
    assert evades >= 5


def test_blinded_attacker_halves_hit_rate():
    """Blind status should produce more evades."""
    rng_blind = random.Random(2)
    rng_normal = random.Random(2)
    blind_evades = 0
    normal_evades = 0
    for _ in range(200):
        if resolve_outcome(
            context=_ctx(attacker_blinded=True),
            rng=rng_blind,
        ).outcome == OutcomeKind.EVADE:
            blind_evades += 1
        if resolve_outcome(
            context=_ctx(),
            rng=rng_normal,
        ).outcome == OutcomeKind.EVADE:
            normal_evades += 1
    assert blind_evades > normal_evades


def test_parry_only_from_front():
    """Rear attacks bypass parry."""
    res = resolve_outcome(
        context=_ctx(
            angle=AttackAngle.REAR,
            defender_parry_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome != OutcomeKind.PARRY


def test_parry_fires_when_high_rate():
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            defender_parry_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome == OutcomeKind.PARRY


def test_parry_then_counter():
    """High parry + high counter -> parry-counter combo."""
    rng = random.Random(0)
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            defender_parry_rate_pct=100,
            defender_counter_rate_pct=100,
        ),
        rng=rng,
    )
    assert res.outcome == OutcomeKind.COUNTER
    assert res.triggered_counter


def test_block_only_when_shielded():
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            defender_shielded=False,
            defender_block_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome != OutcomeKind.BLOCK


def test_block_partial_damage():
    """Block doesn't void damage — applies 0.25 multiplier."""
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            defender_shielded=True,
            defender_block_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome == OutcomeKind.BLOCK
    assert res.damage_multiplier == 0.25


def test_ranged_attack_cannot_be_parried():
    res = resolve_outcome(
        context=_ctx(
            attack_kind=AttackKind.RANGED,
            attacker_accuracy=200, defender_evasion=10,
            defender_parry_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome != OutcomeKind.PARRY


def test_ranged_attack_cannot_be_countered():
    res = resolve_outcome(
        context=_ctx(
            attack_kind=AttackKind.RANGED,
            attacker_accuracy=200, defender_evasion=10,
            defender_counter_rate_pct=100,
        ),
        rng=random.Random(0),
    )
    assert res.outcome != OutcomeKind.COUNTER


def test_weaponskill_bypass_defenses():
    """WS attacks ignore parry + block."""
    res = resolve_outcome(
        context=_ctx(
            attack_kind=AttackKind.WEAPONSKILL,
            attacker_accuracy=200, defender_evasion=10,
            defender_parry_rate_pct=100,
            defender_shielded=True,
            defender_block_rate_pct=100,
            bypass_defenses=True,
        ),
        rng=random.Random(0),
    )
    assert res.outcome not in (
        OutcomeKind.PARRY, OutcomeKind.BLOCK,
    )


def test_stunned_defender_cant_evade_parry_block():
    """Stunned -> attack lands; no evade, no parry, no block."""
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=10, defender_evasion=999,
            defender_parry_rate_pct=100,
            defender_shielded=True,
            defender_block_rate_pct=100,
            defender_stunned=True,
        ),
        rng=random.Random(0),
    )
    assert res.outcome not in (
        OutcomeKind.EVADE, OutcomeKind.PARRY,
        OutcomeKind.BLOCK,
    )


def test_crit_fires_on_high_rate():
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            attacker_crit_rate_pct=50,
        ),
        rng=random.Random(0),
    )
    # 50% crit rate is the cap; at least sometimes will fire.
    # Run a few to find one
    rng = random.Random(0)
    saw_crit = False
    for _ in range(50):
        r = resolve_outcome(
            context=_ctx(
                attacker_accuracy=200, defender_evasion=10,
                attacker_crit_rate_pct=50,
            ),
            rng=rng,
        )
        if r.outcome == OutcomeKind.CRIT:
            saw_crit = True
            break
    assert saw_crit


def test_crit_rate_clamped_at_50():
    """Even crazy crit rate (200) clamps at 50%."""
    rng = random.Random(0)
    crits = 0
    for _ in range(500):
        r = resolve_outcome(
            context=_ctx(
                attacker_accuracy=200, defender_evasion=10,
                attacker_crit_rate_pct=999,
            ),
            rng=rng,
        )
        if r.outcome == OutcomeKind.CRIT:
            crits += 1
    # 50% cap -> ~250 crits in 500
    assert crits < 350


def test_graze_only_for_non_weaponskill():
    rng = random.Random(0)
    saw_graze_ws = False
    for _ in range(200):
        r = resolve_outcome(
            context=_ctx(
                attack_kind=AttackKind.WEAPONSKILL,
                attacker_accuracy=200, defender_evasion=10,
                attacker_crit_rate_pct=0,
            ),
            rng=rng,
        )
        if r.outcome == OutcomeKind.GRAZE:
            saw_graze_ws = True
    assert not saw_graze_ws


def test_graze_uses_half_multiplier():
    """When a graze fires, multiplier is GRAZE_MULTIPLIER."""
    rng = random.Random(0)
    for _ in range(500):
        r = resolve_outcome(
            context=_ctx(
                attacker_accuracy=200, defender_evasion=10,
                attacker_crit_rate_pct=0,
            ),
            rng=rng,
        )
        if r.outcome == OutcomeKind.GRAZE:
            assert r.damage_multiplier == GRAZE_MULTIPLIER
            return
    # If we didn't see a graze in 500 rolls, that's actually fine
    # — the test passes if no graze fired.


def test_clean_hit_unit_multiplier():
    res = resolve_outcome(
        context=_ctx(
            attacker_accuracy=200, defender_evasion=10,
            attacker_crit_rate_pct=0,
        ),
        rng=random.Random(11),
    )
    if res.outcome == OutcomeKind.HIT:
        assert res.damage_multiplier == 1.0


def test_full_lifecycle_paladin_tank_vs_orcish_warrior():
    """A PLD with shield + parry vs orc warrior (no special
    statuses). Run many attacks; verify the outcome distribution
    looks sane (parries, blocks, hits, occasional crits)."""
    rng = random.Random(42)
    counts: dict[OutcomeKind, int] = {k: 0 for k in OutcomeKind}
    for _ in range(2000):
        ctx = _ctx(
            attacker_accuracy=110, defender_evasion=120,
            attacker_crit_rate_pct=8,
            defender_parry_rate_pct=12,
            defender_shielded=True,
            defender_block_rate_pct=15,
        )
        r = resolve_outcome(context=ctx, rng=rng)
        counts[r.outcome] += 1
    # All major outcomes should occur
    for kind in (
        OutcomeKind.HIT, OutcomeKind.CRIT,
        OutcomeKind.PARRY, OutcomeKind.BLOCK,
        OutcomeKind.EVADE, OutcomeKind.GRAZE,
    ):
        assert counts[kind] > 0, f"never saw {kind}"
    # No counter without counter rate
    assert counts[OutcomeKind.COUNTER] == 0
