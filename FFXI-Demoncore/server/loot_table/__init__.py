"""Loot tables — mob drop rolls, rarity tiers, Treasure Hunter.

Why this module exists
----------------------
Every mob in Vana'diel has a drop table, and FFXI's classic
charm is the per-tier rarity grammar:

    common    - drops most fights (60-100% post-TH)
    uncommon  - shows up regularly (15-50%)
    rare      - the thing you actually came here for (1-12%)
    super_rare- the lottery item (0.1-2%)
    ex        - exclusive/cannot be sold; gated by other rules

Treasure Hunter (TH) model
--------------------------
Demoncore's TH expands beyond classic FFXI's THF subjob trick:

  base_level       - subjob-derived TH (THF /sub etc.), 0..3 typical
  equipment_level  - sum of TH bonuses on currently equipped gear
  skill_level      - skill-point/merit/job-point derived TH
  proc_level       - in-fight crit-proc bumps that accumulate per
                       hit, capped so total can't exceed TH 16

The "equipped" stack (base + equipment + skill) caps at TH 9.
That's the steady-state ceiling. During a fight, every melee hit
has a chance to PROC TH up by 1, and proc bumps are allowed to
push total effective TH up to 16. After the fight ends, proc
resets — that's why high-TH kills feel like an event.

Pets (automatons, wyverns, avatars, fomors-as-mobs in PvP) inherit
the master's equipment + skill TH while the master has the pet
deployed. The base subjob trick does NOT transfer (it's a job
ability, not a gear effect). Master's proc state is what the pet
benefits from at proc-roll time.

Public surface
--------------
    Rarity                     enum
    DropEntry / DropTable / ItemDrop
    TreasureHunterState        composable TH model
    MAX_TH_EQUIPPED            ceiling for base+equip+skill stack
    MAX_TH_CRIT_PROC           ceiling once procs are folded in
    DEFAULT_TH_PROC_CHANCE     baseline per-hit proc chance
    effective_th_level(state)  -> 0..16 number for table lookup
    treasure_hunter_modifier(rarity, th_level) -> float
    proc_treasure_hunter(state, rng_pool, *, proc_chance)
                                  -> (procced: bool, new_state)
    master_th_for_pet(master_state) -> TreasureHunterState
    roll_drops(*, table, rng_pool, th_level=0)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class Rarity(str, enum.Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    SUPER_RARE = "super_rare"
    EX = "ex"


@dataclasses.dataclass(frozen=True)
class DropEntry:
    """One slot in a mob's drop table."""
    item_id: str
    base_rate: float                  # 0..1 inclusive
    rarity: Rarity
    label: str = ""                   # human-friendly name (optional)

    def __post_init__(self) -> None:
        if not 0.0 <= self.base_rate <= 1.0:
            raise ValueError(
                f"base_rate {self.base_rate} out of [0,1]"
            )


@dataclasses.dataclass(frozen=True)
class DropTable:
    """A mob's complete drop table."""
    mob_class_id: str
    entries: tuple[DropEntry, ...]
    label: str = ""

    def by_rarity(self, r: Rarity) -> tuple[DropEntry, ...]:
        return tuple(e for e in self.entries if e.rarity == r)


@dataclasses.dataclass(frozen=True)
class ItemDrop:
    """One result of a single drop roll."""
    item_id: str
    rarity: Rarity
    rolled_against: float


# -- Treasure Hunter modifier tables --------------------------------

# Cap on the steady-state stack from base + equipment + skill.
# Demoncore canonical: gear/skill alone never gets you above TH 9.
MAX_TH_EQUIPPED = 9

# Cap once proc bumps are layered on. THIS is the new ceiling
# once you start landing in-fight crit procs.
MAX_TH_CRIT_PROC = 16

MAX_TH_LEVEL = MAX_TH_CRIT_PROC

