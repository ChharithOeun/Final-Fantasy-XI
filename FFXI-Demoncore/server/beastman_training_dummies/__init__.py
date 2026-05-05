"""Beastman training dummies — combat practice rigs.

Each beastman city has a TRAINING HALL stocked with combat
DUMMIES tuned to specific defense profiles (HEAVY_PLATE,
LIGHT_LEATHER, MAGIC_WARD, EVASIVE_GHOST). Players strike a
dummy to PRACTICE — registering damage builds COMBAT INSIGHT
for that profile, which translates into a small accuracy bonus
versus mobs of the same defensive type for the next 30
real-time minutes.

Insights are CAPPED at 10 stacks per profile and DECAY one
stack every 6 minutes once not actively training.

Public surface
--------------
    DummyKind enum
    Dummy dataclass
    InsightSnapshot dataclass
    BeastmanTrainingDummies
        .register_dummy(dummy_id, kind, hp_pool)
        .strike(player_id, dummy_id, damage, now_seconds)
        .insight_for(player_id, kind, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DummyKind(str, enum.Enum):
    HEAVY_PLATE = "heavy_plate"
    LIGHT_LEATHER = "light_leather"
    MAGIC_WARD = "magic_ward"
    EVASIVE_GHOST = "evasive_ghost"


_INSIGHT_CAP = 10
_DECAY_INTERVAL_SECONDS = 360
_INSIGHT_PER_DAMAGE_BUCKET = 1
_DAMAGE_PER_BUCKET = 200


@dataclasses.dataclass
class Dummy:
    dummy_id: str
    kind: DummyKind
    hp_pool: int
    hp_remaining: int


@dataclasses.dataclass
class _Insight:
    stacks: int = 0
    last_stack_gain_at: int = 0


@dataclasses.dataclass(frozen=True)
class StrikeResult:
    accepted: bool
    dummy_id: str
    damage_dealt: int = 0
    hp_remaining: int = 0
    insight_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class InsightSnapshot:
    kind: DummyKind
    stacks: int


@dataclasses.dataclass
class BeastmanTrainingDummies:
    _dummies: dict[str, Dummy] = dataclasses.field(default_factory=dict)
    _insights: dict[
        tuple[str, DummyKind], _Insight,
    ] = dataclasses.field(default_factory=dict)
    _damage_pool: dict[
        tuple[str, str], int,
    ] = dataclasses.field(default_factory=dict)

    def register_dummy(
        self, *, dummy_id: str,
        kind: DummyKind,
        hp_pool: int,
    ) -> t.Optional[Dummy]:
        if dummy_id in self._dummies:
            return None
        if hp_pool <= 0:
            return None
        d = Dummy(
            dummy_id=dummy_id, kind=kind,
            hp_pool=hp_pool, hp_remaining=hp_pool,
        )
        self._dummies[dummy_id] = d
        return d

    def _resolve_decay(
        self, key: tuple[str, DummyKind], now_seconds: int,
    ) -> _Insight:
        ins = self._insights.get(key)
        if ins is None:
            ins = _Insight(stacks=0, last_stack_gain_at=now_seconds)
            self._insights[key] = ins
            return ins
        if ins.stacks <= 0:
            return ins
        elapsed = now_seconds - ins.last_stack_gain_at
        if elapsed <= 0:
            return ins
        decays = elapsed // _DECAY_INTERVAL_SECONDS
        if decays > 0:
            ins.stacks = max(0, ins.stacks - decays)
            ins.last_stack_gain_at = now_seconds
        return ins

    def strike(
        self, *, player_id: str,
        dummy_id: str,
        damage: int,
        now_seconds: int,
    ) -> StrikeResult:
        d = self._dummies.get(dummy_id)
        if d is None:
            return StrikeResult(
                False, dummy_id, reason="unknown dummy",
            )
        if damage <= 0:
            return StrikeResult(
                False, dummy_id, hp_remaining=d.hp_remaining,
                reason="non-positive damage",
            )
        applied = min(damage, d.hp_remaining)
        d.hp_remaining -= applied
        # Reset dummy when depleted to keep training continuous
        if d.hp_remaining <= 0:
            d.hp_remaining = d.hp_pool
        # Accumulate damage toward bucket → insight stack
        pool_key = (player_id, dummy_id)
        pool = self._damage_pool.get(pool_key, 0) + applied
        ins_key = (player_id, d.kind)
        ins = self._resolve_decay(ins_key, now_seconds)
        gained = pool // _DAMAGE_PER_BUCKET
        pool = pool % _DAMAGE_PER_BUCKET
        self._damage_pool[pool_key] = pool
        if gained > 0:
            ins.stacks = min(
                _INSIGHT_CAP,
                ins.stacks + gained * _INSIGHT_PER_DAMAGE_BUCKET,
            )
            ins.last_stack_gain_at = now_seconds
        return StrikeResult(
            accepted=True,
            dummy_id=dummy_id,
            damage_dealt=applied,
            hp_remaining=d.hp_remaining,
            insight_after=ins.stacks,
        )

    def insight_for(
        self, *, player_id: str,
        kind: DummyKind,
        now_seconds: int,
    ) -> InsightSnapshot:
        ins = self._resolve_decay(
            (player_id, kind), now_seconds,
        )
        return InsightSnapshot(kind=kind, stacks=ins.stacks)

    def total_dummies(self) -> int:
        return len(self._dummies)


__all__ = [
    "DummyKind", "Dummy",
    "StrikeResult", "InsightSnapshot",
    "BeastmanTrainingDummies",
]
