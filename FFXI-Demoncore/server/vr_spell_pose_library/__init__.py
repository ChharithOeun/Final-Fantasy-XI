"""VR spell pose library — pose sequences as spell intent.

A "pose" here is a recognizable physical action a VR
player performs to indicate they're casting a spell.
Three sources feed it:

    SEAL    a NIN hand seal (Tiger / Boar / Dog ...)
    GESTURE a free-form VR gesture (POINT / THROW /
            DRAW_RUNE / SLASH / SEAL_FORM / PUNCH)

The library maps an ORDERED SEQUENCE of pose elements
to a spell intent. Examples:

    [SEAL.TIGER, SEAL.BOAR, SEAL.DOG]
        -> Katon: Ichi (fire ninjutsu, level 1)

    [GESTURE.POINT, GESTURE.THROW]
        -> a thrown elemental projectile (BLM stub spell)

    [GESTURE.DRAW_RUNE]
        -> a GEO geomantic placement

This is the bridge between vr_gesture_recognizer (raw
motion -> kind) and game-side spell casting. The recognizer
gives you a stream of recognized gestures; this library
tells you what they ADD UP to.

Live partial-match: as the player works through a sequence
candidates_with_prefix() returns the still-possible spells.
That feeds a HUD that says "Halfway to Suiton: Ichi" or
"Doton: Ichi or Doton: Ni — finish with Ram for Ichi".

Design notes
------------
- Sequences are immutable tuples of pose elements.
- Two poses with the same sequence collide — the second
  registration is rejected (returns False).
- Empty sequences are rejected.
- Lookups are exact: the input sequence must equal the
  registered sequence. For "I just see the first 2 of
  3 elements", use candidates_with_prefix() instead.
- Caller-supplied "spell_intent" is opaque to this module —
  it's a string (or string-like) the spell engine
  understands. We don't validate it.

Public surface
--------------
    PoseSource enum
    PoseElement dataclass (frozen) — (source, code)
    SpellPose dataclass (frozen)
    VrSpellPoseLibrary
        .register_pose(spell_pose) -> bool
        .lookup_by_sequence(sequence) -> Optional[SpellPose]
        .candidates_with_prefix(prefix) -> list[SpellPose]
        .all_poses() -> list[SpellPose]
        .unregister(pose_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PoseSource(str, enum.Enum):
    SEAL = "seal"
    GESTURE = "gesture"


@dataclasses.dataclass(frozen=True)
class PoseElement:
    source: PoseSource
    code: str  # e.g. "tiger" or "draw_rune"


@dataclasses.dataclass(frozen=True)
class SpellPose:
    pose_id: str
    display_name: str
    sequence: tuple[PoseElement, ...]
    spell_intent: str  # opaque key the spell engine reads


@dataclasses.dataclass
class VrSpellPoseLibrary:
    _by_id: dict[str, SpellPose] = dataclasses.field(
        default_factory=dict,
    )
    _by_sequence: dict[
        tuple[PoseElement, ...], SpellPose,
    ] = dataclasses.field(default_factory=dict)

    def register_pose(self, spell_pose: SpellPose) -> bool:
        if not spell_pose.pose_id:
            return False
        if not spell_pose.sequence:
            return False
        if spell_pose.pose_id in self._by_id:
            return False
        if spell_pose.sequence in self._by_sequence:
            return False
        self._by_id[spell_pose.pose_id] = spell_pose
        self._by_sequence[spell_pose.sequence] = spell_pose
        return True

    def lookup_by_sequence(
        self, *, sequence: t.Sequence[PoseElement],
    ) -> t.Optional[SpellPose]:
        return self._by_sequence.get(tuple(sequence))

    def candidates_with_prefix(
        self, *, prefix: t.Sequence[PoseElement],
    ) -> list[SpellPose]:
        pre = tuple(prefix)
        if not pre:
            # Empty prefix matches everything — useful as
            # a "what could I cast" listing
            return list(self._by_id.values())
        out = []
        for seq, pose in self._by_sequence.items():
            if len(seq) >= len(pre) and seq[:len(pre)] == pre:
                out.append(pose)
        # Sort for stable ordering: shorter sequences first
        # (closer to completion), then by display_name
        out.sort(key=lambda p: (len(p.sequence), p.display_name))
        return out

    def all_poses(self) -> list[SpellPose]:
        return list(self._by_id.values())

    def unregister(self, *, pose_id: str) -> bool:
        if pose_id not in self._by_id:
            return False
        pose = self._by_id.pop(pose_id)
        self._by_sequence.pop(pose.sequence, None)
        return True


__all__ = [
    "PoseSource", "PoseElement", "SpellPose",
    "VrSpellPoseLibrary",
]
