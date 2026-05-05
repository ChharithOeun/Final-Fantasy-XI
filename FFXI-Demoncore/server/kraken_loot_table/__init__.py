"""Kraken loot table — boss drops weighted by phase damage.

When the Kraken is defeated, loot doesn't just dump on the
top damage dealer — it's distributed by which PHASES each
party contributed to. Killing the kraken in PHASE_1 pays
trivially because anyone can chip the SUBMERGED phase, but
ENRAGE_DEEP and BLEEDING_GOD are dangerous and pay the
keystone drops.

Loot tiers:
  ABYSSAL_FRAGMENT - common; drops from any contribution
  KRAKEN_INK       - mid; phases 2-3 contribution
  HOLLOW_PEARL     - rare; phase 3 contribution
  DROWNED_CROWN    - guaranteed; phase 4 contribution only
                     (only one party can hold it; goes to
                     the highest phase-4 damage dealer)

Contribution weighting:
  We track damage_by_phase per party. At loot resolution,
  rolls happen against the party that did the most damage
  in that phase. DROWNED_CROWN goes to ONE party — the one
  with the highest BLEEDING_GOD damage.

Public surface
--------------
    KrakenLootTier enum
    LootDrop dataclass
    KrakenLootTable
        .record_phase_damage(party_id, phase, dmg)
        .resolve_distribution(party_ids)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.kraken_world_boss import KrakenPhase


class KrakenLootTier(str, enum.Enum):
    ABYSSAL_FRAGMENT = "abyssal_fragment"
    KRAKEN_INK = "kraken_ink"
    HOLLOW_PEARL = "hollow_pearl"
    DROWNED_CROWN = "drowned_crown"


@dataclasses.dataclass(frozen=True)
class LootDrop:
    party_id: str
    tier: KrakenLootTier
    quantity: int = 1


@dataclasses.dataclass
class KrakenLootTable:
    # party_id -> phase -> total damage
    _damage: dict[str, dict[KrakenPhase, int]] = dataclasses.field(
        default_factory=dict,
    )

    def record_phase_damage(
        self, *, party_id: str,
        phase: KrakenPhase,
        dmg: int,
    ) -> bool:
        if not party_id or dmg <= 0:
            return False
        bucket = self._damage.setdefault(party_id, {})
        bucket[phase] = bucket.get(phase, 0) + dmg
        return True

    def damage_for(
        self, *, party_id: str, phase: KrakenPhase,
    ) -> int:
        return self._damage.get(party_id, {}).get(phase, 0)

    def _top_party_for_phase(
        self, *, phase: KrakenPhase,
    ) -> t.Optional[str]:
        best_party: t.Optional[str] = None
        best_dmg = 0
        for party_id, bucket in self._damage.items():
            dmg = bucket.get(phase, 0)
            if dmg > best_dmg:
                best_dmg = dmg
                best_party = party_id
        return best_party

    def resolve_distribution(
        self,
    ) -> tuple[LootDrop, ...]:
        """Compute drops based on recorded damage."""
        drops: list[LootDrop] = []
        # ABYSSAL_FRAGMENT: every party that did any damage gets one
        for party_id, bucket in self._damage.items():
            if any(v > 0 for v in bucket.values()):
                drops.append(LootDrop(
                    party_id=party_id,
                    tier=KrakenLootTier.ABYSSAL_FRAGMENT,
                ))
        # KRAKEN_INK: top party for INK_CLOUD or ENRAGE_DEEP
        ink_party = (
            self._top_party_for_phase(phase=KrakenPhase.INK_CLOUD)
            or self._top_party_for_phase(phase=KrakenPhase.ENRAGE_DEEP)
        )
        if ink_party is not None:
            drops.append(LootDrop(
                party_id=ink_party,
                tier=KrakenLootTier.KRAKEN_INK,
            ))
        # HOLLOW_PEARL: top party for ENRAGE_DEEP
        pearl_party = self._top_party_for_phase(
            phase=KrakenPhase.ENRAGE_DEEP,
        )
        if pearl_party is not None:
            drops.append(LootDrop(
                party_id=pearl_party,
                tier=KrakenLootTier.HOLLOW_PEARL,
            ))
        # DROWNED_CROWN: top party for BLEEDING_GOD only
        crown_party = self._top_party_for_phase(
            phase=KrakenPhase.BLEEDING_GOD,
        )
        if crown_party is not None:
            drops.append(LootDrop(
                party_id=crown_party,
                tier=KrakenLootTier.DROWNED_CROWN,
            ))
        return tuple(drops)


__all__ = [
    "KrakenLootTier", "LootDrop", "KrakenLootTable",
]
