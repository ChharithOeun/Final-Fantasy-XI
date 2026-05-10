"""Destructible props — destroyable scenery system.

Bandit raids in Bastok Markets are not bandits running
through static scenery; they are bandits *cracking* the
scenery as they go. A barrel takes a great-axe swing and
splinters into wood debris. An oil barrel takes a thunder
spell and detonates, throwing fire damage to every
neighboring crate within three meters, which catch fire
themselves and chain to the cloth awning above the spice
stall, which ignites and drops a curtain of ash. That
cascade is what this module computes.

Every destructible has an armor class (WOOD, MASONRY,
GLASS, METAL, CRATE_LIGHT, BARREL_OIL, CLOTH_AWNING) with
default HP, a fracture pattern (CRACK, SHATTER, EXPLODE,
TOPPLE, BURN), a debris budget, and a replaces_with prop
id pointing at the broken-variant dressing piece. Damage
calls return the cascade list — every prop that actually
broke from the impact, in order, including chained
explosions. Showcase choreography hooks the cascade into
the bandit-raid beat: a single great-axe stroke at frame 0
cracks four crates, ignites two, and sets the awning
falling at frame 90.

Path-blocking is a downstream concern: when a prop with
can_block_path=True breaks, it rolls debris into the lane
and the navmesh can re-bake. That's handled elsewhere; this
module emits the FractureEvent and trusts the consumer.

Public surface
--------------
    ArmorClass enum
    FracturePattern enum
    Element enum
    DestructibleProp dataclass (frozen)
    FractureEvent dataclass (frozen)
    DestructiblePropSystem
"""
from __future__ import annotations

import dataclasses
import enum


class ArmorClass(enum.Enum):
    WOOD = "wood"
    MASONRY = "masonry"
    GLASS = "glass"
    METAL = "metal"
    CRATE_LIGHT = "crate_light"
    BARREL_OIL = "barrel_oil"
    CLOTH_AWNING = "cloth_awning"


class FracturePattern(enum.Enum):
    CRACK = "crack"
    SHATTER = "shatter"
    EXPLODE = "explode"
    TOPPLE = "topple"
    BURN = "burn"


