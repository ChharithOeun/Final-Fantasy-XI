"""Tests for the beastman shadow dynamis."""
from __future__ import annotations

from server.beastman_shadow_dynamis import (
    BeastmanShadowDynamis,
    DynamisCity,
    InstanceState,
)


def _seed(d):
    d.register_zone(
        city=DynamisCity.OZTROJA,
        total_waves=3,
        base_hourglass_seconds=600,
    )


def test_register_zone():
    d = BeastmanShadowDynamis()
    _seed(d)
    assert d.total_zones() == 1


def test_register_zone_duplicate():
    d = BeastmanShadowDynamis()
    _seed(d)
    res = d.register_zone(
        city=DynamisCity.OZTROJA,
        total_waves=5,
        base_hourglass_seconds=900,
    )
    assert res is None


def test_register_zone_zero_waves():
    d = BeastmanShadowDynamis()
    res = d.register_zone(
        city=DynamisCity.HALVUNG,
        total_waves=0,
        base_hourglass_seconds=600,
    )
    assert res is None


def test_enter_basic():
    d = BeastmanShadowDynamis()
    _seed(d)
    res = d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw", "zlar"),
        now_seconds=0,
    )
    assert res.accepted
    assert res.expires_at == 600


def test_enter_unknown_zone():
    d = BeastmanShadowDynamis()
    res = d.enter(
        instance_id="i1",
        city=DynamisCity.HALVUNG,
        party_ids=("kraw",),
        now_seconds=0,
    )
    assert not res.accepted


def test_enter_duplicate_instance():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    res = d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("zlar",),
        now_seconds=0,
    )
    assert not res.accepted


def test_enter_empty_party():
    d = BeastmanShadowDynamis()
    _seed(d)
    res = d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=(),
        now_seconds=0,
    )
    assert not res.accepted


def test_clear_wave_extends_hourglass():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    res = d.clear_wave(instance_id="i1", wave_index=0, now_seconds=10)
    assert res.accepted
    assert res.expires_at == 600 + 180  # base + extension
    assert res.bytnes_dropped == 25


def test_clear_wave_out_of_order():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    res = d.clear_wave(instance_id="i1", wave_index=2, now_seconds=10)
    assert not res.accepted


def test_clear_final_wave_marks_cleared():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    for i in range(3):
        d.clear_wave(
            instance_id="i1", wave_index=i, now_seconds=10 + i,
        )
    inst = d.get_instance("i1")
    assert inst.state == InstanceState.CLEARED


def test_boss_wave_drops_more():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    d.clear_wave(instance_id="i1", wave_index=0, now_seconds=10)
    d.clear_wave(instance_id="i1", wave_index=1, now_seconds=20)
    res = d.clear_wave(
        instance_id="i1", wave_index=2, now_seconds=30,
    )
    assert res.bytnes_dropped == 100


def test_clear_wave_after_expiry():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    res = d.clear_wave(
        instance_id="i1", wave_index=0, now_seconds=999_999,
    )
    assert not res.accepted


def test_clear_unknown_instance():
    d = BeastmanShadowDynamis()
    res = d.clear_wave(
        instance_id="ghost", wave_index=0, now_seconds=0,
    )
    assert not res.accepted


def test_award_currency_basic():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw", "zlar"),
        now_seconds=0,
    )
    for i in range(3):
        d.clear_wave(
            instance_id="i1", wave_index=i, now_seconds=10 + i,
        )
    res = d.award_currency(
        instance_id="i1", player_id="kraw",
    )
    # pool = 25 + 25 + 100 = 150, split 2 = 75
    assert res.bytnes_awarded == 75


def test_award_currency_double_blocked():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    for i in range(3):
        d.clear_wave(
            instance_id="i1", wave_index=i, now_seconds=10 + i,
        )
    d.award_currency(instance_id="i1", player_id="kraw")
    res = d.award_currency(instance_id="i1", player_id="kraw")
    assert not res.accepted


def test_award_currency_not_in_party():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    for i in range(3):
        d.clear_wave(
            instance_id="i1", wave_index=i, now_seconds=10 + i,
        )
    res = d.award_currency(instance_id="i1", player_id="ghost")
    assert not res.accepted


def test_award_currency_not_cleared():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    res = d.award_currency(instance_id="i1", player_id="kraw")
    assert not res.accepted


def test_state_for_lazy_expiry():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    s = d.state_for(instance_id="i1", now_seconds=10_000)
    assert s == InstanceState.EXPIRED


def test_state_for_unknown():
    d = BeastmanShadowDynamis()
    assert d.state_for(
        instance_id="ghost", now_seconds=0,
    ) == InstanceState.STAGED


def test_no_double_clear_after_cleared():
    d = BeastmanShadowDynamis()
    _seed(d)
    d.enter(
        instance_id="i1",
        city=DynamisCity.OZTROJA,
        party_ids=("kraw",),
        now_seconds=0,
    )
    for i in range(3):
        d.clear_wave(
            instance_id="i1", wave_index=i, now_seconds=10 + i,
        )
    res = d.clear_wave(
        instance_id="i1", wave_index=3, now_seconds=40,
    )
    assert not res.accepted
