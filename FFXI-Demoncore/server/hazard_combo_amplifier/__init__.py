"""Hazard combo amplifier — hazards stack catastrophically.

A player on fire is dangerous. A player in water is
dangerous. A player on fire AND in water becomes a
STEAM EXPLOSION that damages everyone within 10 yalms.
A player carrying a charged lightning Aspir AND standing
on a metal floor is at risk of CONDUCTION CHAIN.

This module is a small rules engine. Author registers
ComboRules of the form:

    Combo(combo_id, when_present={tags}, fire_event,
          per_target_damage, radius_yalms, status_id,
          status_seconds, cooldown)

Players carry a "hazard_tag" set (managed by the combat
layer — fire, soaked, frozen, charged, soaked, oil_slick,
etc.). The amplifier checks each player's tag set against
all registered combos. If all `when_present` tags are
satisfied, the combo fires: damage to the player AND
adjacent players in radius, optional status, and a
cooldown so a single soaked-and-burning player isn't
exploding every tick.

Public surface
--------------
    HazardTag enum (canonical tags)
    Combo dataclass (frozen)
    ComboFireResult dataclass (frozen)
    HazardComboAmplifier
        .register_combo(combo) -> bool
        .set_player_tags(player_id, tags)
        .add_tag(player_id, tag)
        .remove_tag(player_id, tag)
        .clear_tags(player_id)
        .tags(player_id) -> set[HazardTag]
        .check(player_id, nearby_players, now_seconds)
            -> tuple[ComboFireResult, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HazardTag(str, enum.Enum):
    BURNING = "burning"
    SOAKED = "soaked"
    FROZEN = "frozen"
    CHARGED = "charged"
    OIL_SLICK = "oil_slick"
    BLEEDING = "bleeding"
    POISONED = "poisoned"
    METAL_GROUND = "metal_ground"


@dataclasses.dataclass(frozen=True)
class Combo:
    combo_id: str
    when_present: tuple[HazardTag, ...]
    label: str
    per_target_damage: int
    radius_yalms: int = 10
    status_id: t.Optional[str] = None
    status_seconds: int = 0
    cooldown_seconds: int = 8


@dataclasses.dataclass(frozen=True)
class ComboFireResult:
    combo_id: str
    label: str
    triggering_player_id: str
    affected_player_ids: tuple[str, ...]
    damage_per_target: int
    status_id: t.Optional[str]
    status_seconds: int
    fired_at: int


# Canonical combos shipped out of the box. Authors can
# extend by calling register_combo().
def _default_combos() -> tuple[Combo, ...]:
    return (
        Combo(
            combo_id="steam_explosion",
            when_present=(HazardTag.BURNING, HazardTag.SOAKED),
            label="STEAM EXPLOSION!",
            per_target_damage=600,
            radius_yalms=10,
            status_id="scalded",
            status_seconds=6,
        ),
        Combo(
            combo_id="ice_shatter",
            when_present=(HazardTag.FROZEN, HazardTag.BLEEDING),
            label="The frozen body shatters!",
            per_target_damage=400,
            radius_yalms=8,
        ),
        Combo(
            combo_id="conduction_chain",
            when_present=(HazardTag.CHARGED, HazardTag.METAL_GROUND),
            label="LIGHTNING ARCS THROUGH THE FLOOR!",
            per_target_damage=900,
            radius_yalms=15,
            status_id="paralysis",
            status_seconds=4,
        ),
        Combo(
            combo_id="oil_inferno",
            when_present=(HazardTag.OIL_SLICK, HazardTag.BURNING),
            label="The oil ignites!",
            per_target_damage=750,
            radius_yalms=12,
            status_id="burn",
            status_seconds=8,
        ),
        Combo(
            combo_id="frostbite_strip",
            when_present=(HazardTag.FROZEN, HazardTag.SOAKED),
            label="Frostbite spreads!",
            per_target_damage=300,
            radius_yalms=6,
            status_id="frost_sleep",
            status_seconds=4,
        ),
    )


@dataclasses.dataclass
class HazardComboAmplifier:
    _combos: dict[str, Combo] = dataclasses.field(default_factory=dict)
    _player_tags: dict[str, set[HazardTag]] = dataclasses.field(
        default_factory=dict,
    )
    _last_fired: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        for c in _default_combos():
            self._combos[c.combo_id] = c

    def register_combo(self, combo: Combo) -> bool:
        if not combo.combo_id or combo.combo_id in self._combos:
            return False
        if not combo.when_present:
            return False
        if combo.per_target_damage < 0:
            return False
        if combo.radius_yalms < 0:
            return False
        if combo.cooldown_seconds < 0:
            return False
        self._combos[combo.combo_id] = combo
        return True

    def set_player_tags(
        self, *, player_id: str, tags: t.Iterable[HazardTag],
    ) -> bool:
        if not player_id:
            return False
        self._player_tags[player_id] = set(tags)
        return True

    def add_tag(
        self, *, player_id: str, tag: HazardTag,
    ) -> bool:
        if not player_id:
            return False
        bag = self._player_tags.setdefault(player_id, set())
        if tag in bag:
            return False
        bag.add(tag)
        return True

    def remove_tag(
        self, *, player_id: str, tag: HazardTag,
    ) -> bool:
        bag = self._player_tags.get(player_id)
        if bag is None or tag not in bag:
            return False
        bag.discard(tag)
        return True

    def clear_tags(self, *, player_id: str) -> bool:
        if player_id in self._player_tags:
            self._player_tags[player_id].clear()
            return True
        return False

    def tags(self, *, player_id: str) -> set[HazardTag]:
        return set(self._player_tags.get(player_id, set()))

    def check(
        self, *, player_id: str,
        nearby_player_ids: t.Iterable[str] = (),
        now_seconds: int = 0,
    ) -> tuple[ComboFireResult, ...]:
        if not player_id:
            return ()
        tags = self._player_tags.get(player_id, set())
        if not tags:
            return ()
        out: list[ComboFireResult] = []
        for c in self._combos.values():
            if not all(t in tags for t in c.when_present):
                continue
            key = (player_id, c.combo_id)
            last = self._last_fired.get(key, -10**9)
            if (now_seconds - last) < c.cooldown_seconds:
                continue
            self._last_fired[key] = now_seconds
            affected = (player_id, *tuple(
                p for p in nearby_player_ids if p and p != player_id
            ))
            out.append(ComboFireResult(
                combo_id=c.combo_id,
                label=c.label,
                triggering_player_id=player_id,
                affected_player_ids=affected,
                damage_per_target=c.per_target_damage,
                status_id=c.status_id,
                status_seconds=c.status_seconds,
                fired_at=now_seconds,
            ))
        return tuple(out)

    def all_combos(self) -> tuple[Combo, ...]:
        return tuple(self._combos.values())


__all__ = [
    "HazardTag", "Combo", "ComboFireResult",
    "HazardComboAmplifier",
]
