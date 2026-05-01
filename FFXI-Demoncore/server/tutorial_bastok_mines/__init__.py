"""Bastok Mines tutorial — the choreographed first 90 minutes.

Per TUTORIAL_BASTOK_MINES.md the new player is taught Demoncore's
visible / audible / weight grammar by the city itself. Seven gates,
each anchored to an NPC, a zone, a learning objective, and a
layered-scene tag.

Module layout:
    gates.py             - 7-gate beat table + GATE_TABLE constants
    state_machine.py     - per-character TutorialSession lifecycle
    flow.py              - orchestrator hook (event dispatch +
                              layered-scene tag emission)
    reveal_skill_pick.py - job -> reveal skill mapping (gate 4)
    boss_smithy.py       - Goblin Smithy boss recipe (gate 7)

Public surface:
    TutorialGate, GateBeat, GATE_TABLE, GATE_TO_BEAT,
        TUTORIAL_AGE_OUT_MINUTES, CHAIN_GATE_CLOSES_REQUIRED,
        get_beat, first_gate, last_gate, gate_after,
        all_layered_scene_tags
    TutorialSession, TutorialPhase
    TutorialFlow, FlowEvent, FlowResult
    RevealSkill, REVEAL_SKILL_BY_JOB, DEFAULT_REVEAL_SKILL,
        pick_reveal_skill
    BossAttack, BossPhase, BossRecipe, GOBLIN_SMITHY,
        GOBLIN_SMITHY_ATTACKS, GOBLIN_SMITHY_PHASES,
        hammer_slam_cast_sequence, named_attacks, total_phases
"""
from .boss_smithy import (
    GOBLIN_SMITHY,
    GOBLIN_SMITHY_ATTACKS,
    GOBLIN_SMITHY_PHASES,
    BossAttack,
    BossPhase,
    BossRecipe,
    hammer_slam_cast_sequence,
    named_attacks,
    total_phases,
)
from .flow import FlowEvent, FlowResult, TutorialFlow
from .gates import (
    CHAIN_GATE_CLOSES_REQUIRED,
    GATE_TABLE,
    GATE_TO_BEAT,
    TUTORIAL_AGE_OUT_MINUTES,
    GateBeat,
    TutorialGate,
    all_layered_scene_tags,
    first_gate,
    gate_after,
    get_beat,
    last_gate,
)
from .reveal_skill_pick import (
    DEFAULT_REVEAL_SKILL,
    REVEAL_SKILL_BY_JOB,
    RevealSkill,
    pick_reveal_skill,
)
from .state_machine import TutorialPhase, TutorialSession

__all__ = [
    # gates
    "TutorialGate", "GateBeat", "GATE_TABLE", "GATE_TO_BEAT",
    "TUTORIAL_AGE_OUT_MINUTES", "CHAIN_GATE_CLOSES_REQUIRED",
    "get_beat", "first_gate", "last_gate", "gate_after",
    "all_layered_scene_tags",
    # state_machine
    "TutorialSession", "TutorialPhase",
    # flow
    "TutorialFlow", "FlowEvent", "FlowResult",
    # reveal_skill_pick
    "RevealSkill", "REVEAL_SKILL_BY_JOB",
    "DEFAULT_REVEAL_SKILL", "pick_reveal_skill",
    # boss_smithy
    "BossAttack", "BossPhase", "BossRecipe",
    "GOBLIN_SMITHY", "GOBLIN_SMITHY_ATTACKS",
    "GOBLIN_SMITHY_PHASES",
    "hammer_slam_cast_sequence", "named_attacks", "total_phases",
]
