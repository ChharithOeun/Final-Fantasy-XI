"""Tests for magic critical hit resolution."""
from __future__ import annotations

import random

from server.magic_crit import (
    BASE_DAMAGE_CRIT_RATE_PCT,
    DAMAGE_CRIT_MULTIPLIER,
    DRAIN_CRIT_MULTIPLIER,
    HEAL_CRIT_MULTIPLIER,
    MAX_CRIT_RATE_PCT,
    MagicCritContext,
    SpellKind,
    resolve_magic_crit,
)


def _ctx(**kwargs) -> MagicCritContext:
    base = dict(
        spell_id="fire_iv",
        spell_kind=SpellKind.DAMAGE,
        spell_tier=4, caster_stat_value=100,
        target_magic_defense_bonus=0,
        gear_magic_crit_bonus_pct=0,
        is_burst=False,
    )
    base.update(kwargs)
    return MagicCritContext(**base)


def test_status_spells_cannot_crit():
    res = resolve_magic_crit(
        context=_ctx(spell_kind=SpellKind.STATUS_LIKE),
        rng=random.Random(0),
    )
    assert not res.crit
    assert res.multiplier == 1.0


def test_summon_spells_cannot_crit():
    res = resolve_magic_crit(
        context=_ctx(spell_kind=SpellKind.SUMMON_LIKE),
        rng=random.Random(0),
    )
    assert not res.crit


def test_dispel_cannot_crit():
    res = resolve_magic_crit(
        context=_ctx(spell_kind=SpellKind.DISPEL_LIKE),
        rng=random.Random(0),
    )
    assert not res.crit


def test_damage_spell_can_crit():
    """Run a few rolls; with 50% effective rate, at least one
    crit should fire."""
    crits = 0
    rng = random.Random(7)
    for _ in range(100):
        res = resolve_magic_crit(
            context=_ctx(
                gear_magic_crit_bonus_pct=50,
            ),
            rng=rng,
        )
        if res.crit:
            crits += 1
    assert crits > 30


def test_damage_crit_uses_1_5x():
    """Force a crit by making rate 100%."""
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 1
    res = resolve_magic_crit(
        context=_ctx(gear_magic_crit_bonus_pct=99),
        rng=_StubRng(),
    )
    assert res.crit
    assert res.multiplier == DAMAGE_CRIT_MULTIPLIER


def test_heal_crit_doubles():
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 1
    res = resolve_magic_crit(
        context=_ctx(
            spell_kind=SpellKind.HEAL,
            spell_id="cure_v", spell_tier=5,
            caster_stat_value=120,
            gear_magic_crit_bonus_pct=99,
        ),
        rng=_StubRng(),
    )
    assert res.crit
    assert res.multiplier == HEAL_CRIT_MULTIPLIER


def test_drain_crit_doubles():
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 1
    res = resolve_magic_crit(
        context=_ctx(
            spell_kind=SpellKind.DRAIN,
            spell_id="drain", spell_tier=2,
            gear_magic_crit_bonus_pct=99,
        ),
        rng=_StubRng(),
    )
    assert res.crit
    assert res.multiplier == DRAIN_CRIT_MULTIPLIER


def test_caster_stat_above_50_adds_rate():
    """+10 stat above 50 = +1% rate."""
    res = resolve_magic_crit(
        context=_ctx(caster_stat_value=150),
        rng=random.Random(0),
    )
    # base 5 + (150-50)//10 = 5 + 10 = 15%; tier 4 -1
    assert res.effective_rate_pct == 14


def test_target_mdb_reduces_rate():
    """Each 5 MDB = -1% crit."""
    res = resolve_magic_crit(
        context=_ctx(
            caster_stat_value=100,
            target_magic_defense_bonus=50,
        ),
        rng=random.Random(0),
    )
    # base 5 + 5 (stat) - 1 (tier 4) - 10 (mdb) = -1 -> 0
    assert res.effective_rate_pct == 0


def test_high_tier_penalty():
    res = resolve_magic_crit(
        context=_ctx(
            spell_kind=SpellKind.DAMAGE,
            spell_tier=6,
            caster_stat_value=50,
            gear_magic_crit_bonus_pct=0,
        ),
        rng=random.Random(0),
    )
    # base 5 + 0 (stat == 50) - 3 (tier 6 is +3 over base 3)
    # Actually tier 6 means (6-3)*1 = -3
    assert res.effective_rate_pct == 2


def test_magic_burst_window_bonus():
    no_burst = resolve_magic_crit(
        context=_ctx(is_burst=False),
        rng=random.Random(0),
    )
    burst = resolve_magic_crit(
        context=_ctx(is_burst=True),
        rng=random.Random(0),
    )
    assert burst.effective_rate_pct == (
        no_burst.effective_rate_pct + 5
    )


def test_crit_rate_capped_at_max():
    res = resolve_magic_crit(
        context=_ctx(
            gear_magic_crit_bonus_pct=999,
        ),
        rng=random.Random(0),
    )
    assert res.effective_rate_pct == MAX_CRIT_RATE_PCT


def test_zero_rate_never_crits():
    res = resolve_magic_crit(
        context=_ctx(
            spell_tier=10,
            caster_stat_value=0,
            gear_magic_crit_bonus_pct=0,
        ),
        rng=random.Random(0),
    )
    assert not res.crit
    assert res.effective_rate_pct == 0


def test_drain_lower_baseline_than_damage():
    drain = resolve_magic_crit(
        context=_ctx(
            spell_kind=SpellKind.DRAIN, spell_tier=1,
            caster_stat_value=50,
        ),
        rng=random.Random(0),
    )
    damage = resolve_magic_crit(
        context=_ctx(
            spell_kind=SpellKind.DAMAGE, spell_tier=1,
            caster_stat_value=50,
        ),
        rng=random.Random(0),
    )
    assert drain.effective_rate_pct < damage.effective_rate_pct


def test_effective_rate_at_default():
    """Check baseline at defaults: damage tier 4, stat 100,
    no MDB or gear -> 5 + 5 - 1 = 9%."""
    res = resolve_magic_crit(
        context=_ctx(
            caster_stat_value=100, spell_tier=4,
        ),
        rng=random.Random(0),
    )
    assert res.effective_rate_pct == 9


def test_full_lifecycle_blm_burst_with_gear():
    """BLM with crit gear, in MB window, casting Fire IV against
    an undead with 0 MDB. Force the rng to crit; result should
    apply 1.5x."""
    class _StubRng:
        def randint(self, lo: int, hi: int) -> int:
            return 1
    res = resolve_magic_crit(
        context=_ctx(
            spell_id="fire_iv", spell_kind=SpellKind.DAMAGE,
            spell_tier=4, caster_stat_value=200,
            gear_magic_crit_bonus_pct=10,
            is_burst=True,
        ),
        rng=_StubRng(),
    )
    # rate = 5 (base) + 15 (stat=200, +15) - 1 (tier 4)
    #        + 10 (gear) + 5 (burst) = 34
    assert res.effective_rate_pct == 34
    assert res.crit
    assert res.multiplier == DAMAGE_CRIT_MULTIPLIER
