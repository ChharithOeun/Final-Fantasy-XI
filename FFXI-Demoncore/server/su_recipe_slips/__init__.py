"""Su recipe-slip catalog — what's needed to climb the Su5 ladder.

Each rung on the Su5 i-lvl ladder (built in `su_progression`) is
gated by a per-rung Recipe Slip plus a small bundle of materials.
The slip names exactly which slot/archetype/tier is being
attempted; the materials are the consumables fed into the bench
alongside the prior-tier Su gear (the "fuel").

Drop sources
------------
Su recipe slips drop from canonical Su content:

* Sortie bosses (Su2/Su3 territory) — common, low-tier slips
* Odyssey Sheol bosses (Su4 territory) — mid-tier slips
* Sheol Gaol gods + Su5 Gaol fights — high-tier (T6-T11) slips
* Domain Invasion / Wildskeeper Reives — open-world rare slips
* Coalition Imprimaturs vendor — purchasable BASE-tier slips
  (T0-T2 only, anti-monopoly safety net)

Weapons
-------
Weapon slips have an additional rarity multiplier — the canonical
"Su weapons mats are harder to acquire" rule. We model this by:

* Weapon slips drop at HALF the rate of armor slips of the same tier
* Weapon slips require an EXTRA two materials per tier (the
  "rare weapon-only mats")
* The material list always includes at least one direct-drop
  ingredient (anti-monopoly — see anti_monopoly_drops module)

Public surface
--------------
    SuSlipKind enum (i-lvl ladder rung)
    SuRecipeSlip dataclass
    SuRecipeSlipMaterials dataclass — bench cost beyond the slip
    SU_SLIP_CATALOG / SLIP_BY_ID
    slip_for(slot, archetype, tier) -> Optional[SuRecipeSlip]
    materials_for(slot, archetype, tier) -> SuRecipeSlipMaterials
    slips_from_source(source_id) -> tuple[SuRecipeSlip, ...]
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.su_progression import (
    SU_LADDER_TIERS,
    SuArchetype,
    SuKind,
    SuSlot,
    ilvl_for_su_tier,
    kind_for_slot,
)


# --------------------------------------------------------------------
# Drop-source assignment
# --------------------------------------------------------------------
# Tier 0 has no slip (the player just owns the Su5 piece directly
# from canonical drops — Sortie / Odyssey / Sheol). T1+ are the
# upgrade rungs, each with a designated slip drop source.

# Per-tier source mapping. Higher tiers come from harder content.
_ARMOR_SOURCE_BY_TIER: dict[int, str] = {
    1: "sortie_boss_low",                # Sortie wing 1
    2: "sortie_boss_mid",
    3: "sortie_boss_high",
    4: "odyssey_sheol_a_boss",
    5: "odyssey_sheol_b_boss",
    6: "odyssey_sheol_c_boss",
    7: "odyssey_sheol_d_boss",
    8: "odyssey_gaol_god_first",
    9: "odyssey_gaol_god_second",
    10: "odyssey_gaol_god_third",
    11: "odyssey_gaol_god_seventh",
}

# Weapons drop from a slightly different / rarer content lane —
# weapon slips come from extra-tough variants.
_WEAPON_SOURCE_BY_TIER: dict[int, str] = {
    1: "sortie_boss_mid",                # one tier higher than armor
    2: "sortie_boss_high",
    3: "odyssey_sheol_a_boss",
    4: "odyssey_sheol_b_boss",
    5: "odyssey_sheol_c_boss",
    6: "odyssey_sheol_d_boss",
    7: "odyssey_gaol_god_first",
    8: "odyssey_gaol_god_second",
    9: "odyssey_gaol_god_third",
    10: "odyssey_gaol_god_fourth",
    11: "odyssey_gaol_god_seventh",
}


# Coalition Imprimaturs vendor offers T1-T2 slips at fixed prices —
# anti-monopoly safety net so brand-new endgamers can climb rung 1.
COALITION_VENDOR_TIERS: frozenset[int] = frozenset({1, 2})


@dataclasses.dataclass(frozen=True)
class SuRecipeSlip:
    slip_id: str
    label: str
    slot: SuSlot
    archetype: SuArchetype
    target_tier: int               # the i-lvl tier this advances to (1..11)
    drop_source_id: str
    drop_rate_pct: float           # per-kill chance per drop slot

    @property
    def kind(self) -> SuKind:
        return kind_for_slot(self.slot)

    @property
    def target_ilvl(self) -> int:
        return ilvl_for_su_tier(self.target_tier)

    @property
    def is_vendor_purchasable(self) -> bool:
        return self.target_tier in COALITION_VENDOR_TIERS


@dataclasses.dataclass(frozen=True)
class MaterialEntry:
    """A single ingredient on a slip's recipe sheet."""
    material_id: str
    count: int = 1
    is_direct_drop: bool = True   # falsy = crafted-only (forbidden alone)


@dataclasses.dataclass(frozen=True)
class SuRecipeSlipMaterials:
    """The bench cost beyond the slip itself + the prior-tier Su
    fuel. These are consumables that drop from various world
    sources (anti-monopoly mandates each material has at least
    one direct-drop source — see `anti_monopoly_drops` module)."""
    slip_id: str
    materials: tuple[MaterialEntry, ...]


