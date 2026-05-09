"""Tests for nation_border_guard."""
from __future__ import annotations

from server.nation_border_guard import (
    NationBorderGuardSystem, Shift, PostState,
)


def _est(s, **overrides):
    args = dict(
        post_id="bastok_gate_n",
        nation_id="bastok",
        zone_a="bastok_markets",
        zone_b="north_gustaberg",
        guard_count=10,
    )
    args.update(overrides)
    return s.establish_post(**args)


def test_establish_happy():
    s = NationBorderGuardSystem()
    assert _est(s) is True


def test_establish_blank():
    s = NationBorderGuardSystem()
    assert _est(s, post_id="") is False


def test_establish_self_zone():
    s = NationBorderGuardSystem()
    assert _est(
        s, zone_a="bastok", zone_b="bastok",
    ) is False


def test_establish_negative_guards():
    s = NationBorderGuardSystem()
    assert _est(s, guard_count=-1) is False


def test_establish_dup_blocked():
    s = NationBorderGuardSystem()
    _est(s)
    assert _est(s) is False


def test_establish_zero_guards_abandoned():
    s = NationBorderGuardSystem()
    _est(s, guard_count=0)
    assert s.post(
        post_id="bastok_gate_n",
    ).state == PostState.ABANDONED


def test_establish_low_guards_undermanned():
    s = NationBorderGuardSystem()
    _est(s, guard_count=3)  # < 6 (min*3)
    assert s.post(
        post_id="bastok_gate_n",
    ).state == PostState.UNDERMANNED


def test_reinforce_happy():
    s = NationBorderGuardSystem()
    _est(s, guard_count=3)
    assert s.reinforce_post(
        post_id="bastok_gate_n",
        additional_guards=10,
    ) is True
    assert s.post(
        post_id="bastok_gate_n",
    ).state == PostState.OPERATIONAL


def test_reinforce_abandoned_blocked():
    s = NationBorderGuardSystem()
    _est(s, guard_count=0)
    assert s.reinforce_post(
        post_id="bastok_gate_n",
        additional_guards=10,
    ) is False


def test_reinforce_negative():
    s = NationBorderGuardSystem()
    _est(s)
    assert s.reinforce_post(
        post_id="bastok_gate_n",
        additional_guards=0,
    ) is False


def test_lose_guards():
    s = NationBorderGuardSystem()
    _est(s, guard_count=10)
    s.lose_guards(
        post_id="bastok_gate_n", lost=8,
    )
    assert s.post(
        post_id="bastok_gate_n",
    ).state == PostState.UNDERMANNED


def test_lose_all_guards_abandoned():
    s = NationBorderGuardSystem()
    _est(s, guard_count=5)
    s.lose_guards(
        post_id="bastok_gate_n", lost=5,
    )
    assert s.post(
        post_id="bastok_gate_n",
    ).state == PostState.ABANDONED


def test_assign_shift_happy():
    s = NationBorderGuardSystem()
    _est(s, guard_count=10)
    assert s.assign_shift(
        post_id="bastok_gate_n", shift=Shift.DAY,
        assigned_guards=4,
    ) is True


def test_assign_shift_over_guards():
    s = NationBorderGuardSystem()
    _est(s, guard_count=5)
    assert s.assign_shift(
        post_id="bastok_gate_n", shift=Shift.DAY,
        assigned_guards=10,
    ) is False


def test_shift_effectiveness_full():
    s = NationBorderGuardSystem()
    _est(s, guard_count=10)
    s.assign_shift(
        post_id="bastok_gate_n", shift=Shift.NIGHT,
        assigned_guards=4,
    )
    assert s.shift_effectiveness_pct(
        post_id="bastok_gate_n", shift=Shift.NIGHT,
    ) == 100


