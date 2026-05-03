"""Tests for dungeon generator."""
from __future__ import annotations

from server.dungeon_generator import (
    DungeonGenerator,
    DungeonTheme,
    MAX_ROOMS,
    MIN_ROOMS,
    RoomKind,
)


def test_generate_returns_dungeon():
    gen = DungeonGenerator()
    d = gen.generate(seed=42, theme=DungeonTheme.CRYPT)
    assert d is not None
    assert d.theme == DungeonTheme.CRYPT


def test_room_count_default():
    gen = DungeonGenerator(default_room_count=8)
    d = gen.generate(seed=1, theme=DungeonTheme.CAVE)
    assert len(d.rooms) == 8


def test_explicit_room_count():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.RUIN, room_count=12,
    )
    assert len(d.rooms) == 12


def test_room_count_clamped_min():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.CAVE, room_count=1,
    )
    assert len(d.rooms) == MIN_ROOMS


def test_room_count_clamped_max():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.CAVE,
        room_count=MAX_ROOMS + 100,
    )
    assert len(d.rooms) == MAX_ROOMS


def test_entrance_first_room():
    gen = DungeonGenerator()
    d = gen.generate(seed=1, theme=DungeonTheme.CAVE)
    assert d.rooms[0].kind == RoomKind.ENTRANCE
    assert d.entrance_room_id == "r0"


def test_boss_room_when_eligible():
    gen = DungeonGenerator(boss_min_rooms=5)
    d = gen.generate(
        seed=1, theme=DungeonTheme.CRYPT, room_count=8,
    )
    assert d.boss_room_id is not None
    assert d.rooms[-1].kind == RoomKind.BOSS


def test_no_boss_when_too_small():
    gen = DungeonGenerator(boss_min_rooms=10)
    d = gen.generate(
        seed=1, theme=DungeonTheme.CRYPT, room_count=5,
    )
    assert d.boss_room_id is None
    assert d.rooms[-1].kind == RoomKind.EXIT


def test_deterministic_for_same_seed():
    gen = DungeonGenerator()
    d1 = gen.generate(
        seed=12345, theme=DungeonTheme.CAVE, room_count=10,
    )
    d2 = gen.generate(
        seed=12345, theme=DungeonTheme.CAVE, room_count=10,
    )
    # Same kinds in same positions
    kinds_1 = tuple(r.kind for r in d1.rooms)
    kinds_2 = tuple(r.kind for r in d2.rooms)
    assert kinds_1 == kinds_2


def test_different_seeds_diverge():
    gen = DungeonGenerator()
    d1 = gen.generate(
        seed=1, theme=DungeonTheme.CAVE, room_count=15,
    )
    d2 = gen.generate(
        seed=999, theme=DungeonTheme.CAVE, room_count=15,
    )
    kinds_1 = tuple(r.kind for r in d1.rooms[1:-1])
    kinds_2 = tuple(r.kind for r in d2.rooms[1:-1])
    assert kinds_1 != kinds_2


def test_corridors_form_spine():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.CAVE, room_count=8,
    )
    spine = [c for c in d.corridors if c.corridor_id.startswith("c")]
    assert len(spine) == 7    # n-1 spine corridors


def test_theme_tags_propagate():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.FACTORY, room_count=5,
    )
    assert "automaton" in d.rooms[1].tags


def test_encounter_and_treasure_totals():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=42, theme=DungeonTheme.CRYPT, room_count=12,
    )
    sum_enc = sum(r.encounter_slots for r in d.rooms)
    sum_tre = sum(r.treasure_slots for r in d.rooms)
    assert d.total_encounter_slots == sum_enc
    assert d.total_treasure_slots == sum_tre


def test_each_room_has_unique_id():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=1, theme=DungeonTheme.CAVE, room_count=10,
    )
    ids = [r.room_id for r in d.rooms]
    assert len(ids) == len(set(ids))


def test_corridors_reference_existing_rooms():
    gen = DungeonGenerator()
    d = gen.generate(
        seed=42, theme=DungeonTheme.CAVE, room_count=15,
    )
    room_ids = {r.room_id for r in d.rooms}
    for c in d.corridors:
        assert c.from_room in room_ids
        assert c.to_room in room_ids


def test_all_themes_generate():
    gen = DungeonGenerator()
    for theme in DungeonTheme:
        d = gen.generate(seed=1, theme=theme, room_count=6)
        assert d.theme == theme
        assert len(d.rooms) == 6
