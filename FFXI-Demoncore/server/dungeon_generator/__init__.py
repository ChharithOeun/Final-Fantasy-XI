"""Dungeon generator — procedural rooms, corridors, themes.

Procedurally produces a dungeon layout: rooms connected by
corridors, themed by biome (CRYPT / RUIN / CAVE / FACTORY /
ICE_HALL), with encounter slots, treasure slots, boss room,
and entry/exit anchors.

A dungeon is reproducible from its seed — given the same seed
and parameters, you get the same layout. That lets the world
deterministically reuse a generated dungeon across reboots
without persisting the geometry.

Public surface
--------------
    DungeonTheme enum
    RoomKind enum
    Room dataclass
    Corridor dataclass
    Dungeon dataclass
    DungeonGenerator
        .generate(seed, theme, room_count) -> Dungeon
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Bounds on dungeon size.
MIN_ROOMS = 3
MAX_ROOMS = 30
DEFAULT_ROOM_COUNT = 8


class DungeonTheme(str, enum.Enum):
    CRYPT = "crypt"
    RUIN = "ruin"
    CAVE = "cave"
    FACTORY = "factory"
    ICE_HALL = "ice_hall"
    SUNKEN_TEMPLE = "sunken_temple"


class RoomKind(str, enum.Enum):
    ENTRANCE = "entrance"
    NORMAL = "normal"
    ENCOUNTER = "encounter"
    TREASURE = "treasure"
    PUZZLE = "puzzle"
    BOSS = "boss"
    EXIT = "exit"


# Theme tag bundles — flavor for downstream systems
_THEME_TAGS: dict[DungeonTheme, tuple[str, ...]] = {
    DungeonTheme.CRYPT: ("undead", "dark", "tomb"),
    DungeonTheme.RUIN: ("collapsed", "ancient", "looted"),
    DungeonTheme.CAVE: ("rocky", "damp", "natural"),
    DungeonTheme.FACTORY: ("mechanical", "automaton", "steam"),
    DungeonTheme.ICE_HALL: ("frozen", "blizzard", "elven"),
    DungeonTheme.SUNKEN_TEMPLE: (
        "water", "sahagin", "submerged",
    ),
}


@dataclasses.dataclass(frozen=True)
class Room:
    room_id: str
    kind: RoomKind
    theme: DungeonTheme
    tags: tuple[str, ...]
    encounter_slots: int = 0    # how many mob spawn anchors
    treasure_slots: int = 0
    note: str = ""


@dataclasses.dataclass(frozen=True)
class Corridor:
    corridor_id: str
    from_room: str
    to_room: str
    has_trap: bool = False
    locked: bool = False


@dataclasses.dataclass(frozen=True)
class Dungeon:
    seed: int
    theme: DungeonTheme
    rooms: tuple[Room, ...]
    corridors: tuple[Corridor, ...]
    entrance_room_id: str
    exit_room_id: str
    boss_room_id: t.Optional[str] = None
    total_encounter_slots: int = 0
    total_treasure_slots: int = 0


@dataclasses.dataclass
class DungeonGenerator:
    default_room_count: int = DEFAULT_ROOM_COUNT
    trap_probability: float = 0.18
    locked_probability: float = 0.10
    boss_min_rooms: int = 5

    def generate(
        self, *, seed: int, theme: DungeonTheme,
        room_count: t.Optional[int] = None,
    ) -> Dungeon:
        n = room_count or self.default_room_count
        n = max(MIN_ROOMS, min(MAX_ROOMS, n))
        rng = random.Random(seed)
        tags = _THEME_TAGS[theme]

        rooms: list[Room] = []

        # Reserve special rooms
        rooms.append(Room(
            room_id="r0", kind=RoomKind.ENTRANCE,
            theme=theme, tags=tags + ("entry",),
            note="entry chamber",
        ))

        # Determine if dungeon supports a boss
        has_boss = n >= self.boss_min_rooms
        boss_id: t.Optional[str] = None
        exit_id = f"r{n - 1}"

        # Middle rooms
        encounter_slots_total = 0
        treasure_slots_total = 0
        for idx in range(1, n - 1):
            roll = rng.random()
            if roll < 0.45:
                kind = RoomKind.ENCOUNTER
                enc = rng.randint(2, 5)
                tre = 0
            elif roll < 0.7:
                kind = RoomKind.TREASURE
                enc = 0
                tre = rng.randint(1, 3)
            elif roll < 0.85:
                kind = RoomKind.PUZZLE
                enc = 0
                tre = rng.randint(0, 1)
            else:
                kind = RoomKind.NORMAL
                enc = rng.randint(0, 2)
                tre = 0
            rooms.append(Room(
                room_id=f"r{idx}", kind=kind,
                theme=theme, tags=tags,
                encounter_slots=enc,
                treasure_slots=tre,
            ))
            encounter_slots_total += enc
            treasure_slots_total += tre

        # Last room: exit (or boss if eligible)
        if has_boss:
            boss_id = exit_id
            rooms.append(Room(
                room_id=exit_id, kind=RoomKind.BOSS,
                theme=theme, tags=tags + ("boss",),
                encounter_slots=1,
                treasure_slots=2,
                note="boss chamber",
            ))
            encounter_slots_total += 1
            treasure_slots_total += 2
        else:
            rooms.append(Room(
                room_id=exit_id, kind=RoomKind.EXIT,
                theme=theme, tags=tags + ("exit",),
                note="exit",
            ))

        # Corridors: spine + a handful of side paths
        corridors: list[Corridor] = []
        # Spine: 0->1->2->...->n-1
        for idx in range(n - 1):
            corridors.append(Corridor(
                corridor_id=f"c{idx}",
                from_room=f"r{idx}",
                to_room=f"r{idx + 1}",
                has_trap=rng.random() < self.trap_probability,
                locked=rng.random() < self.locked_probability,
            ))
        # Optional shortcut(s) — only valid when there's room
        # for two non-adjacent middle rooms
        side_count = max(0, (n - 4) // 4)
        for sx in range(side_count):
            # Need a in [1, n-4] so that a+2 <= n-2
            if n < 6:
                break
            a = rng.randint(1, n - 4)
            b = rng.randint(a + 2, n - 2)
            corridors.append(Corridor(
                corridor_id=f"s{sx}",
                from_room=f"r{a}",
                to_room=f"r{b}",
                has_trap=rng.random() < self.trap_probability,
                locked=False,
            ))

        return Dungeon(
            seed=seed, theme=theme,
            rooms=tuple(rooms),
            corridors=tuple(corridors),
            entrance_room_id="r0",
            exit_room_id=exit_id,
            boss_room_id=boss_id,
            total_encounter_slots=encounter_slots_total,
            total_treasure_slots=treasure_slots_total,
        )


__all__ = [
    "MIN_ROOMS", "MAX_ROOMS", "DEFAULT_ROOM_COUNT",
    "DungeonTheme", "RoomKind",
    "Room", "Corridor", "Dungeon",
    "DungeonGenerator",
]