# --------------------------------------------------------------------
# Slip + material catalog
# --------------------------------------------------------------------
def _build_slip_for(
    slot: SuSlot, archetype: SuArchetype, tier: int,
) -> SuRecipeSlip:
    kind = kind_for_slot(slot)
    if kind == SuKind.WEAPON:
        source = _WEAPON_SOURCE_BY_TIER[tier]
        # Weapons drop at HALF the armor rate
        rate = 0.5 + (tier <= 4) * 0.5     # T1-T4 = 1.0%, T5+ = 0.5%
        rate = rate * 0.5
    else:
        source = _ARMOR_SOURCE_BY_TIER[tier]
        # T1-T4: 2% per kill / drop slot. T5+: 1%.
        rate = 2.0 if tier <= 4 else 1.0
    base_label = (
        f"{archetype.value.title()} {slot.value.replace('_', ' ').title()}"
    )
    return SuRecipeSlip(
        slip_id=f"slip_su_{archetype.value}_{slot.value}_t{tier}",
        label=(
            f"Su5 Recipe Slip: {base_label} -> T{tier}"
            f" (i-lvl {ilvl_for_su_tier(tier)})"
        ),
        slot=slot, archetype=archetype, target_tier=tier,
        drop_source_id=source, drop_rate_pct=rate,
    )


# Per-tier "core mat" — what every slip at this tier asks for.
_CORE_MAT_BY_TIER: dict[int, str] = {
    1: "shadow_dust",
    2: "shadow_dust",
    3: "shadow_resin",
    4: "shadow_resin",
    5: "ebon_filament",
    6: "ebon_filament",
    7: "voidstone_shard",
    8: "voidstone_shard",
    9: "voidstone_core",
    10: "voidstone_core",
    11: "godsblood_essence",
}


def _build_materials_for(
    slip: SuRecipeSlip,
) -> SuRecipeSlipMaterials:
    """Generate the material list for a given slip. Mat counts
    scale with tier; weapons get the extra two weapon-only mats."""
    core = MaterialEntry(
        material_id=_CORE_MAT_BY_TIER[slip.target_tier],
        count=max(1, slip.target_tier),     # T1=1, T2=2, ..., T11=11
        is_direct_drop=True,
    )
    # Slot-flavor mat — chosen so each archetype has thematic
    # ingredients. Always direct-drop for anti-monopoly compliance.
    flavor_id = f"essence_{slip.archetype.value}"
    flavor = MaterialEntry(
        material_id=flavor_id,
        count=1 + slip.target_tier // 3,    # 1 / 1 / 1 / 2 / 2 / 2 / 3 ...
        is_direct_drop=True,
    )
    mats: list[MaterialEntry] = [core, flavor]
    if slip.kind == SuKind.WEAPON:
        # Weapons demand TWO additional rare mats per tier.
        mats.append(MaterialEntry(
            material_id="weapon_grade_alloy",
            count=slip.target_tier,
            is_direct_drop=True,
        ))
        mats.append(MaterialEntry(
            material_id="weapon_grade_oil",
            count=max(1, slip.target_tier // 2),
            is_direct_drop=True,
        ))
    return SuRecipeSlipMaterials(
        slip_id=slip.slip_id, materials=tuple(mats),
    )


def _build_full_catalog() -> tuple[
    tuple[SuRecipeSlip, ...],
    dict[str, SuRecipeSlipMaterials],
]:
    slips: list[SuRecipeSlip] = []
    materials: dict[str, SuRecipeSlipMaterials] = {}
    for slot in SuSlot:
        for archetype in SuArchetype:
            for tier in range(1, SU_LADDER_TIERS):
                slip = _build_slip_for(slot, archetype, tier)
                slips.append(slip)
                materials[slip.slip_id] = _build_materials_for(slip)
    return tuple(slips), materials


SU_SLIP_CATALOG, _MATERIALS_BY_SLIP = _build_full_catalog()

SLIP_BY_ID: dict[str, SuRecipeSlip] = {
    s.slip_id: s for s in SU_SLIP_CATALOG
}


def slip_for(
    *, slot: SuSlot, archetype: SuArchetype, tier: int,
) -> t.Optional[SuRecipeSlip]:
    """Look up a slip by its semantic key."""
    for s in SU_SLIP_CATALOG:
        if (s.slot == slot and s.archetype == archetype
                and s.target_tier == tier):
            return s
    return None


def materials_for(
    *, slip_id: str,
) -> t.Optional[SuRecipeSlipMaterials]:
    return _MATERIALS_BY_SLIP.get(slip_id)


def slips_from_source(source_id: str) -> tuple[SuRecipeSlip, ...]:
    return tuple(
        s for s in SU_SLIP_CATALOG if s.drop_source_id == source_id
    )


def all_material_ids() -> frozenset[str]:
    """Every distinct material the catalog references — used by
    the anti_monopoly_drops validator."""
    out: set[str] = set()
    for slip_mats in _MATERIALS_BY_SLIP.values():
        for m in slip_mats.materials:
            out.add(m.material_id)
    return frozenset(out)


__all__ = [
    "SuRecipeSlip", "MaterialEntry", "SuRecipeSlipMaterials",
    "SU_SLIP_CATALOG", "SLIP_BY_ID", "COALITION_VENDOR_TIERS",
    "slip_for", "materials_for", "slips_from_source",
    "all_material_ids",
]
