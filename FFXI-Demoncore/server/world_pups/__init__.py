"""World PUPs + Rogue Automaton NMs.

Per the user direction: 'my fav job is PUP, let's create a whole
bunch of them scattered around the world. Also have a bunch of
Rogue Automatons with no master roaming the world as Notorious
Monsters that are extremely difficult to kill, they always drop an
insane reward, and each respawns every 24hrs earth time.'

Two halves:
    pup_npcs.py        - 10+ wandering world PUP NPCs with their
                          deployed automatons. Distinct from trusts:
                          these live in zones and have their own
                          schedules + interactions.
    rogue_automatons.py - 10 Rogue Automaton NMs with apex difficulty,
                          insane drops, and 24hr earth-time respawn.
    respawn_timer.py   - Tracks the next-spawn-at moment per NM.

Public surface:
    PupNpcSpec, PUP_NPC_CATALOG, pup_npcs_in_zone
    RogueAutomatonNM, ROGUE_AUTOMATON_NMS, rogue_automaton_for
    RespawnTracker, ROGUE_AUTOMATON_RESPAWN_SECONDS
"""
from .pup_npcs import (
    PUP_NPC_CATALOG,
    PupNpcSpec,
    pup_npcs_in_zone,
)
from .respawn_timer import (
    ROGUE_AUTOMATON_RESPAWN_SECONDS,
    RespawnTracker,
)
from .rogue_automatons import (
    ROGUE_AUTOMATON_NMS,
    RogueAutomatonNM,
    rogue_automaton_for,
)
from .whm_neutral_rogues import (
    HEAL_PULSE_INTERVAL_SECONDS,
    HEAL_PULSE_RADIUS_CM,
    NEUTRAL_WHM_ROGUES,
    NeutralRogueState,
    NeutralWhmRogueManager,
    NeutralWhmRogueRuntime,
    NeutralWhmRogueSpec,
)

__all__ = [
    "PupNpcSpec",
    "PUP_NPC_CATALOG",
    "pup_npcs_in_zone",
    "RogueAutomatonNM",
    "ROGUE_AUTOMATON_NMS",
    "rogue_automaton_for",
    "RespawnTracker",
    "ROGUE_AUTOMATON_RESPAWN_SECONDS",
    "NeutralWhmRogueSpec",
    "NeutralWhmRogueRuntime",
    "NeutralWhmRogueManager",
    "NeutralRogueState",
    "NEUTRAL_WHM_ROGUES",
    "HEAL_PULSE_INTERVAL_SECONDS",
    "HEAL_PULSE_RADIUS_CM",
]
