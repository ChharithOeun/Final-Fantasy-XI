"""Dialogue lipsync — phoneme-driven lip animation.

Demoncore generates voice via voice_pipeline (Higgs Audio v2)
and feeds the resulting WAV into one of four lipsync engines:

    audio2face   — NVIDIA Audio2Face, blendshape curves over
                   ARKit 52, hero-quality, GPU-bound.
    rhubarb      — Rhubarb Lipsync, open-source, MIT, 9 mouth
                   shapes; cheap default for ambient NPCs.
    oculus       — Oculus Lipsync (Meta) Wovr SDK, 15 visemes.
    apple_speech — Apple Speech Synthesizer phoneme stream;
                   used when the iPhone is the capture rig.

Each lipsync track moves through PENDING → ANALYZING → READY
→ BAKED. The baked viseme curve is what UE5's MetaHuman face
control rig consumes.

Public surface
--------------
    LipsyncEngine enum
    TrackState enum
    LipsyncTrack dataclass (frozen)
    PHONEME_TO_VISEME mapping
    VISEMES tuple (14)
    DialogueLipsyncSystem
    engine_for, list_engines
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LipsyncEngine(enum.Enum):
    AUDIO2FACE = "audio2face"
    RHUBARB = "rhubarb"
    OCULUS = "oculus"
    APPLE_SPEECH = "apple_speech"


class TrackState(enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    READY = "ready"
    BAKED = "baked"


# Disney/Preston Blair → modern game viseme set, 14 shapes.
VISEMES: tuple[str, ...] = (
    "sil",     # silence / rest
    "PP",      # p / b / m
    "FF",      # f / v
    "TH",      # th
    "DD",      # t / d
    "kk",      # k / g
    "CH",      # ch / sh / j
    "SS",      # s / z
    "nn",      # n
    "RR",      # r
    "aa",      # ah
    "E",       # eh / ih
    "I",       # ee
    "O",       # oh
    # The 15th would be U; modern engines fold U into O.
)
assert len(VISEMES) == 14, len(VISEMES)


# ARPAbet-style English phoneme → viseme map (40 phonemes).
PHONEME_TO_VISEME: dict[str, str] = {
    # silence
    "sil": "sil", "sp":  "sil", "pause": "sil",
    # plosives / nasals (lips-closed family)
    "P":  "PP", "B":  "PP", "M":  "PP",
    # labiodental fricatives
    "F":  "FF", "V":  "FF",
    # dental fricatives
    "TH": "TH", "DH": "TH",
    # alveolar stops
    "T":  "DD", "D":  "DD",
    # velar stops
    "K":  "kk", "G":  "kk", "NG": "kk",
    # postalveolar
    "CH": "CH", "JH": "CH", "SH": "CH", "ZH": "CH",
    # alveolar fricatives
    "S":  "SS", "Z":  "SS",
    # nasal alveolar / lateral
    "N":  "nn", "L":  "nn",
    # rhotic
    "R":  "RR", "ER": "RR",
    # vowels
    "AA": "aa", "AE": "aa", "AH": "aa", "AO": "aa",
    "AW": "aa", "AY": "aa",
    "EH": "E",  "IH": "E",
    "IY": "I",  "EY": "I",
    "OW": "O",  "OY": "O", "UH": "O", "UW": "O",
    # glides
    "Y":  "I",  "W":  "O", "HH": "sil",
}


SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "en", "ja", "fr", "de",
)


# Per-engine language coverage. Rhubarb only does English well,
# Audio2Face does anything (it's audio-driven), Oculus does
# en + ja, Apple Speech does whatever iOS speaks.
_ENGINE_LANGS: dict[LipsyncEngine, frozenset[str]] = {
    LipsyncEngine.AUDIO2FACE: frozenset({"en", "ja", "fr", "de"}),
    LipsyncEngine.RHUBARB: frozenset({"en"}),
    LipsyncEngine.OCULUS: frozenset({"en", "ja"}),
    LipsyncEngine.APPLE_SPEECH: frozenset({
        "en", "ja", "fr", "de",
    }),
}


@dataclasses.dataclass(frozen=True)
class LipsyncTrack:
    track_id: str
    audio_file: str
    npc_id: str
    language: str
    engine: LipsyncEngine
    state: TrackState
    visemes: tuple[tuple[float, str], ...] = ()
    baked_curve: tuple[tuple[float, dict[str, float]], ...] = ()


# Per-NPC engine override. Hero NPCs get Audio2Face; ambient
# crowd uses Rhubarb. Falls through to engine_for() default.
_NPC_ENGINE_OVERRIDE: dict[str, LipsyncEngine] = {
    "curilla": LipsyncEngine.AUDIO2FACE,
    "volker": LipsyncEngine.AUDIO2FACE,
    "ayame": LipsyncEngine.AUDIO2FACE,
    "maat": LipsyncEngine.AUDIO2FACE,
    "trion": LipsyncEngine.AUDIO2FACE,
    "nanaa_mihgo": LipsyncEngine.AUDIO2FACE,
    "aldo": LipsyncEngine.AUDIO2FACE,
    "cid": LipsyncEngine.AUDIO2FACE,
}


def engine_for(
    npc_id: str, dialogue_importance: str = "ambient",
) -> LipsyncEngine:
    """Pick the lipsync engine for an NPC line.

    Hero NPCs always get Audio2Face. Otherwise importance:
        "hero"    → Audio2Face
        "named"   → Oculus
        "ambient" → Rhubarb (default)
    """
    if npc_id in _NPC_ENGINE_OVERRIDE:
        return _NPC_ENGINE_OVERRIDE[npc_id]
    if dialogue_importance == "hero":
        return LipsyncEngine.AUDIO2FACE
    if dialogue_importance == "named":
        return LipsyncEngine.OCULUS
    return LipsyncEngine.RHUBARB


@dataclasses.dataclass
class DialogueLipsyncSystem:
    """Mutable lipsync queue + analyzer state."""
    _tracks: dict[str, LipsyncTrack] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def queue_track(
        self, *, audio_file: str, npc_id: str,
        language: str = "en",
        dialogue_importance: str = "ambient",
    ) -> LipsyncTrack:
        if not audio_file:
            raise ValueError("audio_file required")
        if not npc_id:
            raise ValueError("npc_id required")
        if language not in SUPPORTED_LANGUAGES:
            # Unsupported language → fall back to Rhubarb,
            # which we treat as the safe-default engine.
            engine = LipsyncEngine.RHUBARB
            language = "en"
        else:
            engine = engine_for(npc_id, dialogue_importance)
            # If the chosen engine doesn't speak this lang,
            # demote to Rhubarb (which always speaks English).
            if language not in _ENGINE_LANGS[engine]:
                engine = LipsyncEngine.RHUBARB
                language = "en"
        tid = f"track_{self._next}"
        self._next += 1
        rec = LipsyncTrack(
            track_id=tid,
            audio_file=audio_file,
            npc_id=npc_id,
            language=language,
            engine=engine,
            state=TrackState.PENDING,
        )
        self._tracks[tid] = rec
        return rec

    def get_track(self, track_id: str) -> LipsyncTrack:
        if track_id not in self._tracks:
            raise KeyError(f"unknown track: {track_id}")
        return self._tracks[track_id]

    def analyze(
        self, track_id: str,
        phonemes: t.Sequence[tuple[float, str]],
    ) -> LipsyncTrack:
        """Convert a phoneme stream into a viseme stream.

        phonemes is a list of (timestamp_s, ARPAbet phoneme).
        Unknown phonemes default to "sil".
        """
        cur = self.get_track(track_id)
        if cur.state == TrackState.BAKED:
            raise RuntimeError(
                f"track {track_id} already baked",
            )
        visemes = tuple(
            (t_s, PHONEME_TO_VISEME.get(p.upper(), "sil"))
            for t_s, p in phonemes
        )
        new = dataclasses.replace(
            cur,
            state=TrackState.READY,
            visemes=visemes,
        )
        self._tracks[track_id] = new
        return new

    def get_visemes(
        self, track_id: str,
    ) -> tuple[tuple[float, str], ...]:
        rec = self.get_track(track_id)
        return rec.visemes

    def bake_curve(self, track_id: str) -> LipsyncTrack:
        """Convert visemes to a per-viseme weight curve.

        At each viseme keyframe, the named viseme is at
        weight 1.0 and every other viseme is 0. UE5's face
        control rig interpolates between frames.
        """
        cur = self.get_track(track_id)
        if cur.state != TrackState.READY:
            raise RuntimeError(
                f"track {track_id} not READY: {cur.state}",
            )
        baked: list[tuple[float, dict[str, float]]] = []
        for t_s, v in cur.visemes:
            weights = {k: 0.0 for k in VISEMES}
            weights[v] = 1.0
            baked.append((t_s, weights))
        new = dataclasses.replace(
            cur,
            state=TrackState.BAKED,
            baked_curve=tuple(baked),
        )
        self._tracks[track_id] = new
        return new

    def tracks(self) -> tuple[LipsyncTrack, ...]:
        return tuple(self._tracks.values())


def list_engines() -> tuple[str, ...]:
    return tuple(sorted(e.value for e in LipsyncEngine))


__all__ = [
    "LipsyncEngine", "TrackState",
    "LipsyncTrack",
    "PHONEME_TO_VISEME", "VISEMES",
    "SUPPORTED_LANGUAGES",
    "DialogueLipsyncSystem",
    "engine_for", "list_engines",
]
