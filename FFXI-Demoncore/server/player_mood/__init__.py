"""Player mood / morale — parallel to NPC mood.

Players carry a mood vector that AI-driven NPCs can read off
(via npc_dialogue_system + entity_memory) and that gameplay
systems can use to scale tempo, regen, and morale-driven
flavor. Different from honor_reputation (long-term standing) —
mood is the SHORT-TERM emotional state.

Vector
------
4 axes, each in [-100, +100]:

    confidence     +winning streak / -KO streak
    energy         +rested / -fatigued
    cohesion       +good party experience / -fights with party
    grit           +tough fights survived / -frustration

The vector decays toward zero each tick (10 minutes default).
Mood events bump components based on the event kind. Snapshots
expose composite booleans like `is_demoralized()`,
`is_high_morale()`.

Public surface
--------------
    MoodAxis enum
    MoodVector dataclass
    MoodEventKind enum
    MoodRegistry
        .apply_event(player_id, kind, magnitude)
        .vector_for(player_id) -> MoodVector
        .tick(player_id, now_seconds) — applies decay
        .is_high_morale(player_id) / .is_demoralized(player_id)
        .combat_speed_multiplier(player_id) -> float
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Decay applied per tick (in subtraction toward 0).
DECAY_PER_TICK = 5
DEFAULT_TICK_INTERVAL_SECONDS = 600.0   # 10 min

VECTOR_MIN = -100
VECTOR_MAX = 100

# Thresholds for composite booleans.
HIGH_MORALE_AVG = 30
DEMORALIZED_AVG = -30


class MoodAxis(str, enum.Enum):
    CONFIDENCE = "confidence"
    ENERGY = "energy"
    COHESION = "cohesion"
    GRIT = "grit"


class MoodEventKind(str, enum.Enum):
    KILLED_NM = "killed_nm"               # +confidence +grit
    KILLED_BOSS = "killed_boss"           # +confidence +grit hugely
    KO_DEATH = "ko_death"                 # -confidence -energy
    PARTY_WIPE = "party_wipe"             # -confidence -cohesion
    REVIVED_BY_ALLY = "revived_by_ally"   # +cohesion
    PARTY_QUARREL = "party_quarrel"       # -cohesion
    LONG_REST = "long_rest"               # +energy
    LONG_GRIND = "long_grind"             # -energy
    LEVEL_UP = "level_up"                 # +confidence +grit
    QUEST_COMPLETED = "quest_completed"   # +confidence +cohesion
    LOST_BOUNTY = "lost_bounty"           # -grit -confidence
    PERFECT_VICTORY = "perfect_victory"   # +confidence
    NEAR_DEATH_SURVIVED = "near_death_survived"  # +grit


# Per-event default magnitudes per axis.
_EVENT_DELTAS: dict[
    MoodEventKind, dict[MoodAxis, int],
] = {
    MoodEventKind.KILLED_NM: {
        MoodAxis.CONFIDENCE: 10, MoodAxis.GRIT: 5,
    },
    MoodEventKind.KILLED_BOSS: {
        MoodAxis.CONFIDENCE: 30, MoodAxis.GRIT: 20,
    },
    MoodEventKind.KO_DEATH: {
        MoodAxis.CONFIDENCE: -25, MoodAxis.ENERGY: -10,
    },
    MoodEventKind.PARTY_WIPE: {
        MoodAxis.CONFIDENCE: -30, MoodAxis.COHESION: -15,
    },
    MoodEventKind.REVIVED_BY_ALLY: {
        MoodAxis.COHESION: 20, MoodAxis.CONFIDENCE: 5,
    },
    MoodEventKind.PARTY_QUARREL: {
        MoodAxis.COHESION: -25,
    },
    MoodEventKind.LONG_REST: {
        MoodAxis.ENERGY: 25,
    },
    MoodEventKind.LONG_GRIND: {
        MoodAxis.ENERGY: -20,
    },
    MoodEventKind.LEVEL_UP: {
        MoodAxis.CONFIDENCE: 15, MoodAxis.GRIT: 10,
    },
    MoodEventKind.QUEST_COMPLETED: {
        MoodAxis.CONFIDENCE: 10, MoodAxis.COHESION: 5,
    },
    MoodEventKind.LOST_BOUNTY: {
        MoodAxis.GRIT: -10, MoodAxis.CONFIDENCE: -10,
    },
    MoodEventKind.PERFECT_VICTORY: {
        MoodAxis.CONFIDENCE: 15,
    },
    MoodEventKind.NEAR_DEATH_SURVIVED: {
        MoodAxis.GRIT: 20,
    },
}


@dataclasses.dataclass
class MoodVector:
    confidence: int = 0
    energy: int = 0
    cohesion: int = 0
    grit: int = 0
    last_tick_at_seconds: float = 0.0

    def __post_init__(self) -> None:
        for axis, val in self.as_dict().items():
            if not (VECTOR_MIN <= val <= VECTOR_MAX):
                raise ValueError(
                    f"axis {axis.value}={val} out of range",
                )

    def as_dict(self) -> dict[MoodAxis, int]:
        return {
            MoodAxis.CONFIDENCE: self.confidence,
            MoodAxis.ENERGY: self.energy,
            MoodAxis.COHESION: self.cohesion,
            MoodAxis.GRIT: self.grit,
        }

    def average(self) -> float:
        return sum(self.as_dict().values()) / 4.0


def _clamp(v: int) -> int:
    return max(VECTOR_MIN, min(VECTOR_MAX, v))


@dataclasses.dataclass
class MoodRegistry:
    decay_per_tick: int = DECAY_PER_TICK
    tick_interval_seconds: float = DEFAULT_TICK_INTERVAL_SECONDS
    _vectors: dict[str, MoodVector] = dataclasses.field(
        default_factory=dict,
    )

    def vector_for(self, player_id: str) -> MoodVector:
        v = self._vectors.get(player_id)
        if v is None:
            v = MoodVector()
            self._vectors[player_id] = v
        return v

    def apply_event(
        self, *, player_id: str, kind: MoodEventKind,
        magnitude_pct: int = 100,
    ) -> MoodVector:
        v = self.vector_for(player_id)
        deltas = _EVENT_DELTAS.get(kind, {})
        for axis, base in deltas.items():
            scaled = (base * magnitude_pct) // 100
            cur = v.as_dict()[axis]
            new = _clamp(cur + scaled)
            setattr(v, axis.value, new)
        return v

    def tick(
        self, *, player_id: str, now_seconds: float,
    ) -> MoodVector:
        v = self.vector_for(player_id)
        elapsed = now_seconds - v.last_tick_at_seconds
        if elapsed < self.tick_interval_seconds:
            return v
        ticks = int(elapsed // self.tick_interval_seconds)
        for axis in MoodAxis:
            cur = v.as_dict()[axis]
            if cur > 0:
                new = max(0, cur - self.decay_per_tick * ticks)
            elif cur < 0:
                new = min(0, cur + self.decay_per_tick * ticks)
            else:
                new = 0
            setattr(v, axis.value, new)
        v.last_tick_at_seconds = now_seconds
        return v

    def is_high_morale(self, player_id: str) -> bool:
        return self.vector_for(player_id).average() >= HIGH_MORALE_AVG

    def is_demoralized(self, player_id: str) -> bool:
        return self.vector_for(player_id).average() <= DEMORALIZED_AVG

    def combat_speed_multiplier(
        self, player_id: str,
    ) -> float:
        """High morale slightly speeds combat (TP gain), low
        morale slows it. Range [0.85, 1.15]."""
        avg = self.vector_for(player_id).average()
        return 1.0 + (avg / 100) * 0.15

    def total_tracked(self) -> int:
        return len(self._vectors)


__all__ = [
    "DECAY_PER_TICK", "DEFAULT_TICK_INTERVAL_SECONDS",
    "VECTOR_MIN", "VECTOR_MAX",
    "HIGH_MORALE_AVG", "DEMORALIZED_AVG",
    "MoodAxis", "MoodEventKind",
    "MoodVector", "MoodRegistry",
]
