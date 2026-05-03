"""Chocobo Woods — capture wild chocobos for breeding/mounted combat.

A new Demoncore zone hosting wild chocobo encounters at five
distinct biomes (each with its own breed lineage). Players
weaken a wild chocobo (no kills — they're not mobs that die,
they flee at low HP), then attempt to capture using:

    GREENS LURE — high-tier vegetable bait, slows the flee
    SOOTHING SONG — Bard-only ability with a capture-rate boost
    CALM TONIC — alchemy item that pacifies the bird

Capture chance scales with chocobo HP%, lure tier, and the
captor's CHR + Husbandry skill.

Captured chocobos feed into:
    chocobo_breeding — as new breeding stock
    mounted_combat   — as combat-trained mounts
    chocobo_digging  — as dig-specialty trainees

Public surface
--------------
    Biome enum (5 zones within Chocobo Woods)
    BreedLineage enum (Vana / Garlaige / Sandy etc — sample)
    WildChocoboEncounter dataclass
    LureKind enum
    capture_chance(...) -> float
    attempt_capture(...) -> CaptureResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import STREAM_LOOT_DROPS, RngPool


# ---------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------

class Biome(str, enum.Enum):
    SUNLIT_GLADE = "sunlit_glade"            # easy biome, most common breeds
    MOSS_HOLLOW = "moss_hollow"              # mid, herbivore-tank chocobos
    THORNED_THICKET = "thorned_thicket"      # mid-high, agility breeds
    SHADOW_RIDGE = "shadow_ridge"            # high, dark-aspect breeds
    SUN_PEAK = "sun_peak"                    # capstone, rare bloodline


class BreedLineage(str, enum.Enum):
    VANA_RIVER = "vana_river"          # blue blood — water/healing
    GARLAIGE = "garlaige"               # red blood — combat
    HALVUNG_FALL = "halvung_fall"      # green — speed
    NIGHTBLOOM = "nightbloom"          # black — dark-aspect, rare
    AURUM_PEAK = "aurum_peak"          # gold — capstone, all-round


class LureKind(str, enum.Enum):
    NONE = "none"                       # bare-handed, very low rate
    GREENS_LURE = "greens_lure"
    SOOTHING_SONG = "soothing_song"     # BRD-only
    CALM_TONIC = "calm_tonic"
    PRISTINE_LURE = "pristine_lure"     # rare-vendor / quest item


_BIOME_LINEAGES: dict[Biome, tuple[BreedLineage, ...]] = {
    Biome.SUNLIT_GLADE: (BreedLineage.VANA_RIVER, BreedLineage.GARLAIGE),
    Biome.MOSS_HOLLOW: (BreedLineage.VANA_RIVER, BreedLineage.HALVUNG_FALL),
    Biome.THORNED_THICKET: (
        BreedLineage.HALVUNG_FALL, BreedLineage.GARLAIGE,
    ),
    Biome.SHADOW_RIDGE: (BreedLineage.NIGHTBLOOM,),
    Biome.SUN_PEAK: (BreedLineage.AURUM_PEAK,),
}


def lineages_in(biome: Biome) -> tuple[BreedLineage, ...]:
    return _BIOME_LINEAGES.get(biome, ())


_LURE_BONUS: dict[LureKind, float] = {
    LureKind.NONE: 0.00,
    LureKind.GREENS_LURE: 0.20,
    LureKind.SOOTHING_SONG: 0.30,        # BRD has the best non-rare lure
    LureKind.CALM_TONIC: 0.25,
    LureKind.PRISTINE_LURE: 0.45,        # rare item, biggest bonus
}


_BIOME_DIFFICULTY: dict[Biome, float] = {
    Biome.SUNLIT_GLADE: 1.00,            # baseline
    Biome.MOSS_HOLLOW: 0.85,
    Biome.THORNED_THICKET: 0.70,
    Biome.SHADOW_RIDGE: 0.45,
    Biome.SUN_PEAK: 0.20,                # capstone — almost untameable
}


# ---------------------------------------------------------------------
# Encounter + capture
# ---------------------------------------------------------------------

@dataclasses.dataclass
class WildChocoboEncounter:
    encounter_id: str
    biome: Biome
    lineage: BreedLineage
    hp_pct: int = 100        # 0-100, hits 0 -> chocobo flees
    fled: bool = False
    captured: bool = False

    def damage(self, *, amount_pct: int) -> bool:
        if self.fled or self.captured:
            return False
        self.hp_pct = max(0, self.hp_pct - amount_pct)
        if self.hp_pct == 0:
            # Wild chocobos don't die — they flee at 0 HP unless
            # captured first.
            self.fled = True
        return True


def capture_chance(
    *, encounter: WildChocoboEncounter, lure: LureKind,
    chr_stat: int, husbandry_skill: int,
) -> float:
    if encounter.fled or encounter.captured:
        return 0.0
    biome_factor = _BIOME_DIFFICULTY[encounter.biome]
    lure_bonus = _LURE_BONUS[lure]
    # Lower HP -> higher capture chance.
    hp_factor = (100 - encounter.hp_pct) / 100.0
    # Stat bonus: each 30 CHR / 30 husbandry adds 1% baseline.
    stat_bonus = (chr_stat + husbandry_skill) / 3000.0
    chance = biome_factor * (0.10 + 0.50 * hp_factor + lure_bonus
                              + stat_bonus)
    return max(0.01, min(0.95, chance))


@dataclasses.dataclass(frozen=True)
class CaptureResult:
    accepted: bool
    captured: bool = False
    fled: bool = False
    chance_used: float = 0.0
    reason: t.Optional[str] = None


def attempt_capture(
    *, encounter: WildChocoboEncounter, lure: LureKind,
    chr_stat: int, husbandry_skill: int,
    rng_pool: RngPool,
) -> CaptureResult:
    if encounter.fled:
        return CaptureResult(False, fled=True, reason="chocobo fled")
    if encounter.captured:
        return CaptureResult(False, captured=True, reason="already captured")
    chance = capture_chance(
        encounter=encounter, lure=lure,
        chr_stat=chr_stat, husbandry_skill=husbandry_skill,
    )
    rng = rng_pool.stream(STREAM_LOOT_DROPS)
    roll = rng.random()
    if roll <= chance:
        encounter.captured = True
        return CaptureResult(
            accepted=True, captured=True, chance_used=chance,
        )
    # Failed capture spooks the bird — it loses 20% HP toward
    # eventual flee. (Chocobo can be re-attempted while above 0.)
    encounter.hp_pct = max(0, encounter.hp_pct - 20)
    if encounter.hp_pct == 0:
        encounter.fled = True
    return CaptureResult(
        accepted=True, captured=False, chance_used=chance,
        fled=encounter.fled,
    )


__all__ = [
    "Biome", "BreedLineage", "LureKind",
    "lineages_in",
    "WildChocoboEncounter",
    "CaptureResult",
    "capture_chance", "attempt_capture",
]
