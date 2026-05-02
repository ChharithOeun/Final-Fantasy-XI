"""Recipe data — concrete material lists per Recipe Slip.

Each slip in `recipe_slip_registry` resolves to a list of
CraftRequirement entries via `materials_for_slip()`. The general
shape per slip:

  ILVL T0 (-> i-lvl 120)
    - bundle: all lvl-99 pieces in slot+archetype
    - 4x base material (cluster / cloth / ore depending on slot)
    - 1x key item drop (R/EX from elite mob)

  ILVL T1-T4 (-> i-lvl 125, 130, 135, 140)
    - bundle: all i-lvl-(99+5*tier) pieces in slot+archetype
    - 4x mid-tier material
    - 1x key item drop (R/EX, harder source per tier)

  ILVL T5-T11 (-> i-lvl 145..175)
    - 4x signature shard (Shadow Genkai boss-specific)
    - 4x shadow fragment (common cross-boss currency)
    - 1x key item drop (R/EX from named bosses)

  QUALITY +1..+4
    - 4x shadow fragment of corresponding tier
    - 1x R/EX polish material (drops from beastmen-stronghold NMs)

This module is **content data**, not engine logic. It can grow
without disturbing the engine surface. We seed it with full
coverage for one slot (HEAD) × three archetypes (CASTER, MELEE,
RANGER), proving the system end-to-end and giving the recipe
chart export something real to render.

Public surface
--------------
    materials_for_slip(slip_id) -> tuple[CraftRequirement, ...]
    has_recipe(slip_id) -> bool
    iter_known_slips() -> Iterator[str]
"""
from __future__ import annotations

import typing as t

from server.recipe_slip_registry import (
    SLIP_BY_ID,
    Archetype,
    Slot,
    TierAxis,
)
from server.synergy_workbench import CraftRequirement


# Bundle ID convention:
#   ilvl_<value>_<archetype>_<slot>_bundle
#       e.g. ilvl_99_caster_head_bundle
# Bundle requirements are flagged is_bundle=True; the synergy
# workbench knows to expand them against the player's inventory
# (which is implementation-specific to the inventory system).


def _ilvl_for_tier(tier: int) -> int:
    """ILVL inputs come from the tier BELOW the output. T0 takes
    lvl 99, T1 takes 104, T2 takes 109, etc. Final T4 takes 119
    (the canonical cap), then T5+ takes shadow currencies."""
    return 99 + 5 * tier


def _bundle_id(*, ilvl: int, archetype: Archetype, slot: Slot) -> str:
    return f"ilvl_{ilvl}_{archetype.value}_{slot.value}_bundle"


def _base_material_for_slot(slot: Slot) -> str:
    """Base craft material per slot. Mirrors canonical FFXI
    crafting (steel for body, leather for legs, etc.)."""
    return {
        Slot.HEAD: "fine_linen_cloth",
        Slot.BODY: "darksteel_ingot",
        Slot.HANDS: "wyvern_scales",
        Slot.LEGS: "tanned_dhalmel_leather",
        Slot.FEET: "tanned_buffalo_leather",
        Slot.NECK: "platinum_ingot",
        Slot.EARRING: "gold_ingot",
        Slot.RING: "platinum_ingot",
        Slot.BACK: "fine_linen_cloth",
        Slot.WAIST: "tanned_buffalo_leather",
    }[slot]


def _key_item_for_ilvl_tier(tier: int) -> str:
    """Each ILVL tier requires a different R/EX key-item drop.
    T0-T4 from elite Fomors; T5-T11 from Shadow Genkai bosses
    (matches the slip drop source map)."""
    if tier <= 1:
        return "fomor_warlord_signet"
    if tier <= 3:
        return "fomor_warlock_glyph"
    if tier == 4:
        return "fomor_inquisitor_seal"
    # T5-T11 each tied to one Shadow Genkai boss
    return {
        5: "khaavex_iceblood_token",
        6: "zharzag_hollow_token",
        7: "morrho_wordless_token",
        8: "skhalya_drowned_token",
        9: "trokhaeb_lantern_token",
        10: "kael_nox_forge_token",
        11: "asmodeus_voice_token",
    }[tier]


def _quality_polish_material(quality_step: int) -> str:
    """+1..+4 polish materials. R/EX drops from beastmen-stronghold
    NMs. Tradeable so newer toons can buy from AH."""
    return {
        1: "common_shadow_polish",
        2: "refined_shadow_polish",
        3: "pristine_shadow_polish",
        4: "eternal_shadow_polish",
    }[quality_step]


