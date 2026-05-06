"""Tests for rebuild_repair_phase."""
from __future__ import annotations

from server.arena_environment import (
    ArenaEnvironment, ArenaFeature, FeatureKind, FeatureState,
)
from server.rebuild_repair_phase import (
    COST_PER_HP_REBUILD,
    COST_PER_HP_REPAIR,
    MIN_CRAFT_SKILL_REBUILD,
    MIN_CRAFT_SKILL_REPAIR,
    PER_FEATURE_COOLDOWN_SECONDS,
    REBUILD_CAP_PCT,
    RebuildRepairPhase,
    RepairKind,
)


def _setup():
    env = ArenaEnvironment()
    env.register_arena(arena_id="a1", features=[
        ArenaFeature(
            feature_id="floor", kind=FeatureKind.FLOOR,
            hp_max=10000, band=1,
        ),
        ArenaFeature(
            feature_id="wall", kind=FeatureKind.WALL,
            hp_max=8000, band=2,
        ),
    ])
    rrp = RebuildRepairPhase(arena_env=env)
    rrp.open_window(
        arena_id="a1", opens_at=0, closes_at=600,
        budget_per_alliance=10000,
    )
    return env, rrp


def test_open_window_happy():
    rrp = RebuildRepairPhase(arena_env=ArenaEnvironment())
    assert rrp.open_window(
        arena_id="a1", opens_at=0, closes_at=600,
        budget_per_alliance=5000,
    ) is True


def test_invalid_window_blocked():
    rrp = RebuildRepairPhase(arena_env=ArenaEnvironment())
    assert rrp.open_window(
        arena_id="a1", opens_at=10, closes_at=10,
        budget_per_alliance=5000,
    ) is False
    assert rrp.open_window(
        arena_id="a1", opens_at=0, closes_at=600,
        budget_per_alliance=0,
    ) is False


def test_repair_intact_blocked():
    env, rrp = _setup()
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is False
    assert "intact" in (out.reason or "")


def test_repair_damaged_happy():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=2000,
        materials_spent=2000, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is True
    assert out.hp_applied == 2000
    assert out.new_hp == 8000


def test_repair_below_min_skill():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=MIN_CRAFT_SKILL_REPAIR - 1,
        now_seconds=10,
    )
    assert out.accepted is False


def test_repair_not_enough_materials():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=100, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is False


def test_repair_caps_at_hp_max():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=2500)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=5000,
        materials_spent=5000, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is True
    assert out.hp_applied == 2500   # only 2500 needed to fill
    assert out.new_hp == 10000


def test_repair_cooldown():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=10,
    )
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=20,
    )
    assert out.accepted is False
    assert "cooldown" in (out.reason or "")
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70,
        now_seconds=10 + PER_FEATURE_COOLDOWN_SECONDS + 1,
    )
    assert out.accepted is True


def test_repair_consumes_budget():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=2000,
        materials_spent=2000, craft_skill=70, now_seconds=10,
    )
    assert rrp.remaining_budget(arena_id="a1") == 8000


def test_repair_over_budget_blocked():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=20000,
        materials_spent=20000, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is False


def test_repair_broken_blocked():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=10000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is False
    assert "broken" in (out.reason or "")


def test_rebuild_broken_happy():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=10000)
    out = rrp.rebuild(
        arena_id="a1", feature_id="floor", hp_target=4000,
        materials_spent=4000 * COST_PER_HP_REBUILD,
        craft_skill=MIN_CRAFT_SKILL_REBUILD, now_seconds=10,
    )
    assert out.accepted is True
    assert out.kind == RepairKind.REBUILD
    assert out.new_hp == 4000


def test_rebuild_caps_at_pct():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=10000)
    # try to rebuild to 9000 (90%) — caps at 60%
    out = rrp.rebuild(
        arena_id="a1", feature_id="floor", hp_target=9000,
        materials_spent=9000 * COST_PER_HP_REBUILD,
        craft_skill=MIN_CRAFT_SKILL_REBUILD, now_seconds=10,
    )
    assert out.accepted is True
    assert out.new_hp == 6000   # 60% of 10000


def test_rebuild_below_skill_blocked():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=10000)
    out = rrp.rebuild(
        arena_id="a1", feature_id="floor", hp_target=4000,
        materials_spent=4000 * COST_PER_HP_REBUILD,
        craft_skill=MIN_CRAFT_SKILL_REBUILD - 1, now_seconds=10,
    )
    assert out.accepted is False


def test_rebuild_intact_blocked():
    env, rrp = _setup()
    out = rrp.rebuild(
        arena_id="a1", feature_id="floor", hp_target=4000,
        materials_spent=4000 * COST_PER_HP_REBUILD,
        craft_skill=MIN_CRAFT_SKILL_REBUILD, now_seconds=10,
    )
    assert out.accepted is False


def test_rebuild_costs_3x_repair():
    """COST_PER_HP_REBUILD is significantly higher."""
    assert COST_PER_HP_REBUILD == 3 * COST_PER_HP_REPAIR


def test_window_closed_blocks_repair():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=4000)
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=700,
    )
    assert out.accepted is False


def test_close_window():
    env, rrp = _setup()
    rrp.close_window(arena_id="a1")
    out = rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=500,
        materials_spent=500, craft_skill=70, now_seconds=10,
    )
    assert out.accepted is False


def test_repair_state_transitions_back_to_intact():
    env, rrp = _setup()
    env.apply_damage(arena_id="a1", feature_id="floor", amount=8000)
    rrp.repair(
        arena_id="a1", feature_id="floor", hp_amount=8000,
        materials_spent=8000, craft_skill=70, now_seconds=10,
    )
    state = env.state(arena_id="a1", feature_id="floor")
    assert state == FeatureState.INTACT
