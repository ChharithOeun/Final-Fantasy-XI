"""Tests for the random encounter scheduler."""
from __future__ import annotations

import random

import pytest

from server.random_encounters import (
    EncounterKind,
    EncounterScheduler,
    EncounterTriggerContext,
    PER_ZONE_COOLDOWN_SECONDS,
    TimeOfDay,
    ZoneEncounterProfile,
    time_of_day_for_hour,
)


def _ctx(**overrides) -> EncounterTriggerContext:
    base = dict(
        zone_id="konschtat", party_id="alpha",
        party_size=3, hour_of_day=12,
        now_seconds=0.0, raid_pressure=0,
        party_outlaw=False, party_avg_level=30,
    )
    base.update(overrides)
    return EncounterTriggerContext(**base)


def _scheduler() -> EncounterScheduler:
    s = EncounterScheduler(base_probability=1.0)  # always fire
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="konschtat", base_risk=50,
    ))
    return s


def test_time_of_day_buckets():
    assert time_of_day_for_hour(12) == TimeOfDay.DAY
    assert time_of_day_for_hour(19) == TimeOfDay.DUSK
    assert time_of_day_for_hour(2) == TimeOfDay.NIGHT
    assert time_of_day_for_hour(23) == TimeOfDay.NIGHT
    assert time_of_day_for_hour(5) == TimeOfDay.DAWN


def test_register_zone_validates_risk():
    s = EncounterScheduler()
    with pytest.raises(ValueError):
        s.register_zone_profile(ZoneEncounterProfile(
            zone_id="bad", base_risk=200,
        ))


def test_unknown_zone_returns_none():
    s = EncounterScheduler()
    res = s.roll(
        context=_ctx(zone_id="ghost"), rng=random.Random(0),
    )
    assert res is None


def test_low_probability_can_skip():
    s = EncounterScheduler(base_probability=0.0)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="konschtat", base_risk=50,
    ))
    rng = random.Random(0)
    # With prob=0, never fires
    for _ in range(20):
        res = s.roll(context=_ctx(), rng=rng)
        assert res is None


def test_high_risk_zone_fires():
    s = _scheduler()
    res = s.roll(
        context=_ctx(party_size=1, hour_of_day=2),
        rng=random.Random(1),
    )
    assert res is not None


def test_cooldown_blocks_immediate_re_roll():
    s = _scheduler()
    rng = random.Random(0)
    first = s.roll(context=_ctx(now_seconds=100.0), rng=rng)
    assert first is not None
    second = s.roll(context=_ctx(now_seconds=200.0), rng=rng)
    assert second is None


def test_cooldown_clears_after_window():
    s = _scheduler()
    rng = random.Random(0)
    s.roll(context=_ctx(now_seconds=100.0), rng=rng)
    later = s.roll(
        context=_ctx(
            now_seconds=100.0 + PER_ZONE_COOLDOWN_SECONDS + 1,
        ),
        rng=rng,
    )
    assert later is not None


def test_reset_zone_cooldown():
    s = _scheduler()
    rng = random.Random(0)
    s.roll(context=_ctx(now_seconds=100.0), rng=rng)
    assert s.reset_zone_cooldown(
        zone_id="konschtat", party_id="alpha",
    )
    res = s.roll(context=_ctx(now_seconds=110.0), rng=rng)
    assert res is not None


def test_night_eligibility_excludes_caravan():
    """Caravan_downed has weight 0 at night."""
    s = EncounterScheduler(base_probability=1.0)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="konschtat", base_risk=80,
        eligible_kinds=frozenset({EncounterKind.CARAVAN_DOWNED}),
    ))
    rng = random.Random(0)
    res = s.roll(
        context=_ctx(hour_of_day=2),  # night
        rng=rng,
    )
    # Only one eligible kind, but it has weight 0 at night
    assert res is None


def test_night_favors_fomor_ambush():
    """At night, FOMOR_AMBUSH has weight 6 vs other low weights."""
    s = EncounterScheduler(base_probability=1.0)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="frontier", base_risk=80,
    ))
    seen: dict[EncounterKind, int] = {}
    rng = random.Random(7)
    # Run many rolls at night with cooldown reset between
    for i in range(50):
        s.reset_zone_cooldown(
            zone_id="frontier", party_id="alpha",
        )
        ctx = _ctx(
            zone_id="frontier", party_id="alpha",
            hour_of_day=2, now_seconds=i * 1.0,
        )
        res = s.roll(context=ctx, rng=rng)
        if res is not None:
            seen[res.encounter_kind] = (
                seen.get(res.encounter_kind, 0) + 1
            )
    # Fomor should be the most common (or tied with lost spirits)
    assert seen.get(EncounterKind.FOMOR_AMBUSH, 0) >= 3