# Per-rarity, per-th-level multiplier. Common ramps gently, rare
# benefits the most. EX is always identity — gated by other rules.
_TH_MODIFIERS: dict[Rarity, dict[int, float]] = {
    Rarity.COMMON: {
        0: 1.00, 1: 1.05, 2: 1.10, 3: 1.13, 4: 1.15,
        5: 1.16, 6: 1.17, 7: 1.18, 8: 1.19, 9: 1.20,
        # proc territory - gentle further bumps
        10: 1.21, 11: 1.22, 12: 1.23, 13: 1.24,
        14: 1.25, 15: 1.26, 16: 1.27,
    },
    Rarity.UNCOMMON: {
        0: 1.00, 1: 1.10, 2: 1.20, 3: 1.27, 4: 1.32,
        5: 1.36, 6: 1.40, 7: 1.43, 8: 1.46, 9: 1.50,
        10: 1.55, 11: 1.60, 12: 1.65, 13: 1.70,
        14: 1.75, 15: 1.80, 16: 1.85,
    },
    Rarity.RARE: {
        0: 1.00, 1: 1.20, 2: 1.40, 3: 1.55, 4: 1.65,
        5: 1.74, 6: 1.82, 7: 1.90, 8: 1.97, 9: 2.05,
        10: 2.15, 11: 2.25, 12: 2.35, 13: 2.45,
        14: 2.55, 15: 2.65, 16: 2.75,
    },
    Rarity.SUPER_RARE: {
        0: 1.00, 1: 1.25, 2: 1.50, 3: 1.70, 4: 1.85,
        5: 1.97, 6: 2.07, 7: 2.16, 8: 2.24, 9: 2.30,
        10: 2.45, 11: 2.60, 12: 2.75, 13: 2.90,
        14: 3.05, 15: 3.20, 16: 3.35,
    },
    # EX rates are gated by external rules — TH never changes them.
    Rarity.EX: {i: 1.0 for i in range(MAX_TH_CRIT_PROC + 1)},
}


def treasure_hunter_modifier(rarity: Rarity, th_level: int) -> float:
    """Return the multiplicative TH modifier for *rarity* at TH
    level *th_level* (0..16).

    Out-of-range th_levels saturate at MAX_TH_CRIT_PROC.
    """
    if th_level < 0:
        raise ValueError(f"th_level {th_level} must be >= 0")
    clamped = min(th_level, MAX_TH_CRIT_PROC)
    return _TH_MODIFIERS[rarity][clamped]


# -- Treasure Hunter STATE (the composable model) -------------------

@dataclasses.dataclass(frozen=True)
class TreasureHunterState:
    """Composable TH state for a player or pet.

    Components stack to produce an effective TH level. Equipment +
    skill + base combine into the steady-state level, capped at
    MAX_TH_EQUIPPED. Proc bumps add on top, capped overall at
    MAX_TH_CRIT_PROC.
    """
    base_level: int = 0
    equipment_level: int = 0
    skill_level: int = 0
    proc_level: int = 0

    def __post_init__(self) -> None:
        for name in ("base_level", "equipment_level",
                     "skill_level", "proc_level"):
            v = getattr(self, name)
            if v < 0:
                raise ValueError(f"{name} {v} must be >= 0")


def effective_th_level(state: TreasureHunterState) -> int:
    """Resolve a TreasureHunterState into a single 0..16 level
    suitable for treasure_hunter_modifier lookup.

    Equipped stack (base + equipment + skill) caps at 9. Procs
    add on top. Total capped at 16.
    """
    equipped = (
        state.base_level + state.equipment_level + state.skill_level
    )
    equipped = min(equipped, MAX_TH_EQUIPPED)
    total = equipped + state.proc_level
    return min(total, MAX_TH_CRIT_PROC)


# Default per-hit proc chance — a bit generous so chains of hits
# accumulate visibly during a fight. Tunable per encounter.
DEFAULT_TH_PROC_CHANCE = 0.10


