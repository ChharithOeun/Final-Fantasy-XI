"""BossRegistry — global catalog of deployable bosses.

Per BOSS_GRAMMAR.md '~50 cinematics across the world'. The registry
holds those bosses keyed by boss_id with reverse lookups for
encounter spawning.
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.mob_class_library import FamilyId

from .instance import DeployableBoss, validate_deployable


class BossRegistry:
    """Per-server registry of authored bosses."""

    def __init__(self) -> None:
        self._by_id: dict[str, DeployableBoss] = {}

    def register(self, boss: DeployableBoss,
                    *,
                    skip_validation: bool = False
                    ) -> None:
        """Add a boss. Raises ValueError on duplicate or invalid."""
        if boss.boss_id in self._by_id:
            raise ValueError(f"boss_id {boss.boss_id!r} already registered")
        if not skip_validation:
            complaints = validate_deployable(boss)
            if complaints:
                raise ValueError(
                    f"deployable {boss.boss_id} invalid: "
                    + "; ".join(complaints))
        self._by_id[boss.boss_id] = boss

    def unregister(self, boss_id: str) -> bool:
        return self._by_id.pop(boss_id, None) is not None

    def get(self, boss_id: str) -> t.Optional[DeployableBoss]:
        return self._by_id.get(boss_id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, boss_id: str) -> bool:
        return boss_id in self._by_id

    def all_bosses(self) -> tuple[DeployableBoss, ...]:
        return tuple(self._by_id.values())

    def by_nation(self, nation: str) -> tuple[DeployableBoss, ...]:
        return tuple(b for b in self._by_id.values()
                      if b.nation == nation)

    def by_family(self, family: FamilyId) -> tuple[DeployableBoss, ...]:
        return tuple(b for b in self._by_id.values()
                      if b.family == family)

    def by_level_band(self, *,
                          level_min: int,
                          level_max: int
                          ) -> tuple[DeployableBoss, ...]:
        if level_min > level_max:
            raise ValueError("level_min cannot exceed level_max")
        return tuple(
            b for b in self._by_id.values()
            if not (b.level_band[1] < level_min
                      or b.level_band[0] > level_max)
        )

    def hero_tier_bosses(self) -> tuple[DeployableBoss, ...]:
        """Hero-tier (per BOSS_GRAMMAR.md: 'Hero bosses are full
        Tier-3 generative agents')."""
        return tuple(b for b in self._by_id.values()
                      if b.recipe.body.is_hero_tier)


# Module-level singleton convenience.
_GLOBAL_REGISTRY = BossRegistry()


def global_registry() -> BossRegistry:
    return _GLOBAL_REGISTRY


def reset_global_registry() -> None:
    """For tests."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = BossRegistry()
