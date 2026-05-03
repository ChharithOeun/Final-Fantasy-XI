"""NPC emotional cascade — emotion propagates through relationships.

When something happens to one NPC (death, betrayal, joyful news,
ascension), the emotion ripples outward through the social
relationship graph: family first, then close friends, then loose
acquaintances. Each hop loses a fraction of intensity.

This is distinct from rumor_propagation (information) — emotional
cascade is about FEELING. A best friend's death drops the player's
trainer into grief, which flattens his quest dialogue and slows
his daily routine for days.

Public surface
--------------
    EmotionKind enum
    EmotionalEvent dataclass
    EmotionalState dataclass — current per-NPC mood
    Relationship dataclass
    NPCEmotionalCascade
        .add_relationship(npc_a, npc_b, closeness)
        .ingest(event)  -> propagates outward
        .state_for(npc_id) -> current emotional state
        .decay_step(seconds_elapsed)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default propagation falls off by this multiplier per hop.
DEFAULT_HOP_DECAY = 0.6
# Below this magnitude we stop propagating — saves work.
PROPAGATION_FLOOR = 5
# Default temporal decay per second (per-second exponential).
DEFAULT_TEMPORAL_DECAY_PER_SEC = 0.001


class EmotionKind(str, enum.Enum):
    GRIEF = "grief"
    JOY = "joy"
    ANGER = "anger"
    FEAR = "fear"
    PRIDE = "pride"
    SHAME = "shame"
    LOVE = "love"
    BETRAYAL = "betrayal"


# Some emotions amplify rivals, others muffle them.
# +1.0 = full propagation, 0.0 = no propagation, negative = inverts
# (e.g. an enemy's joy becomes our anger).
_KIND_RIVALRY_FACTOR: dict[EmotionKind, float] = {
    EmotionKind.GRIEF: 0.0,
    EmotionKind.JOY: 0.0,
    EmotionKind.ANGER: 0.5,
    EmotionKind.FEAR: 0.3,
    EmotionKind.PRIDE: -0.3,    # rival jealousy
    EmotionKind.SHAME: 0.2,
    EmotionKind.LOVE: 0.0,
    EmotionKind.BETRAYAL: 0.7,
}


@dataclasses.dataclass(frozen=True)
class Relationship:
    """Per-edge social tie.

    closeness: 0.0..1.0 — friend/family weight
    rivalry:   0.0..1.0 — adversarial overlay
    """
    other_npc_id: str
    closeness: float = 0.5
    rivalry: float = 0.0


@dataclasses.dataclass(frozen=True)
class EmotionalEvent:
    origin_npc_id: str
    emotion: EmotionKind
    magnitude: int             # 0..100
    triggered_at_seconds: float = 0.0
    note: str = ""


@dataclasses.dataclass
class EmotionalState:
    npc_id: str
    # Magnitude per emotion kind.
    magnitudes: dict[EmotionKind, int] = dataclasses.field(
        default_factory=dict,
    )
    last_updated_seconds: float = 0.0

    def dominant(self) -> t.Optional[EmotionKind]:
        if not self.magnitudes:
            return None
        return max(
            self.magnitudes.items(),
            key=lambda kv: kv[1],
        )[0]


@dataclasses.dataclass
class NPCEmotionalCascade:
    hop_decay: float = DEFAULT_HOP_DECAY
    propagation_floor: int = PROPAGATION_FLOOR
    temporal_decay_per_sec: float = DEFAULT_TEMPORAL_DECAY_PER_SEC
    _adj: dict[str, list[Relationship]] = dataclasses.field(
        default_factory=dict,
    )
    _states: dict[str, EmotionalState] = dataclasses.field(
        default_factory=dict,
    )

    def add_relationship(
        self, *, npc_a: str, npc_b: str,
        closeness: float = 0.5, rivalry: float = 0.0,
    ) -> None:
        self._adj.setdefault(npc_a, []).append(
            Relationship(
                other_npc_id=npc_b,
                closeness=closeness, rivalry=rivalry,
            ),
        )
        self._adj.setdefault(npc_b, []).append(
            Relationship(
                other_npc_id=npc_a,
                closeness=closeness, rivalry=rivalry,
            ),
        )

    def _bump(
        self, npc_id: str, emotion: EmotionKind,
        magnitude: int, now_seconds: float,
    ) -> None:
        st = self._states.setdefault(
            npc_id, EmotionalState(npc_id=npc_id),
        )
        st.magnitudes[emotion] = min(
            100, st.magnitudes.get(emotion, 0) + magnitude,
        )
        st.last_updated_seconds = now_seconds

    def ingest(self, *, event: EmotionalEvent) -> int:
        """Propagate emotion outward via BFS. Returns total
        npcs touched (including origin)."""
        # Origin gets full magnitude
        self._bump(
            event.origin_npc_id, event.emotion,
            event.magnitude, event.triggered_at_seconds,
        )
        seen: set[str] = {event.origin_npc_id}

        # BFS. Each entry: (npc_id, magnitude_at_this_hop)
        frontier: list[tuple[str, int]] = [
            (event.origin_npc_id, event.magnitude),
        ]
        touched = 1
        rivalry_factor = _KIND_RIVALRY_FACTOR[event.emotion]

        while frontier:
            next_frontier: list[tuple[str, int]] = []
            for npc, mag in frontier:
                next_mag_close = int(mag * self.hop_decay)
                if next_mag_close < self.propagation_floor:
                    continue
                for rel in self._adj.get(npc, []):
                    if rel.other_npc_id in seen:
                        continue
                    closeness_share = int(
                        next_mag_close * rel.closeness,
                    )
                    rivalry_share = int(
                        next_mag_close * rel.rivalry
                        * abs(rivalry_factor),
                    )
                    total = closeness_share + rivalry_share
                    if total < self.propagation_floor:
                        continue
                    # If rivalry-factor is negative, propagate
                    # the OPPOSITE emotion to rival
                    target_emotion = event.emotion
                    if (
                        rivalry_factor < 0
                        and rel.rivalry > 0
                    ):
                        target_emotion = (
                            _opposite_emotion(event.emotion)
                        )
                    self._bump(
                        rel.other_npc_id, target_emotion,
                        total, event.triggered_at_seconds,
                    )
                    seen.add(rel.other_npc_id)
                    touched += 1
                    next_frontier.append(
                        (rel.other_npc_id, total),
                    )
            frontier = next_frontier
        return touched

    def state_for(
        self, npc_id: str,
    ) -> t.Optional[EmotionalState]:
        return self._states.get(npc_id)

    def decay_step(
        self, *, elapsed_seconds: float,
    ) -> None:
        """Apply temporal decay to all emotional states."""
        decay = max(
            0.0,
            1.0 - self.temporal_decay_per_sec * elapsed_seconds,
        )
        for st in self._states.values():
            for k in list(st.magnitudes.keys()):
                new_v = int(st.magnitudes[k] * decay)
                if new_v <= 0:
                    del st.magnitudes[k]
                else:
                    st.magnitudes[k] = new_v

    def total_npcs_tracked(self) -> int:
        return len(self._states)


def _opposite_emotion(e: EmotionKind) -> EmotionKind:
    flip: dict[EmotionKind, EmotionKind] = {
        EmotionKind.GRIEF: EmotionKind.JOY,
        EmotionKind.JOY: EmotionKind.GRIEF,
        EmotionKind.ANGER: EmotionKind.FEAR,
        EmotionKind.FEAR: EmotionKind.ANGER,
        EmotionKind.PRIDE: EmotionKind.SHAME,
        EmotionKind.SHAME: EmotionKind.PRIDE,
        EmotionKind.LOVE: EmotionKind.BETRAYAL,
        EmotionKind.BETRAYAL: EmotionKind.ANGER,
    }
    return flip[e]


__all__ = [
    "DEFAULT_HOP_DECAY", "PROPAGATION_FLOOR",
    "EmotionKind", "Relationship",
    "EmotionalEvent", "EmotionalState",
    "NPCEmotionalCascade",
]
