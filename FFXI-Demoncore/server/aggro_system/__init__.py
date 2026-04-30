"""Demoncore aggro + sensory pursuit system.

Per SEAMLESS_WORLD.md. Tracks per-mob, per-player aggro state with
sensory envelopes (sight + sound + smell), state machine transitions
(neutral → suspicious → aggressive → enraged → boss_enraged), and
cross-zone pursuit logic.

Public surface:
    AggroState                — enum of current aggro level
    SensoryProfile             — per-mob sensory configuration
    AggroTracker               — owns state per (mob, player) pair
    AggroTracker.tick          — advance state given current world snapshot
    AggroTracker.notify_damage — refresh persistence + escalate state
    AggroTracker.is_pursuing   — query current pursuit state
"""
from .tracker import (
    AggroState,
    AggroTracker,
    PlayerSnapshot,
    SensoryProfile,
    can_perceive_player,
    compute_player_sound_level,
)

__all__ = [
    "AggroState",
    "AggroTracker",
    "SensoryProfile",
    "PlayerSnapshot",
    "can_perceive_player",
    "compute_player_sound_level",
]
