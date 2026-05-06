"""Environment cascade — break events trigger downstream breaks.

A single broken feature isn't always the end of the
story. A pillar that supports the ceiling, when it falls,
weakens that ceiling. A wall whose collapse pulls down a
section of bridge connected to it. A dam that bursts and
melts the ice sheet downstream. This module wires those
upstream-downstream relationships and propagates damage.

A CascadeRule says: when SOURCE feature crosses BREAK
(or CRACK), apply FOLLOWUP_DAMAGE to TARGET feature with
TARGET_ELEMENT and DELAY_SECONDS. Multiple rules can fire
from one source (a falling pillar can damage 3 nearby
features at once). Cascades themselves can fire MORE
cascades — but every chain has a depth limit so a
catastrophic fight ending in total arena collapse is
authored, not accidental.

Public surface
--------------
    CascadeTrigger enum
    CascadeRule dataclass (frozen)
    CascadeStep dataclass (frozen)
    EnvironmentCascade
        .__init__(arena_env, environment_damage)
        .register_rule(rule) -> bool
        .on_break(arena_id, source_feature_id,
                  source_kind, now_seconds) -> tuple[CascadeStep,...]
        .on_crack(arena_id, source_feature_id,
                  source_kind, now_seconds) -> tuple[CascadeStep,...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import ArenaEnvironment, FeatureKind
from server.environment_damage import (
    DamageEvent, DamageSource, EnvironmentDamage,
)


class CascadeTrigger(str, enum.Enum):
    ON_BREAK = "on_break"
    ON_CRACK = "on_crack"


# Hard cap on cascade depth so a single break can't take
# the whole arena down by accident. Author can tune per
# rule, but the engine will not exceed this.
MAX_CASCADE_DEPTH = 4


@dataclasses.dataclass(frozen=True)
class CascadeRule:
    rule_id: str
    trigger: CascadeTrigger
    source_feature_id: str
    target_feature_id: str
    followup_damage: int
    target_element: str = "neutral"
    delay_seconds: int = 0
    depth_budget: int = 2   # this rule can chain at most N more times


@dataclasses.dataclass(frozen=True)
class CascadeStep:
    rule_id: str
    source_feature_id: str
    target_feature_id: str
    damage_dealt: int
    crossed_crack: bool
    crossed_break: bool
    depth: int
    fired_at: int


@dataclasses.dataclass
class EnvironmentCascade:
    arena_env: ArenaEnvironment
    environment_damage: EnvironmentDamage
    _rules: dict[tuple[CascadeTrigger, str], list[CascadeRule]] = (
        dataclasses.field(default_factory=dict)
    )

    def register_rule(self, rule: CascadeRule) -> bool:
        if not rule.rule_id or not rule.source_feature_id:
            return False
        if not rule.target_feature_id:
            return False
        if rule.followup_damage <= 0:
            return False
        if rule.depth_budget < 0 or rule.depth_budget > MAX_CASCADE_DEPTH:
            return False
        if rule.source_feature_id == rule.target_feature_id:
            return False
        key = (rule.trigger, rule.source_feature_id)
        bag = self._rules.setdefault(key, [])
        if any(r.rule_id == rule.rule_id for r in bag):
            return False
        bag.append(rule)
        return True

    def on_break(
        self, *, arena_id: str, source_feature_id: str,
        now_seconds: int,
    ) -> tuple[CascadeStep, ...]:
        return self._fire(
            arena_id=arena_id,
            trigger=CascadeTrigger.ON_BREAK,
            source_feature_id=source_feature_id,
            now_seconds=now_seconds,
            depth=0,
        )

    def on_crack(
        self, *, arena_id: str, source_feature_id: str,
        now_seconds: int,
    ) -> tuple[CascadeStep, ...]:
        return self._fire(
            arena_id=arena_id,
            trigger=CascadeTrigger.ON_CRACK,
            source_feature_id=source_feature_id,
            now_seconds=now_seconds,
            depth=0,
        )

    def _fire(
        self, *, arena_id: str, trigger: CascadeTrigger,
        source_feature_id: str, now_seconds: int,
        depth: int,
    ) -> tuple[CascadeStep, ...]:
        if depth >= MAX_CASCADE_DEPTH:
            return ()
        bag = self._rules.get((trigger, source_feature_id), [])
        out: list[CascadeStep] = []
        for rule in bag:
            if rule.depth_budget < depth:
                continue
            target = self.arena_env.feature(
                arena_id=arena_id, feature_id=rule.target_feature_id,
            )
            if target is None:
                continue
            event = DamageEvent(
                source=DamageSource.ENV_HAZARD,
                amount=rule.followup_damage,
                element=rule.target_element,
                origin_band=target.band,
                band_radius=0,
                target_feature_ids=(rule.target_feature_id,),
            )
            impacts = self.environment_damage.submit(
                arena_id=arena_id, event=event,
            )
            for imp in impacts:
                step = CascadeStep(
                    rule_id=rule.rule_id,
                    source_feature_id=source_feature_id,
                    target_feature_id=imp.feature_id,
                    damage_dealt=imp.damage_dealt,
                    crossed_crack=imp.crossed_crack,
                    crossed_break=imp.crossed_break,
                    depth=depth + 1,
                    fired_at=now_seconds + rule.delay_seconds,
                )
                out.append(step)
                # If this step crossed break/crack, recurse into
                # this feature's downstream rules
                if imp.crossed_break:
                    children = self._fire(
                        arena_id=arena_id,
                        trigger=CascadeTrigger.ON_BREAK,
                        source_feature_id=imp.feature_id,
                        now_seconds=now_seconds + rule.delay_seconds,
                        depth=depth + 1,
                    )
                    out.extend(children)
                elif imp.crossed_crack:
                    children = self._fire(
                        arena_id=arena_id,
                        trigger=CascadeTrigger.ON_CRACK,
                        source_feature_id=imp.feature_id,
                        now_seconds=now_seconds + rule.delay_seconds,
                        depth=depth + 1,
                    )
                    out.extend(children)
        return tuple(out)


__all__ = [
    "CascadeTrigger", "CascadeRule", "CascadeStep",
    "EnvironmentCascade", "MAX_CASCADE_DEPTH",
]
