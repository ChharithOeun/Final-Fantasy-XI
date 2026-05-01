"""Density budget — per-zone target counts + admission control.

Per AI_WORLD_DENSITY.md density targets (from the doc table):

    Tier              Bastok Markets   South Gustaberg   Castle Oztroja
    ----------------- ---------------- ----------------- ----------------
    0 - REACTIVE      ~200             ~500 (wildlife)    ~50
    1 - SCRIPTED_BARK  80 NPCs          30 mobs            150 mobs
    2 - REFLECTION     25                3                  5
    3 - HERO            4 (Cid+co)       0                  1 (Maat)
    4 - RL_POLICY       0               30 mobs            150 mobs

The budget enforces these targets so the server doesn't blow up when
a zone gets crowded. admit_entity() returns whether a new entity can
join; if a zone is over-budget for a tier, the request is denied.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .tier_classifier import AiTier


# Per-zone density targets pulled directly from the doc.
ZONE_DENSITY_TARGETS: dict[str, dict[AiTier, int]] = {
    "bastok_markets": {
        AiTier.REACTIVE: 200,
        AiTier.SCRIPTED_BARK: 80,
        AiTier.REFLECTION: 25,
        AiTier.HERO: 4,
        AiTier.RL_POLICY: 0,
    },
    "south_gustaberg": {
        AiTier.REACTIVE: 500,
        AiTier.SCRIPTED_BARK: 30,
        AiTier.REFLECTION: 3,
        AiTier.HERO: 0,
        AiTier.RL_POLICY: 30,
    },
    "castle_oztroja": {
        AiTier.REACTIVE: 50,
        AiTier.SCRIPTED_BARK: 150,
        AiTier.REFLECTION: 5,
        AiTier.HERO: 1,
        AiTier.RL_POLICY: 150,
    },
}


# Default per-tier targets for zones not explicitly listed.
DEFAULT_ZONE_TARGETS: dict[AiTier, int] = {
    AiTier.REACTIVE: 100,
    AiTier.SCRIPTED_BARK: 40,
    AiTier.REFLECTION: 5,
    AiTier.HERO: 0,
    AiTier.RL_POLICY: 30,
}


@dataclasses.dataclass
class DensitySnapshot:
    """Per-zone live tier counts."""
    zone: str
    counts: dict[AiTier, int] = dataclasses.field(default_factory=dict)


class DensityBudget:
    """Tracks per-zone tier admittance + enforces target ceilings."""

    def __init__(self) -> None:
        self._zones: dict[str, DensitySnapshot] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def admit(self,
                *,
                zone: str,
                tier: AiTier,
                entity_id: str) -> tuple[bool, str]:
        """Try to admit an entity into the zone at the given tier.
        Returns (admitted, reason). Caller passes entity_id only for
        logging — we don't track per-entity state here."""
        snapshot = self._zones.setdefault(zone, DensitySnapshot(zone=zone))
        target = self._target_for(zone, tier)
        current = snapshot.counts.get(tier, 0)
        if current >= target:
            return False, (f"zone {zone} tier {tier.name} at cap "
                              f"({current}/{target})")
        snapshot.counts[tier] = current + 1
        return True, ""

    def evict(self,
                *,
                zone: str,
                tier: AiTier) -> bool:
        """Remove one entity from the zone tier. Returns True if the
        count was decremented."""
        snapshot = self._zones.get(zone)
        if snapshot is None:
            return False
        current = snapshot.counts.get(tier, 0)
        if current <= 0:
            return False
        snapshot.counts[tier] = current - 1
        return True

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def current(self, *, zone: str) -> DensitySnapshot:
        return self._zones.setdefault(zone, DensitySnapshot(zone=zone))

    def remaining_capacity(self,
                              *,
                              zone: str,
                              tier: AiTier) -> int:
        snapshot = self._zones.setdefault(zone, DensitySnapshot(zone=zone))
        target = self._target_for(zone, tier)
        return max(0, target - snapshot.counts.get(tier, 0))

    def is_at_cap(self, *, zone: str, tier: AiTier) -> bool:
        return self.remaining_capacity(zone=zone, tier=tier) <= 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _target_for(zone: str, tier: AiTier) -> int:
        zone_targets = ZONE_DENSITY_TARGETS.get(zone.lower())
        if zone_targets is None:
            return DEFAULT_ZONE_TARGETS[tier]
        return zone_targets.get(tier, DEFAULT_ZONE_TARGETS[tier])


# Convenience module-level singletons for callers that don't want to
# pass a budget instance around.

_default_budget = DensityBudget()


def admit_entity(*,
                   zone: str,
                   tier: AiTier,
                   entity_id: str,
                   budget: t.Optional[DensityBudget] = None,
                   ) -> tuple[bool, str]:
    """Admit via the default singleton or a caller-supplied budget."""
    bud = budget or _default_budget
    return bud.admit(zone=zone, tier=tier, entity_id=entity_id)


def current_density(*,
                      zone: str,
                      budget: t.Optional[DensityBudget] = None,
                      ) -> DensitySnapshot:
    bud = budget or _default_budget
    return bud.current(zone=zone)