def test_solo_party_higher_probability():
    """Lone travelers see encounters more often."""
    # Effective prob for solo should be > for party of 6
    s = EncounterScheduler(base_probability=0.3)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="konschtat", base_risk=30,
    ))
    rng_a = random.Random(0)
    rng_b = random.Random(0)
    solo_hits = 0
    party_hits = 0
    for i in range(100):
        s.reset_zone_cooldown(
            zone_id="konschtat", party_id="solo",
        )
        s.reset_zone_cooldown(
            zone_id="konschtat", party_id="big",
        )
        if s.roll(
            context=_ctx(
                party_id="solo", party_size=1,
                now_seconds=i * 1.0,
            ),
            rng=rng_a,
        ):
            solo_hits += 1
        if s.roll(
            context=_ctx(
                party_id="big", party_size=6,
                now_seconds=i * 1.0,
            ),
            rng=rng_b,
        ):
            party_hits += 1
    assert solo_hits > party_hits


def test_eligible_kinds_filter():
    """Zone restricted to merchant + pilgrim only."""
    s = EncounterScheduler(base_probability=1.0)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="safe_road", base_risk=80,
        eligible_kinds=frozenset({
            EncounterKind.MERCHANT_HAWK,
            EncounterKind.PILGRIM_PATROL,
        }),
    ))
    rng = random.Random(0)
    seen_kinds: set[EncounterKind] = set()
    for i in range(20):
        s.reset_zone_cooldown(
            zone_id="safe_road", party_id="alpha",
        )
        res = s.roll(
            context=_ctx(
                zone_id="safe_road", party_id="alpha",
                hour_of_day=12, now_seconds=i * 1.0,
            ),
            rng=rng,
        )
        if res is not None:
            seen_kinds.add(res.encounter_kind)
    # Only those two kinds ever surface
    assert seen_kinds.issubset({
        EncounterKind.MERCHANT_HAWK,
        EncounterKind.PILGRIM_PATROL,
    })


def test_mob_count_scales_with_party_size():
    s = EncounterScheduler(base_probability=1.0)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="raid_zone", base_risk=80,
        eligible_kinds=frozenset({
            EncounterKind.BEASTMEN_RAID,
        }),
    ))
    rng = random.Random(11)
    res = s.roll(
        context=_ctx(
            zone_id="raid_zone", party_size=6,
            hour_of_day=12,
        ),
        rng=rng,
    )
    assert res is not None
    # party_size 6 + roll 2..4 = mob count between 8 and 10
    assert res.mob_count >= 8


def test_raid_pressure_amplifies_probability():
    s = EncounterScheduler(base_probability=0.05)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="contested", base_risk=30,
    ))
    rng_low = random.Random(99)
    rng_high = random.Random(99)
    low_hits = 0
    high_hits = 0
    for i in range(100):
        s.reset_zone_cooldown(
            zone_id="contested", party_id="low",
        )
        s.reset_zone_cooldown(
            zone_id="contested", party_id="high",
        )
        if s.roll(
            context=_ctx(
                zone_id="contested", party_id="low",
                raid_pressure=0, now_seconds=i * 1.0,
            ),
            rng=rng_low,
        ):
            low_hits += 1
        if s.roll(
            context=_ctx(
                zone_id="contested", party_id="high",
                raid_pressure=80, now_seconds=i * 1.0,
            ),
            rng=rng_high,
        ):
            high_hits += 1
    assert high_hits > low_hits


def test_full_lifecycle_night_run_through_frontier():
    """Solo level-30 player traveling through a high-risk
    frontier zone at midnight. Multiple encounters fire over
    a long simulated walk."""
    s = EncounterScheduler(base_probability=0.3)
    s.register_zone_profile(ZoneEncounterProfile(
        zone_id="frontier", base_risk=70,
    ))
    rng = random.Random(42)
    encounters: list[str] = []
    for step in range(100):
        # Wait past cooldown each iteration
        ctx = _ctx(
            zone_id="frontier", party_id="alice",
            party_size=1, hour_of_day=2,
            now_seconds=step * (PER_ZONE_COOLDOWN_SECONDS + 1),
        )
        res = s.roll(context=ctx, rng=rng)
        if res is not None:
            encounters.append(res.encounter_kind.value)
    # Several fired and span a few kinds
    assert len(encounters) >= 5
    # Hostile encounters should dominate at night
    hostile = {
        "fomor_ambush", "beastmen_raid", "wildlife_pack",
        "outlaw_bandits",
    }
    hostile_count = sum(1 for e in encounters if e in hostile)
    assert hostile_count >= 3