def test_shift_effectiveness_partial():
    s = NationBorderGuardSystem()
    _est(s, guard_count=10)
    s.assign_shift(
        post_id="bastok_gate_n",
        shift=Shift.GRAVEYARD, assigned_guards=1,
    )
    assert s.shift_effectiveness_pct(
        post_id="bastok_gate_n",
        shift=Shift.GRAVEYARD,
    ) == 50


def test_shift_effectiveness_unassigned_zero():
    s = NationBorderGuardSystem()
    _est(s, guard_count=10)
    assert s.shift_effectiveness_pct(
        post_id="bastok_gate_n", shift=Shift.DAY,
    ) == 0


def test_record_intercept_happy():
    s = NationBorderGuardSystem()
    _est(s)
    iid = s.record_intercept(
        post_id="bastok_gate_n",
        smuggler_id="bob", contraband="moko grass",
        value_gil=5_000, intercepted_day=10,
        shift=Shift.NIGHT,
    )
    assert iid is not None


def test_intercept_unknown_post():
    s = NationBorderGuardSystem()
    iid = s.record_intercept(
        post_id="ghost", smuggler_id="bob",
        contraband="x", value_gil=10,
        intercepted_day=10, shift=Shift.DAY,
    )
    assert iid is None


def test_intercept_blank_smuggler():
    s = NationBorderGuardSystem()
    _est(s)
    iid = s.record_intercept(
        post_id="bastok_gate_n", smuggler_id="",
        contraband="x", value_gil=10,
        intercepted_day=10, shift=Shift.DAY,
    )
    assert iid is None


def test_intercept_at_abandoned_blocked():
    s = NationBorderGuardSystem()
    _est(s, guard_count=0)
    iid = s.record_intercept(
        post_id="bastok_gate_n", smuggler_id="bob",
        contraband="x", value_gil=10,
        intercepted_day=10, shift=Shift.DAY,
    )
    assert iid is None


def test_posts_for_nation():
    s = NationBorderGuardSystem()
    _est(s, post_id="a")
    _est(s, post_id="b", zone_a="x", zone_b="y")
    _est(s, post_id="c", nation_id="windy",
         zone_a="windy", zone_b="east_sarutabaruta")
    out = s.posts_for(nation_id="bastok")
    assert len(out) == 2


def test_posts_at_zone():
    s = NationBorderGuardSystem()
    _est(s, post_id="a", zone_a="x", zone_b="y")
    _est(s, post_id="b", zone_a="y", zone_b="z")
    out = s.posts_at(zone="y")
    assert len(out) == 2


def test_intercepts_at_post():
    s = NationBorderGuardSystem()
    _est(s)
    s.record_intercept(
        post_id="bastok_gate_n",
        smuggler_id="bob", contraband="x",
        value_gil=10, intercepted_day=10,
        shift=Shift.DAY,
    )
    s.record_intercept(
        post_id="bastok_gate_n",
        smuggler_id="cara", contraband="y",
        value_gil=20, intercepted_day=11,
        shift=Shift.NIGHT,
    )
    assert len(s.intercepts_at(
        post_id="bastok_gate_n",
    )) == 2


def test_intercepts_of_smuggler():
    s = NationBorderGuardSystem()
    _est(s)
    s.record_intercept(
        post_id="bastok_gate_n", smuggler_id="bob",
        contraband="x", value_gil=10,
        intercepted_day=10, shift=Shift.DAY,
    )
    s.record_intercept(
        post_id="bastok_gate_n", smuggler_id="bob",
        contraband="y", value_gil=20,
        intercepted_day=11, shift=Shift.NIGHT,
    )
    s.record_intercept(
        post_id="bastok_gate_n", smuggler_id="cara",
        contraband="z", value_gil=30,
        intercepted_day=12, shift=Shift.DAY,
    )
    assert len(s.intercepts_of(
        smuggler_id="bob",
    )) == 2


def test_post_unknown():
    s = NationBorderGuardSystem()
    assert s.post(post_id="ghost") is None


def test_enum_counts():
    assert len(list(Shift)) == 3
    assert len(list(PostState)) == 3
