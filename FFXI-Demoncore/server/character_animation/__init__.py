"""Character animation — per-character animation set.

Holds the catalog of animation clips for FFXI's five
playable races (HUME, ELVAAN, TARUTARU, MITHRA, GALKA) at
each gender. Each clip has a kind (IDLE, WALK, GESTURE_BOW,
REACTION_SURPRISE...), a duration, a looping flag, an
overlay layer, and a set of kinds it can blend with.

Real grooms/ rigs can have hundreds of clips; this module
doesn't ship them all — it ships the lookup discipline.
``best_match(kind, race, gender)`` falls back from the
exact (race, gender) variant to the same race in the other
gender, then to the HUME default for that gender, then to
HUME any-gender. That fallback chain means a half-finished
race never crashes the game; it just borrows hume animation
until the riggers catch up.

Blending rules say which kinds can layer over which: e.g.
TALK_HEAD (FACE_ONLY) layers over WALK (root motion) layers
over IDLE — three layers — but COMBAT_STANCE blocks WALK
because the lower body is locked. The blending graph is
hand-authored from the kinds' overlay layers.

emotion_to_anim() maps a mood tag to the natural reaction
animation: HAPPY -> REACTION_LAUGH, AFRAID -> REACTION_FEAR,
ANGRY -> REACTION_ANGER. crowd_director uses this to make
NPCs visibly emote without having to know about animation
clip IDs.

Public surface
--------------
    AnimationKind enum
    Race enum
    Gender enum
    OverlayLayer enum
    AnimClip dataclass (frozen)
    AnimationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AnimationKind(enum.Enum):
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    SPRINT = "sprint"
    SIT = "sit"
    LEAN = "lean"
    TALK_HEAD = "talk_head"
    GESTURE_POINT = "gesture_point"
    GESTURE_BECKON = "gesture_beckon"
    GESTURE_BOW = "gesture_bow"
    GESTURE_DISMISS = "gesture_dismiss"
    REACTION_SURPRISE = "reaction_surprise"
    REACTION_LAUGH = "reaction_laugh"
    REACTION_ANGER = "reaction_anger"
    REACTION_FEAR = "reaction_fear"
    COMBAT_STANCE = "combat_stance"
    CAST_BEGIN = "cast_begin"
    CAST_RELEASE = "cast_release"
    HIT_FLINCH = "hit_flinch"
    KO_FALL = "ko_fall"
    EMOTE_WAVE = "emote_wave"
    EMOTE_NOD = "emote_nod"
    EMOTE_HEADSHAKE = "emote_headshake"
    EMOTE_SHRUG = "emote_shrug"
    EMOTE_FACEPALM = "emote_facepalm"


class Race(enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    GALKA = "galka"


class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"


class OverlayLayer(enum.Enum):
    NONE = "none"           # full-body, root-motion-capable
    UPPER_BODY = "upper_body"  # arms / chest only
    FACE_ONLY = "face_only"    # head + eyes + jaw


@dataclasses.dataclass(frozen=True)
class AnimClip:
    clip_id: str
    kind: AnimationKind
    race: Race
    gender: Gender
    clip_uri: str
    duration_s: float
    looping: bool
    blendable_with: frozenset[AnimationKind] = frozenset()
    root_motion: bool = False
    overlay_layer: OverlayLayer = OverlayLayer.NONE


# Default blend graph by overlay layer. Used when a clip is
# registered without an explicit blendable_with set, and as
# the source of truth for can_blend().
_LAYER_BLENDS: dict[
    OverlayLayer, frozenset[OverlayLayer],
] = {
    # Full-body root-motion clips can mix with upper-body
    # gestures and face-only animation.
    OverlayLayer.NONE: frozenset({
        OverlayLayer.UPPER_BODY,
        OverlayLayer.FACE_ONLY,
    }),
    # Upper-body gestures sit on top of full-body locomotion
    # and below face-only chatter.
    OverlayLayer.UPPER_BODY: frozenset({
        OverlayLayer.NONE,
        OverlayLayer.FACE_ONLY,
    }),
    # Face-only animation layers on top of everything.
    OverlayLayer.FACE_ONLY: frozenset({
        OverlayLayer.NONE,
        OverlayLayer.UPPER_BODY,
    }),
}


# Kinds that lock the lower body and therefore block
# WALK / RUN / SPRINT regardless of overlay layer.
_LOWER_BODY_LOCKING: frozenset[AnimationKind] = frozenset({
    AnimationKind.COMBAT_STANCE,
    AnimationKind.SIT,
    AnimationKind.LEAN,
    AnimationKind.KO_FALL,
    AnimationKind.CAST_BEGIN,
    AnimationKind.CAST_RELEASE,
})


_LOCOMOTION: frozenset[AnimationKind] = frozenset({
    AnimationKind.WALK,
    AnimationKind.RUN,
    AnimationKind.SPRINT,
})


# Mood -> animation kind for emotion_to_anim().
_EMOTION_MAP: dict[str, AnimationKind] = {
    "HAPPY": AnimationKind.REACTION_LAUGH,
    "AFRAID": AnimationKind.REACTION_FEAR,
    "ANGRY": AnimationKind.REACTION_ANGER,
    "SURPRISED": AnimationKind.REACTION_SURPRISE,
    "NEUTRAL": AnimationKind.IDLE,
    "WEARY": AnimationKind.IDLE,
    "TENDER": AnimationKind.EMOTE_NOD,
    "SAD": AnimationKind.EMOTE_FACEPALM,
}


def _default_overlay_for(kind: AnimationKind) -> OverlayLayer:
    if kind in (
        AnimationKind.TALK_HEAD,
        AnimationKind.EMOTE_NOD,
        AnimationKind.EMOTE_HEADSHAKE,
    ):
        return OverlayLayer.FACE_ONLY
    if kind in (
        AnimationKind.GESTURE_POINT,
        AnimationKind.GESTURE_BECKON,
        AnimationKind.GESTURE_BOW,
        AnimationKind.GESTURE_DISMISS,
        AnimationKind.EMOTE_WAVE,
        AnimationKind.EMOTE_SHRUG,
        AnimationKind.EMOTE_FACEPALM,
    ):
        return OverlayLayer.UPPER_BODY
    return OverlayLayer.NONE


@dataclasses.dataclass
class AnimationSystem:
    _clips: dict[str, AnimClip] = dataclasses.field(
        default_factory=dict,
    )
    # Index: (kind, race, gender) -> tuple of clip_ids (in
    # registration order).
    _index: dict[
        tuple[AnimationKind, Race, Gender],
        list[str],
    ] = dataclasses.field(default_factory=dict)
    _idle_cursor: dict[
        tuple[Race, Gender], int,
    ] = dataclasses.field(default_factory=dict)

    def register_clip(self, clip: AnimClip) -> None:
        if not clip.clip_id:
            raise ValueError("clip_id required")
        if clip.duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        if clip.clip_id in self._clips:
            raise ValueError(
                f"duplicate clip_id: {clip.clip_id}",
            )
        self._clips[clip.clip_id] = clip
        key = (clip.kind, clip.race, clip.gender)
        self._index.setdefault(key, []).append(clip.clip_id)

    def get(self, clip_id: str) -> AnimClip:
        if clip_id not in self._clips:
            raise KeyError(f"unknown clip: {clip_id}")
        return self._clips[clip_id]

    def lookup(
        self,
        kind: AnimationKind,
        race: Race,
        gender: Gender,
    ) -> tuple[AnimClip, ...]:
        """All clips matching exactly (kind, race, gender)."""
        key = (kind, race, gender)
        return tuple(
            self._clips[cid] for cid in self._index.get(key, [])
        )

    def best_match(
        self,
        kind: AnimationKind,
        race: Race,
        gender: Gender,
    ) -> AnimClip | None:
        """Best clip with fallback chain.

        1. Exact (kind, race, gender)
        2. Same race, opposite gender
        3. HUME, requested gender
        4. HUME, opposite gender
        Returns None if nothing in the catalog covers the kind.
        """
        # 1.
        for cid in self._index.get((kind, race, gender), []):
            return self._clips[cid]
        # 2.
        opp = (
            Gender.FEMALE if gender == Gender.MALE
            else Gender.MALE
        )
        for cid in self._index.get((kind, race, opp), []):
            return self._clips[cid]
        # 3.
        for cid in self._index.get((kind, Race.HUME, gender), []):
            return self._clips[cid]
        # 4.
        for cid in self._index.get((kind, Race.HUME, opp), []):
            return self._clips[cid]
        return None

    def all_for_race(
        self, race: Race,
    ) -> tuple[AnimClip, ...]:
        return tuple(
            sorted(
                (c for c in self._clips.values() if c.race == race),
                key=lambda c: c.clip_id,
            )
        )

    def all_kinds_for(
        self, race: Race, gender: Gender,
    ) -> frozenset[AnimationKind]:
        return frozenset(
            kind for (kind, r, g) in self._index
            if r == race and g == gender
        )

    def can_blend(
        self,
        kind_a: AnimationKind,
        kind_b: AnimationKind,
    ) -> bool:
        if kind_a == kind_b:
            return False
        # Lower-body lock blocks all locomotion.
        if (
            kind_a in _LOWER_BODY_LOCKING
            and kind_b in _LOCOMOTION
        ):
            return False
        if (
            kind_b in _LOWER_BODY_LOCKING
            and kind_a in _LOCOMOTION
        ):
            return False
        # Two locomotion kinds don't blend with each other.
        if kind_a in _LOCOMOTION and kind_b in _LOCOMOTION:
            return False
        # Two lower-body-locking kinds don't blend either.
        if (
            kind_a in _LOWER_BODY_LOCKING
            and kind_b in _LOWER_BODY_LOCKING
        ):
            return False
        layer_a = _default_overlay_for(kind_a)
        layer_b = _default_overlay_for(kind_b)
        if layer_a == layer_b:
            return False
        return layer_b in _LAYER_BLENDS[layer_a]

    def emotion_to_anim(self, emotion_tag: str) -> AnimationKind:
        tag = emotion_tag.upper().strip()
        if tag not in _EMOTION_MAP:
            return AnimationKind.IDLE
        return _EMOTION_MAP[tag]

    def idle_variation_for(
        self, race: Race, gender: Gender,
    ) -> AnimClip | None:
        """Round-robin pick across registered IDLE clips for
        this (race, gender). Returns None if none exist."""
        key = (race, gender)
        clips = self._index.get(
            (AnimationKind.IDLE, race, gender), [],
        )
        if not clips:
            # Try fallback to best_match for IDLE.
            return self.best_match(
                AnimationKind.IDLE, race, gender,
            )
        cursor = self._idle_cursor.get(key, 0)
        chosen = clips[cursor % len(clips)]
        self._idle_cursor[key] = (cursor + 1) % len(clips)
        return self._clips[chosen]

    def overlay_layer_for(
        self, kind: AnimationKind,
    ) -> OverlayLayer:
        return _default_overlay_for(kind)

    def clip_count(self) -> int:
        return len(self._clips)


def make_default_clip(
    kind: AnimationKind,
    race: Race,
    gender: Gender,
    clip_id: str | None = None,
    duration_s: float = 1.5,
    looping: bool | None = None,
) -> AnimClip:
    """Convenience builder using the default overlay layer
    + a sensible looping default. Used for fixtures."""
    cid = clip_id or (
        f"clip_{kind.value}_{race.value}_{gender.value}"
    )
    if looping is None:
        looping = kind in (
            AnimationKind.IDLE,
            AnimationKind.WALK,
            AnimationKind.RUN,
            AnimationKind.SPRINT,
            AnimationKind.SIT,
            AnimationKind.LEAN,
            AnimationKind.COMBAT_STANCE,
            AnimationKind.TALK_HEAD,
        )
    layer = _default_overlay_for(kind)
    rm = (
        kind in _LOCOMOTION
        and layer == OverlayLayer.NONE
    )
    return AnimClip(
        clip_id=cid,
        kind=kind,
        race=race,
        gender=gender,
        clip_uri=f"anim://{cid}",
        duration_s=duration_s,
        looping=looping,
        root_motion=rm,
        overlay_layer=layer,
    )


def populate_default_library(sys: AnimationSystem) -> int:
    """Pre-populate ~50 representative clips covering all
    races + both genders for the high-value kinds (IDLE,
    WALK, TALK_HEAD, REACTION_SURPRISE) plus a handful of
    extras. Returns the number of clips registered."""
    n = 0
    high_value = (
        AnimationKind.IDLE,
        AnimationKind.WALK,
        AnimationKind.TALK_HEAD,
        AnimationKind.REACTION_SURPRISE,
    )
    for race in Race:
        for gender in Gender:
            # mithra has no MALE in retail FFXI; we still
            # register clips so the catalog is symmetric and
            # the fallback chain has something to land on.
            for kind in high_value:
                sys.register_clip(make_default_clip(
                    kind, race, gender,
                ))
                n += 1
    # A few extras for HUME baseline so fallbacks have
    # something rich to hit.
    extras = (
        AnimationKind.RUN,
        AnimationKind.GESTURE_BOW,
        AnimationKind.EMOTE_WAVE,
        AnimationKind.REACTION_LAUGH,
        AnimationKind.REACTION_FEAR,
        AnimationKind.COMBAT_STANCE,
    )
    for kind in extras:
        sys.register_clip(make_default_clip(
            kind, Race.HUME, Gender.MALE,
        ))
        sys.register_clip(make_default_clip(
            kind, Race.HUME, Gender.FEMALE,
        ))
        n += 2
    return n


__all__ = [
    "AnimationKind",
    "Race",
    "Gender",
    "OverlayLayer",
    "AnimClip",
    "AnimationSystem",
    "make_default_clip",
    "populate_default_library",
]
