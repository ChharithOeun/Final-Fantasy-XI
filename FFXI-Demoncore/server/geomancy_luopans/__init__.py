"""Geomancer indi/geo bubbles + luopan pets.

GEO has two spell families:

* Indi-spells — buff/debuff bubble that follows the GEO. Only
  one indi can be active at a time. Casting another indi
  replaces the previous.

* Geo-spells — same bubble effect, but anchored to a luopan
  pet that the GEO summons at the cast location. The luopan has
  HP and persists until dispelled or destroyed. The GEO can have
  at most ONE active luopan.

The bubble's effect tier scales with:
* base potency of the spell
* GEO's geomancy skill (+ handbell instrument bonus)
* indi vs geo (geo has 1.25x potency multiplier when on luopan)

Public surface
--------------
    GeoSpellFamily / GeoSpell / GEO_SPELL_CATALOG
    LuopanPet / IndiBubble dataclasses
    GeomancerState
        .cast_indi(spell, skill, instrument_bonus) -> CastResult
        .cast_geo(spell, location, skill, ...) -> CastResult
        .damage_luopan(amount) -> bool
        .clear_indi() / .recall_luopan()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


LUOPAN_BASE_HP = 600
LUOPAN_GEO_POTENCY_MULT = 125  # 1.25x as int percent


class GeoSpellFamily(str, enum.Enum):
    BARRIER = "barrier"     # phys def up / down
    PRECISION = "precision" # acc up / eva down
    REGEN = "regen"
    HASTE = "haste"
    REFRESH = "refresh"
    SLOW = "slow"
    PARALYSIS = "paralysis"
    FRAILTY = "frailty"     # def down
    LANGUOR = "languor"     # acc down
    ATTUNEMENT = "attunement"   # mdb up
    MALAISE = "malaise"     # mdb down
    TORPOR = "torpor"       # haste down


@dataclasses.dataclass(frozen=True)
class GeoSpell:
    spell_id: str
    family: GeoSpellFamily
    label: str
    base_potency: int
    is_buff: bool


GEO_SPELL_CATALOG: dict[str, GeoSpell] = {
    "indi_barrier": GeoSpell(
        "indi_barrier", GeoSpellFamily.BARRIER, "Indi-Barrier",
        base_potency=20, is_buff=True,
    ),
    "geo_barrier": GeoSpell(
        "geo_barrier", GeoSpellFamily.BARRIER, "Geo-Barrier",
        base_potency=20, is_buff=True,
    ),
    "indi_haste": GeoSpell(
        "indi_haste", GeoSpellFamily.HASTE, "Indi-Haste",
        base_potency=15, is_buff=True,
    ),
    "geo_haste": GeoSpell(
        "geo_haste", GeoSpellFamily.HASTE, "Geo-Haste",
        base_potency=15, is_buff=True,
    ),
    "indi_refresh": GeoSpell(
        "indi_refresh", GeoSpellFamily.REFRESH, "Indi-Refresh",
        base_potency=4, is_buff=True,
    ),
    "geo_refresh": GeoSpell(
        "geo_refresh", GeoSpellFamily.REFRESH, "Geo-Refresh",
        base_potency=4, is_buff=True,
    ),
    "indi_regen": GeoSpell(
        "indi_regen", GeoSpellFamily.REGEN, "Indi-Regen",
        base_potency=10, is_buff=True,
    ),
    "geo_frailty": GeoSpell(
        "geo_frailty", GeoSpellFamily.FRAILTY, "Geo-Frailty",
        base_potency=18, is_buff=False,
    ),
    "geo_languor": GeoSpell(
        "geo_languor", GeoSpellFamily.LANGUOR, "Geo-Languor",
        base_potency=15, is_buff=False,
    ),
    "geo_malaise": GeoSpell(
        "geo_malaise", GeoSpellFamily.MALAISE, "Geo-Malaise",
        base_potency=15, is_buff=False,
    ),
    "geo_torpor": GeoSpell(
        "geo_torpor", GeoSpellFamily.TORPOR, "Geo-Torpor",
        base_potency=10, is_buff=False,
    ),
}


def _is_geo(spell: GeoSpell) -> bool:
    return spell.spell_id.startswith("geo_")


def _is_indi(spell: GeoSpell) -> bool:
    return spell.spell_id.startswith("indi_")


@dataclasses.dataclass
class IndiBubble:
    spell_id: str
    family: GeoSpellFamily
    potency: int


@dataclasses.dataclass
class LuopanPet:
    spell_id: str
    family: GeoSpellFamily
    potency: int
    hp: int = LUOPAN_BASE_HP
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0


@dataclasses.dataclass(frozen=True)
class CastResult:
    accepted: bool
    bubble: t.Optional[IndiBubble] = None
    luopan: t.Optional[LuopanPet] = None
    overwrote_previous: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class GeomancerState:
    player_id: str
    indi_active: t.Optional[IndiBubble] = None
    luopan: t.Optional[LuopanPet] = None

    def _potency(self, spell: GeoSpell, *, skill: int,
                 instrument_bonus: int) -> int:
        base = spell.base_potency + skill // 50 + instrument_bonus
        if _is_geo(spell):
            base = (base * LUOPAN_GEO_POTENCY_MULT) // 100
        return base

    # ------------------------------------------------------------------
    # Indi-spell
    # ------------------------------------------------------------------
    def cast_indi(self, *, spell: GeoSpell, skill: int = 240,
                  instrument_bonus: int = 0) -> CastResult:
        if not _is_indi(spell):
            return CastResult(False, reason="not an indi-spell")
        prev = self.indi_active is not None
        bubble = IndiBubble(
            spell_id=spell.spell_id,
            family=spell.family,
            potency=self._potency(spell, skill=skill,
                                  instrument_bonus=instrument_bonus),
        )
        self.indi_active = bubble
        return CastResult(
            accepted=True, bubble=bubble, overwrote_previous=prev,
        )

    def clear_indi(self) -> bool:
        if self.indi_active is None:
            return False
        self.indi_active = None
        return True

    # ------------------------------------------------------------------
    # Geo-spell + luopan
    # ------------------------------------------------------------------
    def cast_geo(self, *, spell: GeoSpell,
                 location: tuple[float, float, float],
                 skill: int = 240,
                 instrument_bonus: int = 0) -> CastResult:
        if not _is_geo(spell):
            return CastResult(False, reason="not a geo-spell")
        prev = self.luopan is not None and self.luopan.is_alive
        new_pet = LuopanPet(
            spell_id=spell.spell_id,
            family=spell.family,
            potency=self._potency(spell, skill=skill,
                                  instrument_bonus=instrument_bonus),
            location=location,
        )
        self.luopan = new_pet
        return CastResult(
            accepted=True, luopan=new_pet, overwrote_previous=prev,
        )

    def damage_luopan(self, *, amount: int) -> bool:
        if self.luopan is None or not self.luopan.is_alive:
            return False
        self.luopan.hp = max(0, self.luopan.hp - amount)
        if not self.luopan.is_alive:
            self.luopan = None
        return True

    def recall_luopan(self) -> bool:
        if self.luopan is None:
            return False
        self.luopan = None
        return True


__all__ = [
    "LUOPAN_BASE_HP", "LUOPAN_GEO_POTENCY_MULT",
    "GeoSpellFamily", "GeoSpell", "GEO_SPELL_CATALOG",
    "IndiBubble", "LuopanPet", "CastResult",
    "GeomancerState",
]
