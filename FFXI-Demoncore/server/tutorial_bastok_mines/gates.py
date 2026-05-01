"""The 7 choreographed gates of the Bastok Mines tutorial.

Per TUTORIAL_BASTOK_MINES.md the first 90 minutes of every new
Demoncore character is a directed sequence of beats anchored to
specific NPCs, zones, and learning objectives. We encode those
beats here so the orchestrator can:

    - know what gate the player is on right now
    - emit the right Tutorial:gate_<n> tag for layered-scene wiring
    - fire the right cinematic / boss-recipe at the right minute
    - age the whole apparatus out after the 90-minute window

The gate ordering is fixed by the doc — there is no branching.
The minute-window numbers are tuning anchors, not hard timers; a
player who lingers can still advance, and a fast player can't
skip ahead. Advancement is event-driven: a gate completes when
its `completion_event` fires.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TutorialGate(enum.IntEnum):
    """The 7 gates, ordered as the player encounters them."""
    ARRIVAL = 1
    WEIGHT = 2
    FIRST_COMBAT = 3
    REVEAL_SKILL = 4
    INTERVENTION = 5
    CHAIN = 6
    BOSS = 7


@dataclasses.dataclass(frozen=True)
class GateBeat:
    """One scripted beat in the tutorial."""
    gate: TutorialGate
    minute_window: tuple[int, int]    # tuning anchor, not a hard limit
    tutorial_npc: str
    tutorial_zone: str
    layered_scene_tag: str
    completion_event: str
    learning_objectives: tuple[str, ...]
    summary: str = ""


# 90-minute total tutorial window per the doc.
TUTORIAL_AGE_OUT_MINUTES = 90


# Master beat table — exactly mirrors the choreography section of
# the doc. Order is the canonical advancement order.
GATE_TABLE: tuple[GateBeat, ...] = (
    GateBeat(
        gate=TutorialGate.ARRIVAL,
        minute_window=(0, 3),
        tutorial_npc="cid",
        tutorial_zone="bastok_mines",
        layered_scene_tag="Tutorial:gate_arrival",
        completion_event="cinematic_arrival_finished",
        learning_objectives=(
            "no_hp_bars_read_posture",
            "world_alive_before_action",
        ),
        summary=(
            "Cid greets at the elevator. Pigeon flies overhead "
            "(Tier-0 ambient). The player reads Cid's posture, "
            "not a number, to know he's healthy."
        ),
    ),
    GateBeat(
        gate=TutorialGate.WEIGHT,
        minute_window=(3, 10),
        tutorial_npc="pellah",
        tutorial_zone="bastok_mines",
        layered_scene_tag="Tutorial:gate_weight",
        completion_event="hammer_delivered_doublet_received",
        learning_objectives=(
            "weight_drives_movement",
            "carry_vs_equipped_weight",
        ),
        summary=(
            "Player carries a hammer (weight 12) to Pellah; the "
            "movement slowdown is felt. Pellah hands back a "
            "Cotton Doublet (weight 4) to teach equipped weight."
        ),
    ),
    GateBeat(
        gate=TutorialGate.FIRST_COMBAT,
        minute_window=(10, 25),
        tutorial_npc="goblin_pickpocket",
        tutorial_zone="bastok_mines_south_gate",
        layered_scene_tag="Tutorial:gate_first_combat",
        completion_event="goblin_pickpocket_defeated",
        learning_objectives=(
            "audible_grunts_per_swing",
            "visible_health_stage_transitions",
            "chain_marker_appears_on_ws",
            "skillchain_close_window_exists",
        ),
        summary=(
            "First fight. Goblin Pickpocket (lvl 1). Player lands "
            "a weapon skill, the white-flash chain marker appears, "
            "and Cid (watching) shouts 'Close it!' to teach the "
            "8-second close window. First time, they miss."
        ),
    ),
    GateBeat(
        gate=TutorialGate.REVEAL_SKILL,
        minute_window=(25, 40),
        tutorial_npc="sleeping_fomor",
        tutorial_zone="bastok_mines_shafts",
        layered_scene_tag="Tutorial:gate_reveal_skill",
        completion_event="reveal_skill_used_on_fomor",
        learning_objectives=(
            "hp_is_words_not_numbers",
            "mood_is_part_of_world",
            "damage_state_is_a_word",
        ),
        summary=(
            "Player descends, finds a sleeping fomor, uses their "
            "job-specific reveal skill, sees vague descriptors "
            "('Tough; (looks furious); (slightly hurt)')."
        ),
    ),
    GateBeat(
        gate=TutorialGate.INTERVENTION,
        minute_window=(40, 55),
        tutorial_npc="wounded_miner",
        tutorial_zone="bastok_mines",
        layered_scene_tag="Tutorial:gate_intervention",
        completion_event="cure_cast_on_wounded_miner",
        learning_objectives=(
            "cures_heal_visibly",
            "no_number_just_better_posture",
        ),
        summary=(
            "Player buys Cure I from the apothecary, returns to a "
            "bloodied miner, casts. Miner grunts in relief, "
            "posture straightens, decals fade."
        ),
    ),
    GateBeat(
        gate=TutorialGate.CHAIN,
        minute_window=(55, 75),
        tutorial_npc="cid",
        tutorial_zone="bastok_mines_training_dummy",
        layered_scene_tag="Tutorial:gate_chain",
        completion_event="player_closed_chains_required",
        learning_objectives=(
            "chain_close_timing",
            "audible_callout_in_player_voice",
            "first_emotional_payoff_moment",
        ),
        summary=(
            "Controlled training fight with Cid as partner. After "
            "3-5 successful chain closes the player audibly shouts "
            "the chain name in their cloned voice — first emotional "
            "payoff."
        ),
    ),
    GateBeat(
        gate=TutorialGate.BOSS,
        minute_window=(75, 90),
        tutorial_npc="goblin_smithy",
        tutorial_zone="bastok_mines_side_tunnel",
        layered_scene_tag="Tutorial:gate_boss",
        completion_event="goblin_smithy_defeated",
        learning_objectives=(
            "phase_transitions_are_visible",
            "named_attack_telegraphs_can_be_dodged",
            "boss_recipe_minimum",
        ),
        summary=(
            "Tier-1 boss recipe: Goblin Smithy (lvl 5). 4 attacks, "
            "3 phases, no critic. Named attack Hammer Slam (cone, "
            "1.5s telegraph). Three casts: hit, dodge, dodge."
        ),
    ),
)


# Number of successful chain closes required to clear the CHAIN gate.
# Doc: 'After 3-5 successful chain closes...'. We anchor at 3 — the
# minimum the doc allows so a competent player isn't drilled.
CHAIN_GATE_CLOSES_REQUIRED = 3


# Gate -> beat lookup. Built once at import time.
GATE_TO_BEAT: dict[TutorialGate, GateBeat] = {
    beat.gate: beat for beat in GATE_TABLE
}


def get_beat(gate: TutorialGate) -> GateBeat:
    """Return the beat for a gate. Raises KeyError on unknown."""
    return GATE_TO_BEAT[gate]


def first_gate() -> TutorialGate:
    return GATE_TABLE[0].gate


def last_gate() -> TutorialGate:
    return GATE_TABLE[-1].gate


def gate_after(gate: TutorialGate) -> t.Optional[TutorialGate]:
    """The next gate after `gate`, or None if `gate` is the last."""
    seq = [b.gate for b in GATE_TABLE]
    try:
        idx = seq.index(gate)
    except ValueError:
        return None
    if idx + 1 >= len(seq):
        return None
    return seq[idx + 1]


def all_layered_scene_tags() -> tuple[str, ...]:
    """All 7 Tutorial:gate_<n> tags, in canonical order."""
    return tuple(b.layered_scene_tag for b in GATE_TABLE)
