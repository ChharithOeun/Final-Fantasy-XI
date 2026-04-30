"""Music generation via ACE-Step v1.5 (or stub backend for CI).

Three output classes:

    BGM      — long-form zone music (3-5 min loop) seeded from
               atmosphere preset (warm orange Bastok sunset →
               brass-heavy industrial march; cool cyan Windurst night
               → woodwind ambient pad)
    BOSS     — boss-specific themes seeded from the agent's mood_axes
               (Maat → noble brass; Shadow Lord → low strings + chant)
    STINGER  — short 5-15 second cues for skillchain detonations,
               magic burst landings, intervention saves, phase
               transitions, defeat moments

Generation is slow (3-10 minutes per minute of audio on a single GPU)
so production pre-generates everything during a build phase. At
runtime the game just plays back files.

Usage:

    from music_pipeline import MusicPipeline

    pipe = MusicPipeline(
        prompt_lib_path="data/music_prompts.yaml",
        output_dir="generated/music",
        backend="stub",   # or "ace_step"
    )
    job = pipe.generate_zone_bgm("bastok_markets", {
        "mood": "industrial_warmth",
        "tempo": "medium",
        "instrumentation": "brass + steel-percussion + low strings",
    })
"""
from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import time
import typing as t


log = logging.getLogger("demoncore.music")


@dataclasses.dataclass
class MusicJob:
    """Result of one generate_for_X call."""
    asset_id: str
    asset_kind: str           # "bgm" | "boss" | "stinger"
    backend: str
    output_path: pathlib.Path
    prompt_used: str
    duration_seconds_target: float
    started_at: float
    finished_at: float
    success: bool
    error: t.Optional[str] = None

    @property
    def wall_seconds(self) -> float:
        return self.finished_at - self.started_at


class StubBackend:
    """Records what would have been generated. Writes a placeholder file."""

    def __init__(self):
        self.calls: list[dict] = []

    def synthesize(self, *, prompt: str, output_path: pathlib.Path,
                    duration_seconds: float) -> bool:
        self.calls.append({
            "prompt": prompt,
            "output_path": str(output_path),
            "duration_seconds": duration_seconds,
        })
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"# stub music asset\n"
            f"prompt: {prompt}\n"
            f"duration: {duration_seconds}s\n"
        )
        return True


