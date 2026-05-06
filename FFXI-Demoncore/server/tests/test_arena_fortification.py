"""Tests for arena_fortification."""
from __future__ import annotations

from server.arena_fortification import (
    ArenaFortification,
    FortificationKind,
    MAX_FORT_PER_FEATURE,
    MIN_CRAFT_SKILL,
    MIN_ELEMENT_MULT_AFTER_GUARD,
)


def _open(arena_id="a1"):
    f = ArenaFortification()
    f.open_prep_window(
        arena_id=arena_id, opens_at=0, closes_at=600,
    )
    return f


def test_open_prep_window_happy():
    f = ArenaFortification()
    assert f.open_prep_window(
        arena_id="a1", opens_at=0, closes_at=600,
    ) is True


def test_invalid_window_blocked():
    f = ArenaFortification()
    assert f.open_prep_window(
        arena_id="a1", opens_at=600, closes_at=600,
    ) is False
    assert f.open_prep_window(
        arena_id="", opens_at=0, closes_at=600,
    ) is False


def test_submit_outside_window():
    f = _open()
    out = f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=5, craft_skill=80,
        now_seconds=601,
    )
    assert out.accepted is False


def test_submit_below_min_skill():
    f = _open()
    out = f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=5,
        craft_skill=MIN_CRAFT_SKILL - 1,
        now_seconds=100,
    )
    assert out.accepted is False


def test_submit_no_materials():
    f = _open()
    out = f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=0, craft_skill=80,
        now_seconds=100,
    )
    assert out.accepted is False


def test_hp_buff_increases_effective_hp():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=25, materials_spent=5, craft_skill=80,
        now_seconds=100,
    )
    eff = f.effective_hp_max(
        arena_id="a1", feature_id="floor", base_hp_max=10000,
        now_seconds=200,
    )
    assert eff == 12500


def test_hp_buff_stacks():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=10, materials_spent=5, craft_skill=80, now_seconds=110,
    )
    eff = f.effective_hp_max(
        arena_id="a1", feature_id="floor", base_hp_max=10000,
        now_seconds=200,
    )
    assert eff == 13000


def test_element_guard_reduces_damage_mult():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="ice", kind=FortificationKind.ELEMENT_GUARD,
        magnitude=70, element="fire", materials_spent=5, craft_skill=80,
        now_seconds=100,
    )
    eff = f.element_mult(
        arena_id="a1", feature_id="ice", element="fire",
        base=3.0, now_seconds=200,
    )
    # 3.0 × 0.30 = 0.90
    assert abs(eff - 0.90) < 0.01


def test_element_guard_floors_at_min():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="ice", kind=FortificationKind.ELEMENT_GUARD,
        magnitude=99, element="fire", materials_spent=5, craft_skill=80,
        now_seconds=100,
    )
    eff = f.element_mult(
        arena_id="a1", feature_id="ice", element="fire",
        base=0.05, now_seconds=200,
    )
    assert eff >= MIN_ELEMENT_MULT_AFTER_GUARD


def test_element_guard_wrong_element_no_effect():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="ice", kind=FortificationKind.ELEMENT_GUARD,
        magnitude=80, element="fire", materials_spent=5, craft_skill=80,
        now_seconds=100,
    )
    eff = f.element_mult(
        arena_id="a1", feature_id="ice", element="ice",
        base=1.0, now_seconds=200,
    )
    assert eff == 1.0


def test_element_guard_requires_element():
    f = _open()
    out = f.submit(
        arena_id="a1", feature_id="ice", kind=FortificationKind.ELEMENT_GUARD,
        magnitude=20, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    assert out.accepted is False


def test_break_delay_accumulates():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="bridge", kind=FortificationKind.BREAK_DELAY,
        magnitude=4, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    f.submit(
        arena_id="a1", feature_id="bridge", kind=FortificationKind.BREAK_DELAY,
        magnitude=3, materials_spent=5, craft_skill=80, now_seconds=110,
    )
    assert f.break_delay_seconds(
        arena_id="a1", feature_id="bridge", now_seconds=200,
    ) == 7


def test_crack_heal_per_second():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="hull", kind=FortificationKind.CRACK_HEAL,
        magnitude=15, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    assert f.crack_heal_per_second(
        arena_id="a1", feature_id="hull", now_seconds=200,
    ) == 15


def test_counter_grant_returned():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.COUNTER_GRANT,
        magnitude=1, counter_id="featherfall",
        materials_spent=5, craft_skill=80, now_seconds=100,
    )
    out = f.counter_grant(
        arena_id="a1", feature_id="floor", now_seconds=200,
    )
    assert out == "featherfall"


def test_counter_grant_requires_counter_id():
    f = _open()
    out = f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.COUNTER_GRANT,
        magnitude=1, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    assert out.accepted is False


def test_max_per_feature_blocks_overstack():
    f = _open()
    for i in range(MAX_FORT_PER_FEATURE):
        ok = f.submit(
            arena_id="a1", feature_id="floor",
            kind=FortificationKind.HP_BUFF,
            magnitude=5, materials_spent=5, craft_skill=80,
            now_seconds=100 + i,
        )
        assert ok.accepted is True
    out = f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=5, materials_spent=5, craft_skill=80, now_seconds=200,
    )
    assert out.accepted is False


def test_expired_forts_not_active():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=5, craft_skill=80,
        now_seconds=100, expires_at=500,
    )
    eff_active = f.effective_hp_max(
        arena_id="a1", feature_id="floor", base_hp_max=10000,
        now_seconds=200,
    )
    assert eff_active == 12000
    eff_after = f.effective_hp_max(
        arena_id="a1", feature_id="floor", base_hp_max=10000,
        now_seconds=600,
    )
    assert eff_after == 10000


def test_clear_arena_drops_all():
    f = _open()
    f.submit(
        arena_id="a1", feature_id="floor", kind=FortificationKind.HP_BUFF,
        magnitude=20, materials_spent=5, craft_skill=80, now_seconds=100,
    )
    f.clear_arena(arena_id="a1")
    eff = f.effective_hp_max(
        arena_id="a1", feature_id="floor", base_hp_max=10000,
    )
    assert eff == 10000