def proc_treasure_hunter(
    state: TreasureHunterState,
    rng_pool: RngPool,
    *,
    proc_chance: float = DEFAULT_TH_PROC_CHANCE,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[bool, TreasureHunterState]:
    """Roll a TH proc on a melee hit.

    On success, bumps proc_level by 1 unless the resulting effective
    TH level would exceed MAX_TH_CRIT_PROC. Returns (procced,
    new_state). On failure, returns (False, state) unchanged.

    proc_chance must be in [0, 1].
    """
    if not 0.0 <= proc_chance <= 1.0:
        raise ValueError("proc_chance must be in [0, 1]")
    # Already at the absolute cap? Skip the roll.
    if effective_th_level(state) >= MAX_TH_CRIT_PROC:
        return False, state
    rng = rng_pool.stream(stream_name)
    if rng.random() < proc_chance:
        bumped = dataclasses.replace(
            state, proc_level=state.proc_level + 1
        )
        # Defensive: if the bump pushes us past the cap (shouldn't
        # happen given the early-return above), clamp.
        if effective_th_level(bumped) > MAX_TH_CRIT_PROC:
            return False, state
        return True, bumped
    return False, state


def master_th_for_pet(
    master_state: TreasureHunterState,
) -> TreasureHunterState:
    """Derive the pet's TH state from the master's.

    Pets inherit master's equipment_level and skill_level (the gear
    the master is wearing radiates to the pet). Master's base_level
    (subjob-derived) does NOT transfer — that's a player-only job
    ability. Proc state DOES transfer because the pet's hits keep
    benefiting from the in-fight tally.
    """
    return TreasureHunterState(
        base_level=0,
        equipment_level=master_state.equipment_level,
        skill_level=master_state.skill_level,
        proc_level=master_state.proc_level,
    )


def reset_proc(state: TreasureHunterState) -> TreasureHunterState:
    """Drop the proc tally back to zero. Call between fights."""
    return dataclasses.replace(state, proc_level=0)


# -- roll engine ---------------------------------------------------

def _effective_rate(entry: DropEntry, th_level: int) -> float:
    raw = entry.base_rate * treasure_hunter_modifier(
        entry.rarity, th_level
    )
    return min(1.0, raw)


def roll_drops(
    *,
    table: DropTable,
    rng_pool: RngPool,
    th_level: int = 0,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[ItemDrop, ...]:
    """Roll *table* once and return what dropped.

    Caller passes a single resolved th_level. To compute it from
    a TreasureHunterState, use effective_th_level().
    """
    out: list[ItemDrop] = []
    rng = rng_pool.stream(stream_name)
    for entry in table.entries:
        threshold = _effective_rate(entry, th_level)
        roll = rng.random()
        if roll < threshold:
            out.append(ItemDrop(
                item_id=entry.item_id,
                rarity=entry.rarity,
                rolled_against=threshold,
            ))
    return tuple(out)


def roll_drops_for(
    *,
    table: DropTable,
    rng_pool: RngPool,
    th_state: TreasureHunterState,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[ItemDrop, ...]:
    """Convenience: roll *table* using a TreasureHunterState."""
    return roll_drops(
        table=table,
        rng_pool=rng_pool,
        th_level=effective_th_level(th_state),
        stream_name=stream_name,
    )


def drops_count_by_rarity(
    drops: t.Sequence[ItemDrop],
) -> dict[Rarity, int]:
    bucket: dict[Rarity, int] = {r: 0 for r in Rarity}
    for d in drops:
        bucket[d.rarity] += 1
    return bucket


__all__ = [
    "Rarity",
    "DropEntry",
    "DropTable",
    "ItemDrop",
    "TreasureHunterState",
    "MAX_TH_EQUIPPED", "MAX_TH_CRIT_PROC", "MAX_TH_LEVEL",
    "DEFAULT_TH_PROC_CHANCE",
    "effective_th_level",
    "treasure_hunter_modifier",
    "proc_treasure_hunter",
    "master_th_for_pet",
    "reset_proc",
    "roll_drops",
    "roll_drops_for",
    "drops_count_by_rarity",
]
