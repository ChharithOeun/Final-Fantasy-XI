"""VR torch lighting — handheld light sources cast real light.

Crawl through Garlaige Citadel in VR holding a torch.
You hold up your right hand; the torch in that hand is
the brightest light source in your local rendering. Move
the torch left, the wall lights up. Lower it, the floor
illuminates. Drop it, the room goes dark — the torch is
on the ground but still burning, and the bats coming
toward you AREN'T silhouetted by your light any more.

Light kinds we recognize (defaults — modder can add more):
    TORCH       warm yellow-orange, 8m radius
    LANTERN     warmer, brighter, 12m radius
    GLOW_STONE  cold blue-white, 5m radius (no flicker)
    PHOSPHOR    BLM-cast, magenta, 6m, dramatic flicker

Each light has fuel_seconds — how long it stays lit.
0 = infinite (a glow stone). Otherwise it ticks down per
second of held time and goes out when fuel hits 0. Some
sources (LANTERN) accept refuel; others (TORCH) don't.

Light state per player:
    held_kind     which kind they're holding (None if empty)
    held_hand     LEFT or RIGHT
    fuel_remaining current fuel; -1 if infinite
    is_lit        bool

Aiming:
    aim_at(world_x, world_y, world_z) — the rendering
    layer's "where the light points" reference. The
    server doesn't simulate the actual lit-pixel set;
    we just track where the player has the torch pointed.

Public surface
--------------
    LightKind enum
    Hand enum
    LightSource dataclass (frozen) — catalog entry
    HeldLight dataclass (frozen) — current state per player
    VrTorchLighting
        .register_light_kind(kind, default_fuel_s, refuelable)
            -> bool
        .equip(player_id, kind, hand) -> bool
        .unequip(player_id) -> bool
        .aim_at(player_id, x, y, z) -> bool
        .tick(player_id, elapsed_seconds) -> None
        .refuel(player_id, fuel_s) -> bool
        .held(player_id) -> Optional[HeldLight]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LightKind(str, enum.Enum):
    TORCH = "torch"
    LANTERN = "lantern"
    GLOW_STONE = "glow_stone"
    PHOSPHOR = "phosphor"


class Hand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class LightSource:
    kind: LightKind
    radius_m: float
    color_temp_k: int
    flicker: bool
    refuelable: bool
    default_fuel_s: float  # -1 = infinite


@dataclasses.dataclass(frozen=True)
class HeldLight:
    player_id: str
    kind: LightKind
    hand: Hand
    fuel_remaining_s: float  # -1 if infinite
    is_lit: bool
    aim_x: float
    aim_y: float
    aim_z: float
    radius_m: float
    color_temp_k: int


_DEFAULT_LIGHTS: dict[LightKind, LightSource] = {
    LightKind.TORCH: LightSource(
        kind=LightKind.TORCH, radius_m=8.0,
        color_temp_k=2200, flicker=True,
        refuelable=False, default_fuel_s=900.0,  # 15 min
    ),
    LightKind.LANTERN: LightSource(
        kind=LightKind.LANTERN, radius_m=12.0,
        color_temp_k=2700, flicker=False,
        refuelable=True, default_fuel_s=1800.0,  # 30 min
    ),
    LightKind.GLOW_STONE: LightSource(
        kind=LightKind.GLOW_STONE, radius_m=5.0,
        color_temp_k=6500, flicker=False,
        refuelable=False, default_fuel_s=-1.0,
    ),
    LightKind.PHOSPHOR: LightSource(
        kind=LightKind.PHOSPHOR, radius_m=6.0,
        color_temp_k=4500, flicker=True,
        refuelable=False, default_fuel_s=120.0,  # 2 min
    ),
}


@dataclasses.dataclass
class _PlayerLight:
    kind: LightKind
    hand: Hand
    fuel_remaining: float
    aim_x: float = 0.0
    aim_y: float = 0.0
    aim_z: float = 0.0


@dataclasses.dataclass
class VrTorchLighting:
    _lights: dict[
        LightKind, LightSource,
    ] = dataclasses.field(
        default_factory=lambda: dict(_DEFAULT_LIGHTS),
    )
    _held: dict[str, _PlayerLight] = dataclasses.field(
        default_factory=dict,
    )

    def register_light_kind(
        self, *, source: LightSource,
    ) -> bool:
        """Add or replace a light catalog entry."""
        if source.radius_m <= 0:
            return False
        self._lights[source.kind] = source
        return True

    def equip(
        self, *, player_id: str,
        kind: LightKind, hand: Hand,
    ) -> bool:
        if not player_id:
            return False
        if kind not in self._lights:
            return False
        if player_id in self._held:
            return False
        src = self._lights[kind]
        self._held[player_id] = _PlayerLight(
            kind=kind, hand=hand,
            fuel_remaining=src.default_fuel_s,
        )
        return True

    def unequip(self, *, player_id: str) -> bool:
        if player_id not in self._held:
            return False
        del self._held[player_id]
        return True

    def aim_at(
        self, *, player_id: str,
        x: float, y: float, z: float,
    ) -> bool:
        if player_id not in self._held:
            return False
        h = self._held[player_id]
        h.aim_x = x
        h.aim_y = y
        h.aim_z = z
        return True

    def tick(
        self, *, player_id: str, elapsed_s: float,
    ) -> bool:
        if player_id not in self._held:
            return False
        if elapsed_s <= 0:
            return True
        h = self._held[player_id]
        # Infinite fuel: skip
        if h.fuel_remaining < 0:
            return True
        h.fuel_remaining = max(
            0.0, h.fuel_remaining - elapsed_s,
        )
        return True

    def refuel(
        self, *, player_id: str, fuel_s: float,
    ) -> bool:
        if player_id not in self._held:
            return False
        if fuel_s <= 0:
            return False
        h = self._held[player_id]
        src = self._lights[h.kind]
        if not src.refuelable:
            return False
        # Refuel can't exceed default
        h.fuel_remaining = min(
            src.default_fuel_s,
            h.fuel_remaining + fuel_s,
        )
        return True

    def held(
        self, *, player_id: str,
    ) -> t.Optional[HeldLight]:
        if player_id not in self._held:
            return None
        h = self._held[player_id]
        src = self._lights[h.kind]
        is_lit = (
            h.fuel_remaining < 0
            or h.fuel_remaining > 0
        )
        return HeldLight(
            player_id=player_id,
            kind=h.kind,
            hand=h.hand,
            fuel_remaining_s=h.fuel_remaining,
            is_lit=is_lit,
            aim_x=h.aim_x, aim_y=h.aim_y, aim_z=h.aim_z,
            radius_m=src.radius_m,
            color_temp_k=src.color_temp_k,
        )


__all__ = [
    "LightKind", "Hand", "LightSource", "HeldLight",
    "VrTorchLighting",
]
