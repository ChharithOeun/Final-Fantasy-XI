"""Demoncore player state machine.

Owns the hardcore-death + Fomor-transition state machine per
HARDCORE_DEATH.md + FOMOR_GEAR_PROGRESSION.md. The most important
state machine in Demoncore — it defines the apex difficulty pillar:
at level 99, death starts a 1-hour permadeath timer, after which the
player's character becomes an AI-controlled Fomor in the world.

Public surface:
    PlayerStateMachine
    PlayerLifecycle (enum)
    DeathPenalty
"""
from .machine import (
    DeathEvent,
    DeathPenalty,
    PlayerLifecycle,
    PlayerSnapshot,
    PlayerStateMachine,
)

__all__ = [
    "PlayerStateMachine",
    "PlayerLifecycle",
    "PlayerSnapshot",
    "DeathEvent",
    "DeathPenalty",
]
