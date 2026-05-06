"""Rebuild & repair phase — between-phase mid-fight recovery.

Long fights have phase transitions: cinematic the boss
roars and walks 30 yalms back, the floor stops shaking,
the camera pulls out, and the alliance gets a SHORT
window to repair, regroup, re-buff. This module wires
the repair side: alliances spend materials and craft
skill DURING the fight to heal damaged-but-not-broken
features, and to RAISE permanently-broken features back
to a damaged-but-functional state.

There are two operations:

    repair(feature_id, hp_amount, materials_spent,
           craft_skill, now_seconds)
        -> only works if feature is DAMAGED or CRACKED;
        cannot heal a BROKEN feature

    rebuild(feature_id, hp_target, materials_spent,
            craft_skill, now_seconds)
        -> only works if feature is BROKEN; rebuilds to
        HP_target (capped at hp_max * REBUILD_CAP_PCT,
        e.g. 60% — repaired features are weaker than
        original)

Each operation has a per-feature cooldown so a single
repair team can't single-handedly outrun boss damage.
And operations consume an "alliance repair budget" so
the alliance has to choose where to spend.

Public surface
--------------
    RepairResult dataclass (frozen)
    RebuildRepairPhase
        .open_window(arena_id, opens_at, closes_at,
                     budget_per_alliance)
        .repair(arena_id, feature_id, hp_amount,
                materials_spent, craft_skill, now_seconds)
            -> RepairResult
        .rebuild(arena_id, feature_id, hp_target,
                 materials_spent, craft_skill, now_seconds)
            -> RepairResult
        .remaining_budget(arena_id) -> int
        .close_window(arena_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import (
    ArenaEnvironment, FeatureState,
)


class RepairKind(str, enum.Enum):
    REPAIR = "repair"
    REBUILD = "rebuild"


# Tuning knobs
MIN_CRAFT_SKILL_REPAIR = 50
MIN_CRAFT_SKILL_REBUILD = 80
PER_FEATURE_COOLDOWN_SECONDS = 30
REBUILD_CAP_PCT = 60          # rebuilt feature's hp ceiling
COST_PER_HP_REPAIR = 1
COST_PER_HP_REBUILD = 3       # rebuilds are 3x more expensive


@dataclasses.dataclass(frozen=True)
class RepairResult:
    accepted: bool
    kind: t.Optional[RepairKind] = None
    feature_id: str = ""
    hp_applied: int = 0
    new_hp: int = 0
    budget_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _Window:
    opens_at: int
    closes_at: int
    budget: int
    last_action_at: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class RebuildRepairPhase:
    arena_env: ArenaEnvironment
    _windows: dict[str, _Window] = dataclasses.field(default_factory=dict)

    def open_window(
        self, *, arena_id: str,
        opens_at: int, closes_at: int,
        budget_per_alliance: int,
    ) -> bool:
        if not arena_id or closes_at <= opens_at:
            return False
        if budget_per_alliance <= 0:
            return False
        self._windows[arena_id] = _Window(
            opens_at=opens_at, closes_at=closes_at,
            budget=budget_per_alliance,
        )
        return True

    def remaining_budget(self, *, arena_id: str) -> int:
        w = self._windows.get(arena_id)
        return w.budget if w else 0

    def close_window(self, *, arena_id: str) -> bool:
        if arena_id in self._windows:
            del self._windows[arena_id]
            return True
        return False

    def _check_window(
        self, *, arena_id: str, now_seconds: int,
    ) -> tuple[t.Optional[_Window], t.Optional[str]]:
        w = self._windows.get(arena_id)
        if w is None:
            return None, "no window"
        if now_seconds < w.opens_at:
            return None, "window not open"
        if now_seconds >= w.closes_at:
            return None, "window closed"
        return w, None

    def _check_cooldown(
        self, *, w: _Window, feature_id: str, now_seconds: int,
    ) -> bool:
        last = w.last_action_at.get(feature_id, -10**9)
        return (now_seconds - last) >= PER_FEATURE_COOLDOWN_SECONDS

    def repair(
        self, *, arena_id: str, feature_id: str,
        hp_amount: int, materials_spent: int,
        craft_skill: int, now_seconds: int,
    ) -> RepairResult:
        w, reason = self._check_window(
            arena_id=arena_id, now_seconds=now_seconds,
        )
        if w is None:
            return RepairResult(False, reason=reason)
        if hp_amount <= 0:
            return RepairResult(False, reason="non-positive hp")
        if craft_skill < MIN_CRAFT_SKILL_REPAIR:
            return RepairResult(False, reason="craft skill too low")
        if materials_spent < hp_amount * COST_PER_HP_REPAIR:
            return RepairResult(False, reason="not enough materials")
        if hp_amount > w.budget:
            return RepairResult(False, reason="over alliance budget")
        feat = self.arena_env.feature(
            arena_id=arena_id, feature_id=feature_id,
        )
        if feat is None:
            return RepairResult(False, reason="unknown feature")
        state = self.arena_env.state(
            arena_id=arena_id, feature_id=feature_id,
        )
        if state == FeatureState.BROKEN:
            return RepairResult(False, reason="feature broken — rebuild")
        if state == FeatureState.INTACT:
            return RepairResult(False, reason="already intact")
        if not self._check_cooldown(
            w=w, feature_id=feature_id, now_seconds=now_seconds,
        ):
            return RepairResult(False, reason="cooldown")
        # apply healing — we expose this through a low-level helper
        cur_hp = self.arena_env.hp(
            arena_id=arena_id, feature_id=feature_id,
        )
        max_heal = feat.hp_max - cur_hp
        applied = min(hp_amount, max_heal)
        if applied <= 0:
            return RepairResult(False, reason="already at max")
        new_hp = cur_hp + applied
        self._set_hp(
            arena_id=arena_id, feature_id=feature_id, hp=new_hp,
        )
        w.budget -= applied
        w.last_action_at[feature_id] = now_seconds
        return RepairResult(
            accepted=True, kind=RepairKind.REPAIR,
            feature_id=feature_id, hp_applied=applied,
            new_hp=new_hp, budget_remaining=w.budget,
        )

    def rebuild(
        self, *, arena_id: str, feature_id: str,
        hp_target: int, materials_spent: int,
        craft_skill: int, now_seconds: int,
    ) -> RepairResult:
        w, reason = self._check_window(
            arena_id=arena_id, now_seconds=now_seconds,
        )
        if w is None:
            return RepairResult(False, reason=reason)
        if hp_target <= 0:
            return RepairResult(False, reason="non-positive target")
        if craft_skill < MIN_CRAFT_SKILL_REBUILD:
            return RepairResult(False, reason="craft skill too low for rebuild")
        feat = self.arena_env.feature(
            arena_id=arena_id, feature_id=feature_id,
        )
        if feat is None:
            return RepairResult(False, reason="unknown feature")
        cap = feat.hp_max * REBUILD_CAP_PCT // 100
        clamped_target = min(hp_target, cap)
        if materials_spent < clamped_target * COST_PER_HP_REBUILD:
            return RepairResult(False, reason="not enough materials")
        if clamped_target > w.budget:
            return RepairResult(False, reason="over alliance budget")
        state = self.arena_env.state(
            arena_id=arena_id, feature_id=feature_id,
        )
        if state != FeatureState.BROKEN:
            return RepairResult(False, reason="feature not broken")
        if not self._check_cooldown(
            w=w, feature_id=feature_id, now_seconds=now_seconds,
        ):
            return RepairResult(False, reason="cooldown")
        self._set_hp(
            arena_id=arena_id, feature_id=feature_id,
            hp=clamped_target,
        )
        w.budget -= clamped_target
        w.last_action_at[feature_id] = now_seconds
        return RepairResult(
            accepted=True, kind=RepairKind.REBUILD,
            feature_id=feature_id, hp_applied=clamped_target,
            new_hp=clamped_target, budget_remaining=w.budget,
        )

    def _set_hp(
        self, *, arena_id: str, feature_id: str, hp: int,
    ) -> None:
        # Direct write — go through ArenaEnvironment's internal dict
        a = self.arena_env._arenas.get(arena_id, {})
        s = a.get(feature_id)
        if s is not None:
            s.hp = max(0, min(hp, s.feature.hp_max))


__all__ = [
    "RepairKind", "RepairResult", "RebuildRepairPhase",
    "MIN_CRAFT_SKILL_REPAIR", "MIN_CRAFT_SKILL_REBUILD",
    "PER_FEATURE_COOLDOWN_SECONDS", "REBUILD_CAP_PCT",
    "COST_PER_HP_REPAIR", "COST_PER_HP_REBUILD",
]
