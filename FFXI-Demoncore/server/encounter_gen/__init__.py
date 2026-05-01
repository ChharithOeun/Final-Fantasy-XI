"""Encounter generator — dynamic mob spawn populator.

Given a zone + level + party size, produces a balanced spawn list
using the mob class library and zone-appropriate bestiary tables.

Public surface:
    EncounterGenerator
    EncounterRequest
    EncounterPlan
"""
from .generator import (
    EncounterGenerator,
    EncounterPlan,
    EncounterRequest,
    SpawnEntry,
)

__all__ = [
    "EncounterGenerator",
    "EncounterPlan",
    "EncounterRequest",
    "SpawnEntry",
]