def _shadow_genkai_signature_shard(tier: int) -> str:
    """Each Shadow Genkai boss drops a unique signature shard."""
    return {
        5: "khaavex_signature_shard",
        6: "zharzag_signature_shard",
        7: "morrho_signature_shard",
        8: "skhalya_signature_shard",
        9: "trokhaeb_signature_shard",
        10: "kael_nox_signature_shard",
        11: "asmodeus_signature_shard",
    }[tier]


def _ilvl_recipe(
    *, slip_id: str, slot: Slot, archetype: Archetype,
    target_tier: int,
) -> tuple[CraftRequirement, ...]:
    base_mat = _base_material_for_slot(slot)
    key_item = _key_item_for_ilvl_tier(target_tier)

    if target_tier <= 4:
        # T0-T4: feed in old gear bundles + 4x base mat + key item
        input_ilvl = _ilvl_for_tier(target_tier)
        bundle = _bundle_id(
            ilvl=input_ilvl, archetype=archetype, slot=slot,
        )
        return (
            CraftRequirement(bundle, 1, is_bundle=True),
            CraftRequirement(base_mat, 4),
            CraftRequirement(key_item, 1),
        )
    # T5-T11: feed in shadow shards + fragments + key item
    return (
        CraftRequirement(_shadow_genkai_signature_shard(target_tier), 4),
        CraftRequirement("shadow_fragment_common", 4),
        CraftRequirement(key_item, 1),
    )


def _quality_recipe(
    *, slip_id: str, slot: Slot, archetype: Archetype,
    target_quality: int,
) -> tuple[CraftRequirement, ...]:
    polish = _quality_polish_material(target_quality)
    fragment_qty = 2 + target_quality   # +1 needs 3, +4 needs 6
    return (
        CraftRequirement("shadow_fragment_common", fragment_qty),
        CraftRequirement(polish, 1),
    )


# ---------------------------------------------------------------------
# Build the recipe table for HEAD x (CASTER, MELEE, RANGER) seed slice
# ---------------------------------------------------------------------
_SEEDED_SLOTS = (Slot.HEAD,)
_SEEDED_ARCHETYPES = (Archetype.CASTER, Archetype.MELEE, Archetype.RANGER)


def _build_recipe_table() -> dict[str, tuple[CraftRequirement, ...]]:
    out: dict[str, tuple[CraftRequirement, ...]] = {}
    for slip in SLIP_BY_ID.values():
        if slip.slot not in _SEEDED_SLOTS:
            continue
        if slip.archetype not in _SEEDED_ARCHETYPES:
            continue
        if slip.axis == TierAxis.ILVL:
            out[slip.slip_id] = _ilvl_recipe(
                slip_id=slip.slip_id,
                slot=slip.slot,
                archetype=slip.archetype,
                target_tier=slip.target_step,
            )
        else:
            out[slip.slip_id] = _quality_recipe(
                slip_id=slip.slip_id,
                slot=slip.slot,
                archetype=slip.archetype,
                target_quality=slip.target_step,
            )
    return out


_RECIPE_TABLE: dict[str, tuple[CraftRequirement, ...]] = _build_recipe_table()


def materials_for_slip(slip_id: str) -> tuple[CraftRequirement, ...]:
    """Return the material list for a slip. Empty tuple if no
    recipe is authored yet — callers should treat empty as
    'recipe coming in a content batch'."""
    return _RECIPE_TABLE.get(slip_id, ())


def has_recipe(slip_id: str) -> bool:
    return slip_id in _RECIPE_TABLE


def iter_known_slips() -> t.Iterator[str]:
    return iter(_RECIPE_TABLE.keys())


def seeded_slot_archetype_pairs() -> tuple[tuple[Slot, Archetype], ...]:
    """Reports which (slot, archetype) combos have full recipe
    coverage seeded. The recipe-coverage validator script uses
    this to know what to expect green vs. orange-flagged."""
    return tuple(
        (slot, arch)
        for slot in _SEEDED_SLOTS
        for arch in _SEEDED_ARCHETYPES
    )


__all__ = [
    "materials_for_slip",
    "has_recipe",
    "iter_known_slips",
    "seeded_slot_archetype_pairs",
]
