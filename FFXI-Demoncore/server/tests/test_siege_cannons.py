"""Tests for siege_cannons."""
from __future__ import annotations

from server.siege_cannons import (
    AmmoKind, CannonSize, CrewRole, SiegeCannons,
)


def test_register_cannon_happy():
    s = SiegeCannons()
    assert s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT,
        arena_id="a1", band=2,
    ) is True


def test_register_dup_blocked():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    assert s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    ) is False


def test_assign_role_happy():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    assert s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    ) is True


def test_assign_invalid_role_for_size():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    # LIGHT only needs GUNNER
    assert s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.LOADER,
    ) is False


def test_assign_dup_role_blocked():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.HEAVY, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    )
    assert s.assign_role(
        cannon_id="c1", player_id="bob", role=CrewRole.GUNNER,
    ) is False


def test_one_role_per_player():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.HEAVY, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    )
    assert s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.LOADER,
    ) is False


def test_leave_role():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    )
    assert s.leave_role(cannon_id="c1", player_id="alice") is True


def test_fully_crewed_light_with_one():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    )
    assert s.fully_crewed(cannon_id="c1") is True


def test_fully_crewed_heavy_needs_three():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.HEAVY, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="a", role=CrewRole.GUNNER,
    )
    assert s.fully_crewed(cannon_id="c1") is False
    s.assign_role(
        cannon_id="c1", player_id="b", role=CrewRole.LOADER,
    )
    assert s.fully_crewed(cannon_id="c1") is False
    s.assign_role(
        cannon_id="c1", player_id="c", role=CrewRole.AIMER,
    )
    assert s.fully_crewed(cannon_id="c1") is True


def _light_ready():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="alice", role=CrewRole.GUNNER,
    )
    return s


def test_load_ammo_requires_full_crew():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.LIGHT, arena_id="a1",
    )
    assert s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=10,
    ) is False


def test_load_ammo_happy():
    s = _light_ready()
    assert s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=10,
    ) is True


def test_aim_at_feature_or_mob_only():
    s = _light_ready()
    assert s.aim(cannon_id="c1") is False
    assert s.aim(
        cannon_id="c1", target_feature_id="hull", target_mob_id="m1",
    ) is False
    assert s.aim(cannon_id="c1", target_feature_id="hull") is True


def test_fire_no_ammo():
    s = _light_ready()
    s.aim(cannon_id="c1", target_feature_id="hull")
    out = s.fire(cannon_id="c1", now_seconds=20)
    assert out.accepted is False


def test_fire_happy_path():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="hull")
    out = s.fire(cannon_id="c1", now_seconds=20)
    assert out.accepted is True
    assert out.damage == 800   # LIGHT base, no bonus
    assert out.element == "neutral"


def test_fire_round_shot_vs_hull_bonus():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="hull")
    out = s.fire(
        cannon_id="c1", now_seconds=20,
        target_feature_kind="ship_hull",
    )
    # +50% on ship_hull
    assert out.damage == 1200


def test_chain_shot_pillar_bonus():
    s = SiegeCannons()
    s.register_cannon(
        cannon_id="c1", size=CannonSize.MEDIUM, arena_id="a1",
    )
    s.assign_role(
        cannon_id="c1", player_id="a", role=CrewRole.LOADER,
    )
    s.assign_role(
        cannon_id="c1", player_id="b", role=CrewRole.GUNNER,
    )
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.CHAIN_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="pillar1")
    out = s.fire(
        cannon_id="c1", now_seconds=30,
        target_feature_kind="pillar",
    )
    # MEDIUM base 2200, +100% pillar = 4400
    assert out.damage == 4400


def test_fire_reload_cooldown():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="hull")
    s.fire(cannon_id="c1", now_seconds=10)
    # immediately can't load
    assert s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=11,
    ) is False
    # past reload (LIGHT = 12s)
    assert s.can_fire(cannon_id="c1", now_seconds=22) is True


def test_fire_resets_loaded_ammo():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.ROUND_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="hull")
    s.fire(cannon_id="c1", now_seconds=20)
    c = s.cannon(cannon_id="c1")
    assert c.loaded_ammo is None


def test_fire_shell_element():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.FIRE_SHELL, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_feature_id="ice")
    out = s.fire(
        cannon_id="c1", now_seconds=20,
        target_feature_kind="ice_sheet",
    )
    assert out.element == "fire"
    assert out.damage == 1200    # LIGHT 800 +50% bonus


def test_aim_at_mob():
    s = _light_ready()
    s.load_ammo(
        cannon_id="c1", ammo=AmmoKind.GRAPE_SHOT, now_seconds=0,
    )
    s.aim(cannon_id="c1", target_mob_id="boss1")
    out = s.fire(cannon_id="c1", now_seconds=20)
    assert out.accepted is True
    assert out.target_mob_id == "boss1"
    assert out.target_feature_id is None
