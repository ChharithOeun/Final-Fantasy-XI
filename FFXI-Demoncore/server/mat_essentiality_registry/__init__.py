"""Mat essentiality registry — declares what's economically critical.

Not all items are equal. Iron ore is essential — half the crafts
need it. A Galkan-tribe ceremonial dagger is luxury — its absence
hurts no one. The economy regulator should aggressively boost
drop rates for ESSENTIAL items but leave the luxuries alone.

This module owns that classification. Each item gets:
* An EssentialityTier (CORE_BASIC / CRAFT_INPUT / CONSUMABLE /
  SPECIALTY / LUXURY)
* A priority weight (used by the regulator to rank scarce items)
* Tags for grouping (cloth, metal, food, alchemy, magic)
* Optional notes about why it matters

Tiers
-----
CORE_BASIC      Daily-use items every player needs. Cure potions,
                arrows, basic crystals. Strongest regulator boosts.
CRAFT_INPUT     Inputs to common crafts. Cloth, lumber, ore.
                Strong boosts when scarce.
CONSUMABLE      Items consumed during play but not strictly
                essential (food, drinks, status remedies).
                Modest boosts.
SPECIALTY       Niche but valued — specific craft inputs, NM mats.
                Light boosts.
LUXURY          Cosmetic / vanity / collector items. No boosts.

Public surface
--------------
    EssentialityTier enum
    EssentialMatEntry dataclass
    MatEssentialityRegistry
        .register(item_id, tier, ...)
        .tier_for(item_id) / .priority_for(item_id)
        .by_tier(tier) / .by_tag(tag)
        .priority_rank() — items sorted by priority desc
    seed_default_essentials()  — out-of-the-box list
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EssentialityTier(str, enum.Enum):
    CORE_BASIC = "core_basic"
    CRAFT_INPUT = "craft_input"
    CONSUMABLE = "consumable"
    SPECIALTY = "specialty"
    LUXURY = "luxury"


# Per-tier priority weight. Higher = regulator boosts more.
_TIER_PRIORITY: dict[EssentialityTier, int] = {
    EssentialityTier.CORE_BASIC: 100,
    EssentialityTier.CRAFT_INPUT: 75,
    EssentialityTier.CONSUMABLE: 50,
    EssentialityTier.SPECIALTY: 25,
    EssentialityTier.LUXURY: 0,
}


def priority_for_tier(tier: EssentialityTier) -> int:
    return _TIER_PRIORITY[tier]


@dataclasses.dataclass(frozen=True)
class EssentialMatEntry:
    item_id: str
    tier: EssentialityTier
    tags: frozenset[str] = frozenset()
    notes: str = ""

    @property
    def priority(self) -> int:
        return priority_for_tier(self.tier)


@dataclasses.dataclass
class MatEssentialityRegistry:
    _by_id: dict[str, EssentialMatEntry] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, item_id: str, tier: EssentialityTier,
        tags: t.Iterable[str] = (), notes: str = "",
    ) -> EssentialMatEntry:
        entry = EssentialMatEntry(
            item_id=item_id, tier=tier,
            tags=frozenset(tags), notes=notes,
        )
        self._by_id[item_id] = entry
        return entry

    def get(self, item_id: str) -> t.Optional[EssentialMatEntry]:
        return self._by_id.get(item_id)

    def tier_for(
        self, item_id: str,
    ) -> t.Optional[EssentialityTier]:
        e = self._by_id.get(item_id)
        return e.tier if e else None

    def priority_for(self, item_id: str) -> int:
        """Items not in the registry default to LUXURY priority
        (0) — they don't get regulator attention."""
        e = self._by_id.get(item_id)
        return e.priority if e else 0

    def by_tier(
        self, tier: EssentialityTier,
    ) -> tuple[EssentialMatEntry, ...]:
        return tuple(
            e for e in self._by_id.values() if e.tier == tier
        )

    def by_tag(self, tag: str) -> tuple[EssentialMatEntry, ...]:
        return tuple(
            e for e in self._by_id.values() if tag in e.tags
        )

    def priority_rank(self) -> tuple[EssentialMatEntry, ...]:
        return tuple(sorted(
            self._by_id.values(),
            key=lambda e: e.priority,
            reverse=True,
        ))

    def is_essential(self, item_id: str) -> bool:
        """Anything CORE_BASIC, CRAFT_INPUT, or CONSUMABLE counts
        as essential. SPECIALTY/LUXURY items don't."""
        e = self._by_id.get(item_id)
        if e is None:
            return False
        return e.tier in (
            EssentialityTier.CORE_BASIC,
            EssentialityTier.CRAFT_INPUT,
            EssentialityTier.CONSUMABLE,
        )

    def total(self) -> int:
        return len(self._by_id)


