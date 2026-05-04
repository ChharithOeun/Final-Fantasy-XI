"""Tests for the beastman mounts."""
from __future__ import annotations

from server.beastman_mounts import (
    BeastmanMounts,
    MountKind,
    SpecialTrait,
    TerrainAffinity,
)
from server.beastman_playable_races import BeastmanRace


def test_profile_for_iron_boar():
    m = BeastmanMounts()
    p = m.profile_for(mount_kind=MountKind.IRON_BOAR)
    assert p.race == BeastmanRace.ORC
    assert p.special_trait == SpecialTrait.CHARGE


def test_profile_for_coiler_water_affinity():
    m = BeastmanMounts()
    p = m.profile_for(mount_kind=MountKind.COILER)
    assert TerrainAffinity.SHALLOW_WATER in p.affinities


def test_profile_for_wing_strider_glide():
    m = BeastmanMounts()
    p = m.profile_for(
        mount_kind=MountKind.WING_STRIDER,
    )
    assert p.special_trait == SpecialTrait.GLIDE


def test_profile_for_stone_treader_load():
    m = BeastmanMounts()
    p = m.profile_for(
        mount_kind=MountKind.STONE_TREADER,
    )
    assert p.special_trait == SpecialTrait.LOAD


def test_acquire_correct_race():
    m = BeastmanMounts()
    assert m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )


def test_acquire_wrong_race_rejected():
    m = BeastmanMounts()
    assert not m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.WING_STRIDER,
    )


def test_acquire_double_rejected():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert not m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )


def test_can_ride_after_acquire():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert m.can_ride(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )


def test_cannot_ride_unacquired():
    m = BeastmanMounts()
    assert not m.can_ride(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )


def test_summon_returns_base_speed():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert speed == 140


def test_summon_affinity_bonus():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
        terrain=TerrainAffinity.FOREST,
    )
    # 140 + 20 = 160
    assert speed == 160


def test_summon_off_affinity_no_bonus():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
        terrain=TerrainAffinity.SHALLOW_WATER,
    )
    assert speed == 140


def test_summon_unacquired_returns_none():
    m = BeastmanMounts()
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert speed is None


def test_active_mount_set_after_summon():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert m.active_mount(
        player_id="alice",
    ) == MountKind.IRON_BOAR


def test_dismiss_clears():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    m.summon(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert m.dismiss(player_id="alice")
    assert m.active_mount(player_id="alice") is None


def test_dismiss_no_active_returns_false():
    m = BeastmanMounts()
    assert not m.dismiss(player_id="alice")


def test_acquired_for_lookup():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    acquired = m.acquired_for(player_id="alice")
    assert MountKind.IRON_BOAR in acquired


def test_lamia_water_speed_boost():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.LAMIA,
        mount_kind=MountKind.COILER,
    )
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.LAMIA,
        mount_kind=MountKind.COILER,
        terrain=TerrainAffinity.SHALLOW_WATER,
    )
    # 130 + 35 = 165
    assert speed == 165


def test_quadav_stone_treader_slow_baseline():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.QUADAV,
        mount_kind=MountKind.STONE_TREADER,
    )
    speed = m.summon(
        player_id="alice",
        race=BeastmanRace.QUADAV,
        mount_kind=MountKind.STONE_TREADER,
    )
    # Slowest baseline at 110
    assert speed == 110


def test_per_player_isolation():
    m = BeastmanMounts()
    m.acquire(
        player_id="alice",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
    assert not m.can_ride(
        player_id="bob",
        race=BeastmanRace.ORC,
        mount_kind=MountKind.IRON_BOAR,
    )
