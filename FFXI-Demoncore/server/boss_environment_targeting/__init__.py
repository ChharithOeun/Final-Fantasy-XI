"""Boss environment targeting — bosses aim at the arena.

A canny boss doesn't just hit the tank; it hits the
ROOM. Mirahna's dual-cast Meteor Splash specifically
targets the ceiling. Vorrak's tail-sweep aims at the
east pillar. The Drowned King smashes the dam to flood
the chamber. This module gives every boss an environment
target plan: a list of preferred features, the trigger
conditions for choosing them, and a cooldown.

Plans:
    SCHEDULED   - fires at fixed in-fight elapsed seconds
    HP_GATED    - fires when boss HP crosses a band
    REACTIVE    - fires when a player action triggers it
                  (e.g. kited near a wall, the boss
                  decides to drop the wall)

Each plan picks a target feature_id (or a category like
"any wall") and emits a TargetSelection record the
combat layer feeds into the spell/AOE engine. The plan
does NOT roll the damage itself — it just announces
intent so the rest of the system can decide.

A boss can have a `learning_factor` 0..100 that biases
its choice toward features the alliance has NOT yet
fortified — the boss "remembers" what hit hardest in
prior phases.

Public surface
--------------
    PlanTrigger enum
    EnvTargetPlan dataclass (frozen)
    TargetSelection dataclass (frozen)
    BossEnvironmentTargeting
        .register_plan(boss_id, plan)
        .start_fight(boss_id, fight_id, hp_max, started_at)
        .choose_target(boss_id, fight_id, current_hp,
                       elapsed_seconds, trigger,
                       fortified_feature_ids)
            -> Optional[TargetSelection]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PlanTrigger(str, enum.Enum):
    SCHEDULED = "scheduled"
    HP_GATED = "hp_gated"
    REACTIVE = "reactive"


@dataclasses.dataclass(frozen=True)
class EnvTargetPlan:
    plan_id: str
    boss_id: str
    trigger: PlanTrigger
    feature_id: str               # explicit target
    damage: int
    element: str = "neutral"
    # SCHEDULED: fires once when elapsed >= scheduled_at
    scheduled_at: int = -1
    # HP_GATED: fires when HP% drops below this band
    hp_pct_floor: int = -1
    # REACTIVE: requires REACTIVE trigger event
    reactive_tag: t.Optional[str] = None
    cooldown_seconds: int = 60
    # 0..100 — chance the boss skips this plan if the
    # target feature is already fortified by the alliance
    fortify_avoid_pct: int = 0


@dataclasses.dataclass(frozen=True)
class TargetSelection:
    plan_id: str
    boss_id: str
    fight_id: str
    feature_id: str
    damage: int
    element: str
    chosen_at: int
    reason: str = ""


@dataclasses.dataclass
class _FightState:
    fight_id: str
    boss_id: str
    hp_max: int
    started_at: int
    last_fired_at: dict[str, int] = dataclasses.field(default_factory=dict)
    consumed_scheduled: set[str] = dataclasses.field(default_factory=set)
    crossed_hp_gates: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class BossEnvironmentTargeting:
    _plans: dict[str, list[EnvTargetPlan]] = dataclasses.field(
        default_factory=dict,
    )
    _fights: dict[str, _FightState] = dataclasses.field(default_factory=dict)

    def register_plan(self, plan: EnvTargetPlan) -> bool:
        if not plan.plan_id or not plan.boss_id or not plan.feature_id:
            return False
        if plan.damage <= 0:
            return False
        if plan.trigger == PlanTrigger.SCHEDULED and plan.scheduled_at < 0:
            return False
        if plan.trigger == PlanTrigger.HP_GATED and not (
            0 <= plan.hp_pct_floor <= 100
        ):
            return False
        if plan.trigger == PlanTrigger.REACTIVE and not plan.reactive_tag:
            return False
        if not (0 <= plan.fortify_avoid_pct <= 100):
            return False
        bag = self._plans.setdefault(plan.boss_id, [])
        if any(p.plan_id == plan.plan_id for p in bag):
            return False
        bag.append(plan)
        return True

    def start_fight(
        self, *, boss_id: str, fight_id: str,
        hp_max: int, started_at: int,
    ) -> bool:
        if not boss_id or not fight_id or hp_max <= 0:
            return False
        if fight_id in self._fights:
            return False
        self._fights[fight_id] = _FightState(
            fight_id=fight_id, boss_id=boss_id,
            hp_max=hp_max, started_at=started_at,
        )
        return True

    def choose_target(
        self, *, boss_id: str, fight_id: str,
        current_hp: int, elapsed_seconds: int,
        trigger: PlanTrigger,
        fortified_feature_ids: t.Iterable[str] = (),
        reactive_tag: t.Optional[str] = None,
        rng_roll_pct: int = 100,   # caller-supplied RNG roll 1..100
    ) -> t.Optional[TargetSelection]:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id:
            return None
        plans = self._plans.get(boss_id, [])
        forts = set(fortified_feature_ids)
        for p in plans:
            if p.trigger != trigger:
                continue
            # cooldown
            last = f.last_fired_at.get(p.plan_id, -10**9)
            if (elapsed_seconds - last) < p.cooldown_seconds:
                continue
            # one-shot semantics for SCHEDULED + HP_GATED
            if trigger == PlanTrigger.SCHEDULED:
                if p.plan_id in f.consumed_scheduled:
                    continue
                if elapsed_seconds < p.scheduled_at:
                    continue
            elif trigger == PlanTrigger.HP_GATED:
                if p.plan_id in f.crossed_hp_gates:
                    continue
                hp_pct = (current_hp * 100) // max(1, f.hp_max)
                if hp_pct > p.hp_pct_floor:
                    continue
            elif trigger == PlanTrigger.REACTIVE:
                if reactive_tag != p.reactive_tag:
                    continue
            # fortified-avoidance bias
            avoided = False
            if p.feature_id in forts and rng_roll_pct <= p.fortify_avoid_pct:
                avoided = True
            if avoided:
                continue
            # fire
            f.last_fired_at[p.plan_id] = elapsed_seconds
            if trigger == PlanTrigger.SCHEDULED:
                f.consumed_scheduled.add(p.plan_id)
            elif trigger == PlanTrigger.HP_GATED:
                f.crossed_hp_gates.add(p.plan_id)
            return TargetSelection(
                plan_id=p.plan_id, boss_id=boss_id,
                fight_id=fight_id, feature_id=p.feature_id,
                damage=p.damage, element=p.element,
                chosen_at=elapsed_seconds,
                reason=trigger.value,
            )
        return None


__all__ = [
    "PlanTrigger", "EnvTargetPlan", "TargetSelection",
    "BossEnvironmentTargeting",
]