class AceStepBackend:
    """Real ACE-Step backend via local HTTP service.

    Expects an ACE-Step service at the given URL with a /generate
    endpoint that accepts {prompt, duration_seconds} and returns
    audio bytes (wav or mp3).
    """

    def __init__(self, *, url: str = "http://localhost:7866",
                 timeout_seconds: float = 600.0):
        self.url = url
        self.timeout_seconds = timeout_seconds

    def synthesize(self, *, prompt: str, output_path: pathlib.Path,
                    duration_seconds: float) -> bool:
        try:
            import httpx
        except ImportError:
            log.error("httpx not installed; cannot use AceStepBackend")
            return False

        try:
            payload = {
                "prompt": prompt,
                "duration_seconds": duration_seconds,
                "output_format": "wav",
            }
            response = httpx.post(
                f"{self.url}/generate", json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                log.warning("ACE-Step returned %d: %s",
                            response.status_code, response.text[:200])
                return False
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True
        except Exception as e:
            log.warning("ACE-Step request failed: %s", e)
            return False


def _compose_prompt(asset_kind: str, params: dict) -> str:
    """Build a music-generation prompt from structured parameters.

    The ACE-Step model takes natural-language prompts. We compose them
    to be specific enough for consistent output.
    """
    if asset_kind == "bgm":
        # Zone BGM
        mood = params.get("mood", "neutral")
        tempo = params.get("tempo", "medium")
        instrumentation = params.get("instrumentation", "orchestral")
        location = params.get("location", "")
        prompt = f"{mood} fantasy orchestral score, {tempo} tempo, " \
                 f"featuring {instrumentation}"
        if location:
            prompt += f", evoking {location}"
        prompt += ", looping, ambient layer"
        return prompt

    elif asset_kind == "boss":
        # Boss theme
        boss_personality = params.get("personality", "")
        moods = params.get("mood_axes", [])
        intensity = params.get("intensity", "high")
        prompt = f"{intensity}-intensity boss battle theme"
        if boss_personality:
            prompt += f" for a character described as {boss_personality}"
        if moods:
            prompt += f", emotional palette: {', '.join(moods)}"
        prompt += ", building tension, fantasy orchestral with brass and percussion"
        return prompt

    elif asset_kind == "stinger":
        # Short cue
        event = params.get("event_kind", "generic")
        duration = params.get("duration_seconds", 8.0)
        prompts = {
            "skillchain_close":   "triumphant chord stinger, 3 seconds, brass + cymbal",
            "magic_burst_landed": "harmonic cascade, 4 seconds, ascending strings",
            "intervention_save":  "redemptive horn fanfare, 5 seconds, gold brass",
            "boss_phase_transition":"dark dissonance shift, 6 seconds, low strings + drums",
            "boss_defeat":        "hymn-like resolution, 8 seconds, full ensemble",
            "party_wipe":         "descending dirge, 6 seconds, low brass + tolling bell",
            "level_up":           "single bright bell + ascending arpeggio, 3 seconds",
            "first_skillchain":   "warm major chord, sustained 4 seconds, harp + flute",
        }
        return prompts.get(event, f"{duration:.0f}-second fantasy game stinger")

    else:
        return params.get("prompt", "fantasy orchestral cue")


# ----------------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------------

class MusicPipeline:

    def __init__(self, *,
                 output_dir: str | pathlib.Path,
                 backend: str = "stub",
                 backend_kwargs: t.Optional[dict] = None):
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if backend == "ace_step":
            self.backend = AceStepBackend(**(backend_kwargs or {}))
        elif backend == "stub":
            self.backend = StubBackend()
        else:
            raise ValueError(f"unknown backend: {backend!r}")
        self.backend_name = backend

    def _generate(self, *, asset_id: str, asset_kind: str,
                   prompt: str, duration_seconds: float) -> MusicJob:
        out_dir = self.output_dir / asset_kind
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{asset_id}.wav"

        started = time.time()
        success = self.backend.synthesize(
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
        )
        finished = time.time()

        return MusicJob(
            asset_id=asset_id,
            asset_kind=asset_kind,
            backend=self.backend_name,
            output_path=output_path,
            prompt_used=prompt,
            duration_seconds_target=duration_seconds,
            started_at=started,
            finished_at=finished,
            success=success,
            error=None if success else "synth failed",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_zone_bgm(self, zone_slug: str,
                            atmosphere: dict) -> MusicJob:
        prompt = _compose_prompt("bgm", {**atmosphere,
                                          "location": zone_slug})
        return self._generate(
            asset_id=f"bgm_{zone_slug}",
            asset_kind="bgm",
            prompt=prompt,
            duration_seconds=180.0,    # 3-min loop
        )

    def generate_boss_theme(self, boss_id: str, *,
                             personality: str = "",
                             mood_axes: t.Optional[list] = None,
                             intensity: str = "high") -> MusicJob:
        prompt = _compose_prompt("boss", {
            "personality": personality,
            "mood_axes": mood_axes or [],
            "intensity": intensity,
        })
        return self._generate(
            asset_id=f"boss_{boss_id}",
            asset_kind="boss",
            prompt=prompt,
            duration_seconds=120.0,
        )

    def generate_stinger(self, event_kind: str,
                          duration_seconds: float = 6.0) -> MusicJob:
        prompt = _compose_prompt("stinger", {
            "event_kind": event_kind,
            "duration_seconds": duration_seconds,
        })
        return self._generate(
            asset_id=f"stinger_{event_kind}",
            asset_kind="stinger",
            prompt=prompt,
            duration_seconds=duration_seconds,
        )

    def generate_canonical_stinger_set(self) -> list[MusicJob]:
        """Generate the standard 8-stinger library used everywhere."""
        events = [
            "skillchain_close",
            "magic_burst_landed",
            "intervention_save",
            "boss_phase_transition",
            "boss_defeat",
            "party_wipe",
            "level_up",
            "first_skillchain",
        ]
        return [self.generate_stinger(e) for e in events]