class Element(enum.Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    EARTH = "earth"
    WATER = "water"
    WIND = "wind"
    ICE = "ice"
    LIGHTNING = "lightning"
    LIGHT = "light"
    DARK = "dark"


_DEFAULT_HP: dict[ArmorClass, int] = {
    ArmorClass.WOOD: 50,
    ArmorClass.MASONRY: 200,
    ArmorClass.GLASS: 10,
    ArmorClass.METAL: 500,
    ArmorClass.CRATE_LIGHT: 15,
    ArmorClass.BARREL_OIL: 8,
    ArmorClass.CLOTH_AWNING: 5,
}

_DEFAULT_PATTERN: dict[ArmorClass, FracturePattern] = {
    ArmorClass.WOOD: FracturePattern.CRACK,
    ArmorClass.MASONRY: FracturePattern.SHATTER,
    ArmorClass.GLASS: FracturePattern.SHATTER,
    ArmorClass.METAL: FracturePattern.TOPPLE,
    ArmorClass.CRATE_LIGHT: FracturePattern.CRACK,
    ArmorClass.BARREL_OIL: FracturePattern.EXPLODE,
    ArmorClass.CLOTH_AWNING: FracturePattern.BURN,
}

_DEFAULT_DEBRIS_COUNT: dict[ArmorClass, int] = {
    ArmorClass.WOOD: 8,
    ArmorClass.MASONRY: 14,
    ArmorClass.GLASS: 12,
    ArmorClass.METAL: 4,
    ArmorClass.CRATE_LIGHT: 6,
    ArmorClass.BARREL_OIL: 18,
    ArmorClass.CLOTH_AWNING: 4,
}

_DEFAULT_DEBRIS_LIFETIME: dict[ArmorClass, float] = {
    ArmorClass.WOOD: 4.0,
    ArmorClass.MASONRY: 6.0,
    ArmorClass.GLASS: 3.5,
    ArmorClass.METAL: 5.0,
    ArmorClass.CRATE_LIGHT: 3.0,
    ArmorClass.BARREL_OIL: 5.0,
    ArmorClass.CLOTH_AWNING: 4.0,
}


# How far an oil barrel explosion reaches (in meters) and
# the fire damage it deals to neighbors.
BARREL_EXPLOSION_RADIUS_M = 3.0
BARREL_EXPLOSION_DAMAGE = 30
PROPAGATABLE = frozenset({
    ArmorClass.CRATE_LIGHT,
    ArmorClass.CLOTH_AWNING,
    ArmorClass.WOOD,
    ArmorClass.BARREL_OIL,  # chains
})


# Weapon class -> what it CAN destroy. Some props need
# heavy weaponry: a wooden crate falls to anything, but
# masonry walls only crack under great-axe / great-sword
# / heavy magic. Cloth ignites from anything fire.
_WEAPON_CAN_DESTROY: dict[str, frozenset[ArmorClass]] = {
    "sword": frozenset({
        ArmorClass.WOOD, ArmorClass.GLASS,
        ArmorClass.CRATE_LIGHT, ArmorClass.BARREL_OIL,
        ArmorClass.CLOTH_AWNING,
    }),
    "great_sword": frozenset({a for a in ArmorClass}),
    "axe": frozenset({
        ArmorClass.WOOD, ArmorClass.GLASS,
        ArmorClass.CRATE_LIGHT, ArmorClass.BARREL_OIL,
        ArmorClass.CLOTH_AWNING, ArmorClass.MASONRY,
    }),
    "great_axe": frozenset({a for a in ArmorClass}),
    "h2h": frozenset({
        ArmorClass.WOOD, ArmorClass.GLASS,
        ArmorClass.CRATE_LIGHT, ArmorClass.CLOTH_AWNING,
    }),
    "dagger": frozenset({
        ArmorClass.GLASS, ArmorClass.CLOTH_AWNING,
    }),
    "bow": frozenset({
        ArmorClass.GLASS, ArmorClass.CLOTH_AWNING,
        ArmorClass.BARREL_OIL,
    }),
    "gun": frozenset({a for a in ArmorClass
                      if a != ArmorClass.METAL}),
    "club": frozenset({
        ArmorClass.WOOD, ArmorClass.GLASS,
        ArmorClass.MASONRY, ArmorClass.CRATE_LIGHT,
        ArmorClass.BARREL_OIL, ArmorClass.CLOTH_AWNING,
    }),
    "staff": frozenset({
        ArmorClass.WOOD, ArmorClass.GLASS,
        ArmorClass.CRATE_LIGHT, ArmorClass.CLOTH_AWNING,
    }),
}


@dataclasses.dataclass(frozen=True)
class DestructibleProp:
    prop_id: str
    source_dressing_id: str
    hp: int
    armor_class: ArmorClass
    fracture_pattern: FracturePattern
    debris_count: int
    debris_lifetime_s: float
    sound_event_id: str
    particle_emit_id: str
    replaces_with: str
    can_block_path: bool
    fire_propagates: bool


@dataclasses.dataclass(frozen=True)
class FractureEvent:
    prop_id: str
    pattern: FracturePattern
    debris_count: int
    debris_lifetime_s: float
    replaces_with: str
    sound_event_id: str
    particle_emit_id: str


@dataclasses.dataclass
class DestructiblePropSystem:
    _props: dict[str, DestructibleProp] = dataclasses.field(
        default_factory=dict,
    )
    # current HP (mutable)
    _hp: dict[str, int] = dataclasses.field(default_factory=dict)
    # Zone membership: prop_id -> zone_id
    _zone_of: dict[str, str] = dataclasses.field(default_factory=dict)
    # Spatial proximity for cascade: prop_id -> set of
    # neighbor prop_ids within explosion radius.
    _neighbors: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)
    _destroyed: set[str] = dataclasses.field(default_factory=set)

    # ------------------------------------------------- register
    def register_prop(
        self,
        prop_id: str,
        source_dressing_id: str,
        armor: ArmorClass,
        custom_hp: int | None = None,
        zone_id: str = "",
        replaces_with: str | None = None,
        can_block_path: bool = False,
        fire_propagates: bool | None = None,
        sound_event_id: str | None = None,
        particle_emit_id: str | None = None,
    ) -> DestructibleProp:
        if not prop_id:
            raise ValueError("prop_id required")
        if prop_id in self._props:
            raise ValueError(
                f"duplicate prop_id: {prop_id}",
            )
        hp = custom_hp if custom_hp is not None else (
            _DEFAULT_HP[armor]
        )
        if hp <= 0:
            raise ValueError("hp must be > 0")
        prop = DestructibleProp(
            prop_id=prop_id,
            source_dressing_id=source_dressing_id,
            hp=hp,
            armor_class=armor,
            fracture_pattern=_DEFAULT_PATTERN[armor],
            debris_count=_DEFAULT_DEBRIS_COUNT[armor],
            debris_lifetime_s=_DEFAULT_DEBRIS_LIFETIME[armor],
            sound_event_id=(
                sound_event_id
                or f"sfx_break_{armor.value}"
            ),
            particle_emit_id=(
                particle_emit_id
                or _default_particle_for(armor)
            ),
            replaces_with=(
                replaces_with or f"{source_dressing_id}_broken"
            ),
            can_block_path=can_block_path,
            fire_propagates=(
                fire_propagates
                if fire_propagates is not None
                else (armor in PROPAGATABLE)
            ),
        )
        self._props[prop_id] = prop
        self._hp[prop_id] = hp
        if zone_id:
            self._zone_of[prop_id] = zone_id
        self._neighbors.setdefault(prop_id, set())
        return prop

    def link_neighbors(
        self, a: str, b: str,
    ) -> None:
        """Wire two props as within explosion radius. Used by
        the bandit-raid setup so the showcase knows which
        crates chain when the oil barrel goes up."""
        if a not in self._props or b not in self._props:
            raise KeyError("unknown prop in link")
        if a == b:
            raise ValueError("can't link prop to itself")
        self._neighbors.setdefault(a, set()).add(b)
        self._neighbors.setdefault(b, set()).add(a)

    def get(self, prop_id: str) -> DestructibleProp:
        if prop_id not in self._props:
            raise KeyError(f"unknown prop: {prop_id}")
        return self._props[prop_id]

    def hp(self, prop_id: str) -> int:
        if prop_id not in self._hp:
            raise KeyError(f"unknown prop: {prop_id}")
        return self._hp[prop_id]

    def is_destroyed(self, prop_id: str) -> bool:
        return prop_id in self._destroyed

    # ------------------------------------------------- damage
    def damage(
        self,
        prop_id: str,
        hp_delta: int,
        element: Element = Element.PHYSICAL,
    ) -> list[str]:
        """Apply damage. Returns the list of prop_ids that
        broke as a result, in cascade order. Already-destroyed
        props are no-ops (return [])."""
        if prop_id not in self._props:
            raise KeyError(f"unknown prop: {prop_id}")
        if hp_delta <= 0:
            raise ValueError("hp_delta must be > 0")
        if prop_id in self._destroyed:
            return []
        cascade: list[str] = []
        self._apply_damage(prop_id, hp_delta, element, cascade)
        return cascade

    def _apply_damage(
        self,
        prop_id: str,
        dmg: int,
        element: Element,
        cascade: list[str],
    ) -> None:
        if prop_id in self._destroyed:
            return
        # Cloth awning ignites doubly to fire.
        prop = self._props[prop_id]
        eff_dmg = dmg
        if (
            element == Element.FIRE
            and prop.armor_class == ArmorClass.CLOTH_AWNING
        ):
            eff_dmg = dmg * 2
        # Glass shatters faster under any non-physical hit.
        if (
            prop.armor_class == ArmorClass.GLASS
            and element != Element.PHYSICAL
        ):
            eff_dmg = max(eff_dmg, prop.hp)
        new_hp = self._hp[prop_id] - eff_dmg
        if new_hp > 0:
            self._hp[prop_id] = new_hp
            return
        # Destroyed.
        self._hp[prop_id] = 0
        self._destroyed.add(prop_id)
        cascade.append(prop_id)
        # Cascade for oil barrels: deal fire damage to all
        # propagatable neighbors within radius.
        if prop.armor_class == ArmorClass.BARREL_OIL:
            for neighbor in sorted(
                self._neighbors.get(prop_id, set())
            ):
                if neighbor in self._destroyed:
                    continue
                neighbor_prop = self._props[neighbor]
                if neighbor_prop.fire_propagates:
                    self._apply_damage(
                        neighbor, BARREL_EXPLOSION_DAMAGE,
                        Element.FIRE, cascade,
                    )

    def fracture_event(self, prop_id: str) -> FractureEvent:
        prop = self.get(prop_id)
        return FractureEvent(
            prop_id=prop_id,
            pattern=prop.fracture_pattern,
            debris_count=prop.debris_count,
            debris_lifetime_s=prop.debris_lifetime_s,
            replaces_with=prop.replaces_with,
            sound_event_id=prop.sound_event_id,
            particle_emit_id=prop.particle_emit_id,
        )

    def props_in_zone(
        self, zone_id: str,
    ) -> tuple[DestructibleProp, ...]:
        return tuple(
            sorted(
                (
                    self._props[pid]
                    for pid, zid in self._zone_of.items()
                    if zid == zone_id
                ),
                key=lambda p: p.prop_id,
            )
        )

    def can_be_destroyed_by(
        self, prop_id: str, weapon_class: str,
    ) -> bool:
        prop = self.get(prop_id)
        wc = weapon_class.lower()
        if wc not in _WEAPON_CAN_DESTROY:
            return False
        return prop.armor_class in _WEAPON_CAN_DESTROY[wc]

    def all_prop_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._props.keys()))

    def prop_count(self) -> int:
        return len(self._props)


def _default_particle_for(armor: ArmorClass) -> str:
    if armor == ArmorClass.WOOD:
        return "debris_wood"
    if armor == ArmorClass.MASONRY:
        return "debris_stone"
    if armor == ArmorClass.GLASS:
        return "debris_stone"
    if armor == ArmorClass.METAL:
        return "spark_metal_heavy"
    if armor == ArmorClass.CRATE_LIGHT:
        return "debris_wood"
    if armor == ArmorClass.BARREL_OIL:
        return "ember_storm"
    if armor == ArmorClass.CLOTH_AWNING:
        return "ember_drift"
    return "smoke_burst"


__all__ = [
    "ArmorClass",
    "FracturePattern",
    "Element",
    "DestructibleProp",
    "FractureEvent",
    "DestructiblePropSystem",
    "BARREL_EXPLOSION_RADIUS_M",
    "BARREL_EXPLOSION_DAMAGE",
]