# --------------------------------------------------------------------
# Default seed — canonical FFXI essentials
# --------------------------------------------------------------------
_DEFAULT_ENTRIES: tuple[
    tuple[str, EssentialityTier, frozenset[str]], ...,
] = (
    # CORE_BASIC: things every player consumes regularly
    ("cure_potion", EssentialityTier.CORE_BASIC,
     frozenset({"alchemy", "consumable_heal"})),
    ("ether", EssentialityTier.CORE_BASIC,
     frozenset({"alchemy", "consumable_mana"})),
    ("arrows_basic", EssentialityTier.CORE_BASIC,
     frozenset({"woodworking", "ranged_ammo"})),
    ("crystal_fire", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_ice", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_wind", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_earth", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_lightning", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_water", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_light", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    ("crystal_dark", EssentialityTier.CORE_BASIC,
     frozenset({"crystal", "elemental"})),
    # CRAFT_INPUT: bulk inputs to many crafts
    ("iron_ore", EssentialityTier.CRAFT_INPUT,
     frozenset({"metal", "smithing"})),
    ("mythril_ore", EssentialityTier.CRAFT_INPUT,
     frozenset({"metal", "smithing"})),
    ("oak_lumber", EssentialityTier.CRAFT_INPUT,
     frozenset({"wood", "woodworking"})),
    ("ash_lumber", EssentialityTier.CRAFT_INPUT,
     frozenset({"wood", "woodworking"})),
    ("cotton_thread", EssentialityTier.CRAFT_INPUT,
     frozenset({"cloth", "clothcraft"})),
    ("silk_thread", EssentialityTier.CRAFT_INPUT,
     frozenset({"cloth", "clothcraft"})),
    ("linen_thread", EssentialityTier.CRAFT_INPUT,
     frozenset({"cloth", "clothcraft"})),
    ("dhalmel_leather", EssentialityTier.CRAFT_INPUT,
     frozenset({"leather", "leathercraft"})),
    ("ram_leather", EssentialityTier.CRAFT_INPUT,
     frozenset({"leather", "leathercraft"})),
    ("yagudo_feather", EssentialityTier.CRAFT_INPUT,
     frozenset({"misc"})),
    # CONSUMABLE: used during play but not strictly required
    ("apple_mint", EssentialityTier.CONSUMABLE,
     frozenset({"food", "agility"})),
    ("rolanberry_pie", EssentialityTier.CONSUMABLE,
     frozenset({"food", "magic"})),
    ("meat_jerky", EssentialityTier.CONSUMABLE,
     frozenset({"food", "physical"})),
    ("eye_drops", EssentialityTier.CONSUMABLE,
     frozenset({"alchemy", "remedy"})),
    ("antidote", EssentialityTier.CONSUMABLE,
     frozenset({"alchemy", "remedy"})),
    ("echo_drops", EssentialityTier.CONSUMABLE,
     frozenset({"alchemy", "remedy"})),
    # SPECIALTY: niche craft inputs / NM mats
    ("sturdy_wood_chips", EssentialityTier.SPECIALTY,
     frozenset({"woodworking"})),
    ("noble_wine", EssentialityTier.SPECIALTY,
     frozenset({"food"})),
    ("rosewood_lumber", EssentialityTier.SPECIALTY,
     frozenset({"wood", "high_tier"})),
    # LUXURY: vanity / collector
    ("decorative_egg", EssentialityTier.LUXURY,
     frozenset({"furnishing"})),
    ("painted_canvas", EssentialityTier.LUXURY,
     frozenset({"art"})),
    ("bonanza_marble", EssentialityTier.LUXURY,
     frozenset({"event"})),
)


def seed_default_essentials(
    registry: MatEssentialityRegistry,
) -> MatEssentialityRegistry:
    for item_id, tier, tags in _DEFAULT_ENTRIES:
        registry.register(item_id=item_id, tier=tier, tags=tags)
    return registry


__all__ = [
    "EssentialityTier", "priority_for_tier",
    "EssentialMatEntry", "MatEssentialityRegistry",
    "seed_default_essentials",
]
