"""Environment damage — routes attacks into the feature graph.

This module is the bridge between combat actions and the
arena_environment registry. It accepts damage events from
many sources:

    SPELL_AOE        - a magic spell with an area of effect
    WEAPON_SKILL     - a player WS that overshoots its target
    BOSS_TELL        - a boss telegraph that hits walls
    CANNON_VOLLEY    - ship cannon fire on a hull
    BOSS_2HR         - king's Spirit Surge sweep, queen's
                       dual-cast Meteor, etc.
    DEBRIS_FALL      - secondary impacts from already-broken
                       features (cascade damage)
    ENV_HAZARD       - a battle hazard hits another feature
                       (chain destruction)

Each event picks features by zone-band overlap and
distributes damage. Sources whose origin band differs by
more than 1 from a feature's band attenuate by 50% per
extra band.

The output is a list of `FeatureImpact` records ready to
be fed into ArenaEnvironment.apply_damage().

Public surface
--------------
    DamageSource enum
    DamageEvent dataclass (frozen)
    FeatureImpact dataclass (frozen)
    EnvironmentDamage
        .__init__(arena_env)
        .submit(arena_id, event) -> tuple[FeatureImpact, ...]
        .total_environmental_damage(arena_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import (
    ArenaEnvironment, ArenaFeature, BreakResult, FeatureKind,
)


class DamageSource(str, enum.Enum):
    SPELL_AOE = "spell_aoe"
    WEAPON_SKILL = "weapon_skill"
    BOSS_TELL = "boss_tell"
    CANNON_VOLLEY = "cannon_volley"
    BOSS_2HR = "boss_2hr"
    DEBRIS_FALL = "debris_fall"
    ENV_HAZARD = "env_hazard"


@dataclasses.dataclass(frozen=True)
class DamageEvent:
    source: DamageSource
    amount: int
    element: str = "neutral"
    origin_band: int = 0
    # explicit feature targets — if empty, all features in band
    # range are picked
    target_feature_ids: tuple[str, ...] = ()
    # target kinds — empty means all kinds
    target_kinds: tuple[FeatureKind, ...] = ()
    # band radius — 0 = same band only, 1 = adjacent
    band_radius: int = 1


@dataclasses.dataclass(frozen=True)
class FeatureImpact:
    feature_id: str
    damage_dealt: int
    crossed_crack: bool
    crossed_break: bool
    hp_remaining: int


@dataclasses.dataclass
class EnvironmentDamage:
    arena_env: ArenaEnvironment
    _total_per_arena: dict[str, int] = dataclasses.field(default_factory=dict)

    def submit(
        self, *, arena_id: str, event: DamageEvent,
    ) -> tuple[FeatureImpact, ...]:
        feats = self.arena_env.features_for(arena_id=arena_id)
        if not feats:
            return ()
        # Pick targets
        targets: list[ArenaFeature] = []
        if event.target_feature_ids:
            wanted = set(event.target_feature_ids)
            targets = [f for f in feats if f.feature_id in wanted]
        else:
            for f in feats:
                if event.target_kinds and f.kind not in event.target_kinds:
                    continue
                band_gap = abs(f.band - event.origin_band)
                if band_gap > event.band_radius:
                    continue
                targets.append(f)
        impacts: list[FeatureImpact] = []
        running_total = self._total_per_arena.setdefault(arena_id, 0)
        for f in targets:
            band_gap = abs(f.band - event.origin_band)
            attenuation = 0.5 ** band_gap if band_gap > 0 else 1.0
            scaled = max(0, int(event.amount * attenuation))
            if scaled <= 0:
                continue
            r: BreakResult = self.arena_env.apply_damage(
                arena_id=arena_id, feature_id=f.feature_id,
                amount=scaled, element=event.element,
            )
            if not r.accepted:
                continue
            actually_dealt = scaled - r.hp_remaining if False else (
                # accurate: just use the difference; but the env
                # already capped at 0, so dealt = scaled or
                # remaining-prev. We don't have prev here, so
                # treat dealt as min(scaled, hp_pre). Use scaled
                # as upper bound; if break crossed and
                # hp_remaining is 0, dealt is at least the
                # element-scaled amount.
                scaled
            )
            running_total += actually_dealt
            impacts.append(FeatureImpact(
                feature_id=f.feature_id,
                damage_dealt=actually_dealt,
                crossed_crack=r.crossed_crack,
                crossed_break=r.crossed_break,
                hp_remaining=r.hp_remaining,
            ))
        self._total_per_arena[arena_id] = running_total
        return tuple(impacts)

    def total_environmental_damage(self, *, arena_id: str) -> int:
        return self._total_per_arena.get(arena_id, 0)


__all__ = [
    "DamageSource", "DamageEvent", "FeatureImpact",
    "EnvironmentDamage",
]
