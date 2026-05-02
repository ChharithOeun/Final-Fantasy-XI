"""Voidwatch — staged endgame raid encounters.

Voidwatch NMs are summoned via voidstones at fixed nodes. Each
encounter has stages: ENGAGE -> EMPOWERED (mob heals/buffs at
threshold) -> CLEAVE (final wipe-attempt). Each stage has its
own damage threshold to push past. After kill, Riftborn loot
rolls. Cooldown timer prevents spamming.

Public surface
--------------
    Stage enum
    VoidwatchSpec catalog
    VoidwatchEncounter live state
        .deal_damage(amount) -> Stage transitions
        .conclude() -> RewardRoll
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class Stage(str, enum.Enum):
    DORMANT = "dormant"
    ENGAGE = "engage"
    EMPOWERED = "empowered"
    CLEAVE = "cleave"
    DEFEATED = "defeated"


@dataclasses.dataclass(frozen=True)
class StageSpec:
    name: Stage
    damage_to_advance: int


@dataclasses.dataclass(frozen=True)
class RiftbornDrop:
    item_id: str
    weight: int


@dataclasses.dataclass(frozen=True)
class VoidwatchSpec:
    voidwatch_id: str
    label: str
    zone_id: str
    tier: int                              # 1..4 difficulty
    stages: tuple[StageSpec, ...]
    riftborn_pool: tuple[RiftbornDrop, ...]
    cooldown_seconds: int = 60 * 60        # 1 hour between attempts


# Sample catalog
VOIDWATCH_CATALOG: tuple[VoidwatchSpec, ...] = (
    VoidwatchSpec(
        voidwatch_id="ig_alima_tier_1", label="Ig-Alima",
        zone_id="caedarva_mire", tier=1,
        stages=(
            StageSpec(Stage.ENGAGE, damage_to_advance=8000),
            StageSpec(Stage.EMPOWERED, damage_to_advance=20000),
            StageSpec(Stage.CLEAVE, damage_to_advance=40000),
        ),
        riftborn_pool=(
            RiftbornDrop("riftborn_boulder", weight=60),
            RiftbornDrop("voidstone", weight=25),
            RiftbornDrop("riftcinder", weight=15),
        ),
    ),
    VoidwatchSpec(
        voidwatch_id="qilin_tier_3", label="Qilin",
        zone_id="garlaige_citadel", tier=3,
        stages=(
            StageSpec(Stage.ENGAGE, damage_to_advance=20000),
            StageSpec(Stage.EMPOWERED, damage_to_advance=50000),
            StageSpec(Stage.CLEAVE, damage_to_advance=100000),
        ),
        riftborn_pool=(
            RiftbornDrop("voidstone", weight=40),
            RiftbornDrop("riftcinder", weight=30),
            RiftbornDrop("voidleaf", weight=20),
            RiftbornDrop("riftdross", weight=10),
        ),
    ),
)

SPEC_BY_ID: dict[str, VoidwatchSpec] = {
    s.voidwatch_id: s for s in VOIDWATCH_CATALOG
}


@dataclasses.dataclass
class VoidwatchEncounter:
    encounter_id: str
    voidwatch_id: str
    stage: Stage = Stage.DORMANT
    damage_in_stage: int = 0
    started_at_tick: int = 0

    @property
    def spec(self) -> VoidwatchSpec:
        return SPEC_BY_ID[self.voidwatch_id]

    def engage(self, *, now_tick: int) -> bool:
        if self.stage != Stage.DORMANT:
            return False
        self.stage = Stage.ENGAGE
        self.started_at_tick = now_tick
        self.damage_in_stage = 0
        return True

    def deal_damage(self, *, amount: int) -> Stage:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if self.stage in (Stage.DORMANT, Stage.DEFEATED):
            return self.stage
        self.damage_in_stage += amount
        # Advance stages while threshold met
        spec_stages = self.spec.stages
        for spec_stage in spec_stages:
            if self.stage == spec_stage.name and \
                    self.damage_in_stage >= spec_stage.damage_to_advance:
                # Advance to next stage
                idx = spec_stages.index(spec_stage)
                if idx + 1 < len(spec_stages):
                    self.stage = spec_stages[idx + 1].name
                    self.damage_in_stage = 0
                else:
                    self.stage = Stage.DEFEATED
                break
        return self.stage


@dataclasses.dataclass(frozen=True)
class RewardRoll:
    accepted: bool
    drop_item_id: t.Optional[str] = None
    reason: t.Optional[str] = None


def conclude(
    encounter: VoidwatchEncounter, *,
    rng_pool: RngPool,
    stream_name: str = STREAM_LOOT_DROPS,
) -> RewardRoll:
    if encounter.stage != Stage.DEFEATED:
        return RewardRoll(False, reason="not defeated")
    rng = rng_pool.stream(stream_name)
    pool = encounter.spec.riftborn_pool
    total = sum(d.weight for d in pool)
    pick = rng.uniform(0, total)
    cum = 0.0
    chosen = pool[0].item_id
    for d in pool:
        cum += d.weight
        if pick <= cum:
            chosen = d.item_id
            break
    return RewardRoll(accepted=True, drop_item_id=chosen)


__all__ = [
    "Stage", "StageSpec", "RiftbornDrop", "VoidwatchSpec",
    "VOIDWATCH_CATALOG", "SPEC_BY_ID",
    "VoidwatchEncounter", "RewardRoll",
    "conclude",
]
