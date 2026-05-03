"""Anti-monopoly drop policy + recipe validator.

User mandate: crafters cannot corner the materials market. They
already make money from selling crafts and hiring out their
craft skill, so MATS must drop directly to players — not be
exclusively craftable.

This module enforces that with two layers:

1. A registry of every material referenced anywhere in the game's
   recipes, paired with the world sources that DROP it directly.
2. A validator that walks recipe sheets (Su slips today, Ambuscade
   slips tomorrow, eventually all crafts) and asserts every input
   material has at least one direct-drop source.

If a recipe sneaks in a "crafted-only" material — a synth output
that can't be obtained any other way — that's a monopoly hook,
and the validator fails.

Design principles
-----------------
* Materials are first-class entities with a small metadata blob:
  rarity, primary drop source, optional vendor fallback.
* Every material has at least ONE non-craft source. Crafters CAN
  still produce it (great for them, makes the craft skill useful)
  but cannot be the only path.
* The vendor fallback (Coalition Imprimaturs / NPC merchants) is
  the safety net for new players who don't have access to the
  drop content yet.

Public surface
--------------
    DropSourceKind enum (mob / boss / instance / vendor / chest)
    DropSource dataclass — single concrete world source
    MaterialRegistryEntry dataclass — a material + its sources
    ANTI_MONOPOLY_REGISTRY  — the master table
    register_material(...) — for tests / programmatic registration
    has_direct_drop(material_id) -> bool
    sources_for(material_id) -> tuple[DropSource, ...]
    validate_recipe(material_ids) -> ValidationReport
    audit_su_slip_catalog() -> ValidationReport
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.su_recipe_slips import (
    SU_SLIP_CATALOG,
    materials_for,
)


class DropSourceKind(str, enum.Enum):
    MOB = "mob"                 # regular mob in zone
    BOSS = "boss"               # named boss / NM
    INSTANCE = "instance"       # instanced content (Sortie/Odyssey/etc)
    OPEN_WORLD = "open_world"   # WildKeeper / Domain Invasion
    VENDOR = "vendor"           # NPC sale (Coalition Imprimaturs)
    CHEST = "chest"             # field chest / coffer
    GATHER = "gather"           # mining / harvesting / fishing /
                                #   excavation / chocobo digging


# Source kinds the validator counts as "direct drop" — i.e. NOT
# the result of a synth. Vendor counts as direct because the
# anti-monopoly rule allows shop fallbacks for accessibility.
DIRECT_DROP_KINDS: frozenset[DropSourceKind] = frozenset({
    DropSourceKind.MOB,
    DropSourceKind.BOSS,
    DropSourceKind.INSTANCE,
    DropSourceKind.OPEN_WORLD,
    DropSourceKind.VENDOR,
    DropSourceKind.CHEST,
    DropSourceKind.GATHER,
})


@dataclasses.dataclass(frozen=True)
class DropSource:
    source_id: str
    kind: DropSourceKind
    drop_rate_pct: float = 1.0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class MaterialRegistryEntry:
    material_id: str
    sources: tuple[DropSource, ...]
    can_also_be_crafted: bool = False

    def has_direct_drop(self) -> bool:
        return any(
            s.kind in DIRECT_DROP_KINDS for s in self.sources
        )


@dataclasses.dataclass(frozen=True)
class ValidationReport:
    ok: bool
    missing_direct_drop: tuple[str, ...]
    unregistered: tuple[str, ...]
    total_materials_checked: int

    def summary(self) -> str:
        if self.ok:
            return (
                f"OK: {self.total_materials_checked} materials "
                f"checked, all have direct-drop sources."
            )
        lines = [
            f"FAIL: {self.total_materials_checked} materials checked",
        ]
        if self.missing_direct_drop:
            lines.append(
                "  missing direct-drop sources: "
                + ", ".join(self.missing_direct_drop)
            )
        if self.unregistered:
            lines.append(
                "  unregistered materials: "
                + ", ".join(self.unregistered)
            )
        return "\n".join(lines)


# --------------------------------------------------------------------
# Registry construction
# --------------------------------------------------------------------
_REGISTRY: dict[str, MaterialRegistryEntry] = {}


def register_material(
    *, material_id: str,
    sources: t.Iterable[DropSource],
    can_also_be_crafted: bool = False,
) -> MaterialRegistryEntry:
    entry = MaterialRegistryEntry(
        material_id=material_id,
        sources=tuple(sources),
        can_also_be_crafted=can_also_be_crafted,
    )
    _REGISTRY[material_id] = entry
    return entry


def has_direct_drop(material_id: str) -> bool:
    e = _REGISTRY.get(material_id)
    return bool(e and e.has_direct_drop())


def sources_for(material_id: str) -> tuple[DropSource, ...]:
    e = _REGISTRY.get(material_id)
    return e.sources if e else ()


def is_registered(material_id: str) -> bool:
    return material_id in _REGISTRY


def all_registered() -> frozenset[str]:
    return frozenset(_REGISTRY)


def validate_recipe(
    material_ids: t.Iterable[str],
) -> ValidationReport:
    """Check that every material in the list has at least one
    direct-drop source. Returns a report — caller decides what
    to do with failures."""
    ids = list(material_ids)
    missing: list[str] = []
    unregistered: list[str] = []
    for mid in ids:
        if not is_registered(mid):
            unregistered.append(mid)
            continue
        if not has_direct_drop(mid):
            missing.append(mid)
    return ValidationReport(
        ok=not missing and not unregistered,
        missing_direct_drop=tuple(sorted(set(missing))),
        unregistered=tuple(sorted(set(unregistered))),
        total_materials_checked=len(set(ids)),
    )


def audit_su_slip_catalog() -> ValidationReport:
    """Sweep the entire Su slip catalog and verify every referenced
    material has a registered direct-drop source. This is the
    canonical anti-monopoly gate — call it from CI."""
    all_mats: set[str] = set()
    for slip in SU_SLIP_CATALOG:
        slip_mats = materials_for(slip_id=slip.slip_id)
        if slip_mats is None:
            continue
        for m in slip_mats.materials:
            all_mats.add(m.material_id)
    return validate_recipe(all_mats)


# --------------------------------------------------------------------
# Default material registry — every Su slip material seeded
# --------------------------------------------------------------------
def _seed_default_registry() -> None:
    # Core tier mats — drop from canonical Sortie / Odyssey / Sheol
    # bosses. Each gets at least one BOSS source plus an OPEN_WORLD
    # fallback so the supply isn't bottlenecked on a single boss
    # spawn. Crafters MAY also synth them — but the direct-drop
    # supply means the AH price has a floor.
    register_material(
        material_id="shadow_dust",
        sources=(
            DropSource("fomor_elite_warlord", DropSourceKind.MOB,
                       drop_rate_pct=8.0),
            DropSource("sortie_boss_low", DropSourceKind.BOSS,
                       drop_rate_pct=15.0),
            DropSource("coalition_imprimaturs_vendor",
                       DropSourceKind.VENDOR,
                       notes="20 imprimaturs"),
        ),
        can_also_be_crafted=True,
    )
    register_material(
        material_id="shadow_resin",
        sources=(
            DropSource("fomor_elite_warlock", DropSourceKind.MOB,
                       drop_rate_pct=6.0),
            DropSource("sortie_boss_high", DropSourceKind.BOSS,
                       drop_rate_pct=10.0),
        ),
        can_also_be_crafted=True,
    )
    register_material(
        material_id="ebon_filament",
        sources=(
            DropSource("odyssey_sheol_a_boss", DropSourceKind.BOSS,
                       drop_rate_pct=5.0),
            DropSource("wildskeeper_reive_zombie",
                       DropSourceKind.OPEN_WORLD,
                       drop_rate_pct=15.0,
                       notes="contribution-based"),
        ),
        can_also_be_crafted=True,
    )
    register_material(
        material_id="voidstone_shard",
        sources=(
            DropSource("odyssey_sheol_c_boss", DropSourceKind.BOSS,
                       drop_rate_pct=3.0),
            DropSource("domain_invasion_zombie_dragon",
                       DropSourceKind.OPEN_WORLD,
                       drop_rate_pct=20.0,
                       notes="weekly persistent contribution"),
        ),
        # NOT craftable — capstone-tier mat. Open-world supply
        # keeps the AH price stable.
        can_also_be_crafted=False,
    )
    register_material(
        material_id="voidstone_core",
        sources=(
            DropSource("odyssey_gaol_god_first", DropSourceKind.BOSS,
                       drop_rate_pct=2.0),
            DropSource("domain_invasion_zombie_dragon",
                       DropSourceKind.OPEN_WORLD,
                       drop_rate_pct=5.0),
        ),
        can_also_be_crafted=False,
    )
    register_material(
        material_id="godsblood_essence",
        sources=(
            DropSource("odyssey_gaol_god_seventh",
                       DropSourceKind.BOSS,
                       drop_rate_pct=1.0,
                       notes="capstone — only the 7th god drops"),
            DropSource("automaton_swarm_trial_world_first",
                       DropSourceKind.INSTANCE,
                       drop_rate_pct=10.0,
                       notes="world-first only"),
        ),
        can_also_be_crafted=False,
    )

    # Archetype-flavor mats — drop from job-themed mobs / NMs.
    flavor_sources = {
        "essence_caster": ("yagudo_oracle_nm", DropSourceKind.MOB),
        "essence_melee": ("orc_warlord_nm", DropSourceKind.MOB),
        "essence_ranger": ("quadav_ranger_nm", DropSourceKind.MOB),
        "essence_ninja": ("shadow_clan_ninja_nm", DropSourceKind.MOB),
        "essence_blue_mage": ("psychomancer_nm", DropSourceKind.BOSS),
        "essence_puppet": ("rogue_automaton_nm", DropSourceKind.BOSS),
        "essence_beast": ("primal_beast_nm", DropSourceKind.MOB),
        "essence_dancer": ("siren_nm", DropSourceKind.MOB),
        "essence_rune": ("rune_titan_nm", DropSourceKind.BOSS),
    }
    for mat_id, (source, kind) in flavor_sources.items():
        register_material(
            material_id=mat_id,
            sources=(
                DropSource(source, kind, drop_rate_pct=12.0),
                DropSource(
                    "coalition_imprimaturs_vendor",
                    DropSourceKind.VENDOR,
                    notes="50 imprimaturs",
                ),
            ),
            can_also_be_crafted=False,
        )

    # Weapon-only mats — alloy + oil. Weapons are intentionally
    # harder so these come from harder sources, but still drop.
    register_material(
        material_id="weapon_grade_alloy",
        sources=(
            DropSource("odyssey_sheol_b_boss", DropSourceKind.BOSS,
                       drop_rate_pct=4.0),
            DropSource("mining_zone_zitah", DropSourceKind.GATHER,
                       drop_rate_pct=10.0,
                       notes="rare mining proc"),
        ),
        can_also_be_crafted=True,
    )
    register_material(
        material_id="weapon_grade_oil",
        sources=(
            DropSource("odyssey_sheol_b_boss", DropSourceKind.BOSS,
                       drop_rate_pct=6.0),
            DropSource("chocobo_digging_marjami",
                       DropSourceKind.GATHER,
                       drop_rate_pct=2.0),
        ),
        can_also_be_crafted=True,
    )


_seed_default_registry()


__all__ = [
    "DropSourceKind", "DropSource",
    "DIRECT_DROP_KINDS",
    "MaterialRegistryEntry", "ValidationReport",
    "register_material", "has_direct_drop",
    "sources_for", "is_registered", "all_registered",
    "validate_recipe", "audit_su_slip_catalog",
]
