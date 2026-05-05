"""Tests for underwater swim."""
from __future__ import annotations

from server.underwater_swim import PressureTier, UnderwaterSwim


def test_enter_water():
    s = UnderwaterSwim()
    res = s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    assert res.accepted
    assert res.breath_seconds == 120


def test_enter_invalid_breath():
    s = UnderwaterSwim()
    res = s.enter_water(
        player_id="kraw",
        max_breath_seconds=0,
        now_seconds=0,
    )
    assert not res.accepted


def test_descend_basic():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    res = s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=10,
        now_seconds=5,
    )
    assert res.accepted
    assert res.depth_yalms == 20
    assert res.stamina_after == 90
    assert res.pressure_tier == PressureTier.SAFE


def test_descend_pressure_light():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=70,
        stamina_cost=20,
        now_seconds=5,
    )
    snap = s.state_for(
        player_id="kraw", now_seconds=5,
    )
    assert snap.pressure_tier == PressureTier.LIGHT


def test_descend_pressure_heavy():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=100,
        stamina_cost=20,
        now_seconds=5,
    )
    snap = s.state_for(
        player_id="kraw", now_seconds=5,
    )
    assert snap.pressure_tier == PressureTier.HEAVY


def test_descend_pressure_crushing():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=200,
        stamina_cost=20,
        now_seconds=5,
    )
    snap = s.state_for(
        player_id="kraw", now_seconds=5,
    )
    assert snap.pressure_tier == PressureTier.CRUSHING


def test_pressure_negator_clears_pressure():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.equip_pressure_negator(
        player_id="kraw", equipped=True,
    )
    s.descend(
        player_id="kraw",
        yalms_down=200,
        stamina_cost=20,
        now_seconds=5,
    )
    snap = s.state_for(
        player_id="kraw", now_seconds=5,
    )
    assert snap.pressure_tier == PressureTier.SAFE


def test_descend_insufficient_stamina():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    res = s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=200,
        now_seconds=5,
    )
    assert not res.accepted


def test_descend_invalid_move():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    res = s.descend(
        player_id="kraw",
        yalms_down=0,
        stamina_cost=10,
        now_seconds=5,
    )
    assert not res.accepted


def test_descend_not_in_water():
    s = UnderwaterSwim()
    res = s.descend(
        player_id="ghost",
        yalms_down=10,
        stamina_cost=5,
        now_seconds=0,
    )
    assert not res.accepted


def test_ascend_basic():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=30,
        stamina_cost=10,
        now_seconds=5,
    )
    res = s.ascend(
        player_id="kraw",
        yalms_up=20,
        stamina_cost=10,
        now_seconds=10,
    )
    assert res.accepted
    assert res.depth_yalms == 10


def test_ascend_clamps_at_surface():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=10,
        stamina_cost=5,
        now_seconds=5,
    )
    res = s.ascend(
        player_id="kraw",
        yalms_up=999,
        stamina_cost=5,
        now_seconds=10,
    )
    assert res.depth_yalms == 0


def test_breath_drains_when_submerged():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=60,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=10,
        now_seconds=0,
    )
    res = s.breath_tick(player_id="kraw", now_seconds=10)
    assert res.breath_seconds == 50


def test_breath_refills_at_surface():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=60,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=10,
        now_seconds=0,
    )
    s.breath_tick(player_id="kraw", now_seconds=30)
    s.surface(player_id="kraw", now_seconds=31)
    res = s.breath_tick(player_id="kraw", now_seconds=32)
    assert res.breath_seconds == 60


def test_drowning_flagged():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=10,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=10,
        now_seconds=0,
    )
    res = s.breath_tick(player_id="kraw", now_seconds=20)
    assert res.drowning


def test_pressure_damage_scales_with_tier():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=200,
        stamina_cost=20,
        now_seconds=0,
    )
    res = s.breath_tick(player_id="kraw", now_seconds=10)
    # CRUSHING tier_count=3, 10s elapsed, 25/tick → 750
    assert res.pressure_damage_dealt == 750


def test_state_for_unknown():
    s = UnderwaterSwim()
    assert s.state_for(
        player_id="ghost", now_seconds=0,
    ) is None


def test_surface_resets_state():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=50,
        stamina_cost=20,
        now_seconds=5,
    )
    s.surface(player_id="kraw", now_seconds=10)
    snap = s.state_for(
        player_id="kraw", now_seconds=10,
    )
    assert not snap.submerged
    assert snap.depth_yalms == 0


def test_re_enter_water_resets():
    s = UnderwaterSwim()
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=60,
        now_seconds=0,
    )
    s.descend(
        player_id="kraw",
        yalms_down=20,
        stamina_cost=80,
        now_seconds=5,
    )
    s.enter_water(
        player_id="kraw",
        max_breath_seconds=120,
        now_seconds=10,
    )
    snap = s.state_for(player_id="kraw", now_seconds=10)
    assert snap.depth_yalms == 0
    assert snap.stamina == 100
