"""Goblin Smithy — the tutorial's first boss-grade encounter.

Per TUTORIAL_BASTOK_MINES.md (minute 75-90) the gate's payload is
a Tier-1 boss using the BOSS_GRAMMAR.md minimum recipe: lvl 5,
4 attacks, 3 phases, no critic. The named attack is Hammer Slam,
a cone telegraph with a 1.5s cast.

Three scripted casts:
    1. Hits the player.
    2. Player sidesteps.
    3. Player sidesteps again.

The fight teaches phase transition by pure visual reading. The
goblin starts pristine, goes scuffed, then wounded, then broken.
Posture and breathing change at each phase.

This module owns the recipe shape; the orchestrator + boss_critic
modules execute it.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class BossAttack:
    """One attack in the boss's repertoire."""
    name: str
    is_named: bool
    cast_time_seconds: float
    telegraph_shape: t.Optional[str]   # "cone" | "circle" | "line" | None
    cooldown_seconds: float


@dataclasses.dataclass(frozen=True)
class BossPhase:
    """One phase of the boss fight. Triggered by hp_fraction."""
    phase_index: int
    triggered_at_hp_fraction: float    # 1.0 = pristine; 0.0 = broken
    visible_state_label: str
    posture_change_summary: str


@dataclasses.dataclass(frozen=True)
class BossRecipe:
    """The full minimum recipe for the tutorial boss."""
    boss_id: str
    label: str
    job: str
    level: int
    attacks: tuple[BossAttack, ...]
    phases: tuple[BossPhase, ...]
    has_critic_llm: bool
    cinematic_intro_seconds: float
    drop_id: str
    closing_line_npc: str
    closing_line: str


# The doc names exactly four attacks — three plain swings + the
# named Hammer Slam. We encode them all so boss_critic can
# round-robin while leaving 'Hammer Slam' as the only telegraphed
# beat the player has to read.
GOBLIN_SMITHY_ATTACKS: tuple[BossAttack, ...] = (
    BossAttack(name="hammer_swing_basic",
                is_named=False,
                cast_time_seconds=0.0,
                telegraph_shape=None,
                cooldown_seconds=2.5),
    BossAttack(name="anvil_kick",
                is_named=False,
                cast_time_seconds=0.0,
                telegraph_shape=None,
                cooldown_seconds=4.0),
    BossAttack(name="bellows_shove",
                is_named=False,
                cast_time_seconds=0.0,
                telegraph_shape=None,
                cooldown_seconds=6.0),
    BossAttack(name="hammer_slam",
                is_named=True,
                cast_time_seconds=1.5,
                telegraph_shape="cone",
                cooldown_seconds=12.0),
)


# Three phases per BOSS_GRAMMAR.md minimum recipe. Phase boundaries
# are at 66%% and 33%% hp.
GOBLIN_SMITHY_PHASES: tuple[BossPhase, ...] = (
    BossPhase(phase_index=1,
                triggered_at_hp_fraction=1.0,
                visible_state_label="pristine",
                posture_change_summary=(
                    "stands tall, hammer rests on shoulder, "
                    "calm breathing"
                )),
    BossPhase(phase_index=2,
                triggered_at_hp_fraction=0.66,
                visible_state_label="scuffed",
                posture_change_summary=(
                    "hammer drops slightly, breathing audible, "
                    "shifts weight"
                )),
    BossPhase(phase_index=3,
                triggered_at_hp_fraction=0.33,
                visible_state_label="wounded",
                posture_change_summary=(
                    "limp pronounced, swings get wider and slower, "
                    "ragged breath"
                )),
)


GOBLIN_SMITHY: BossRecipe = BossRecipe(
    boss_id="tutorial_goblin_smithy",
    label="Goblin Smithy",
    job="WAR",
    level=5,
    attacks=GOBLIN_SMITHY_ATTACKS,
    phases=GOBLIN_SMITHY_PHASES,
    has_critic_llm=False,                  # doc: 'no critic'
    cinematic_intro_seconds=4.0,
    drop_id="bronze_ore_small",
    closing_line_npc="cid",
    closing_line="That's mining work, kid. Welcome.",
)


def hammer_slam_cast_sequence() -> tuple[str, ...]:
    """The 3 scripted casts of Hammer Slam, per the doc.

    Cast 1 hits, casts 2 and 3 are dodged. Returned tuple labels are
    the cast outcomes in order.
    """
    return ("hit", "dodge", "dodge")


def named_attacks(recipe: BossRecipe = GOBLIN_SMITHY) -> tuple[BossAttack, ...]:
    """Filter the recipe's attacks down to the named ones."""
    return tuple(a for a in recipe.attacks if a.is_named)


def total_phases(recipe: BossRecipe = GOBLIN_SMITHY) -> int:
    return len(recipe.phases)
