"""Remix pipeline — pull canonical retail FFXI music + restyle.

Extends the original generation pipeline (pipeline.py) with stem
separation + style transfer for taking the retail FFXI music
library and remixing it per Demoncore's mood/atmosphere palette.

Per MUSIC_REMIX_PIPELINE.md.

Two backends mirror the parent pipeline:
- `ace_step_remix`: real ACE-Step + Demucs HTTP service
- `stub`: writes JSON manifest entries; no audio synthesis

Usage:

    from music_pipeline.remix import RemixPipeline

    pipe = RemixPipeline(
        retail_extracted_dir="extracted/music_retail",
        output_dir="generated/music_remix",
        style_config_path="data/music_remix_targets.json",
        backend="stub",
    )
    job = pipe.remix_track(
        track_id="bgm_bastok_markets",
        mood_variant="daytime",
    )
"""
from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import time
import typing as t


log = logging.getLogger("demoncore.music.remix")


@dataclasses.dataclass
class RemixJob:
    track_id: str
    mood_variant: str
    backend: str
    source_path: pathlib.Path
    output_path: pathlib.Path
    style_prompt: str
    success: bool
    started_at: float
    finished_at: float
    error: t.Optional[str] = None

    @property
    def wall_seconds(self) -> float:
        return self.finished_at - self.started_at


class StubRemixBackend:
    """Records what would have happened. No audio."""

    def __init__(self):
        self.calls: list[dict] = []

    def stem_separate(self, source: pathlib.Path,
                      stems_dir: pathlib.Path) -> bool:
        stems_dir.mkdir(parents=True, exist_ok=True)
        # Emit 4 placeholder stem files to make downstream tests realistic
        for stem in ("vocals", "bass", "drums", "other"):
            (stems_dir / f"{stem}.wav").write_text(
                f"# stub stem\nsource: {source.name}\nstem: {stem}\n"
            )
        self.calls.append({"op": "stem_separate", "source": str(source)})
        return True

    def apply_style(self, *, stems_dir: pathlib.Path,
                    style_prompt: str, mood_tag: str,
                    duration_sec: float,
                    output_path: pathlib.Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"# stub remix output\n"
            f"source_stems: {stems_dir}\n"
            f"style: {style_prompt}\n"
            f"mood: {mood_tag}\n"
            f"duration: {duration_sec}s\n"
        )
        self.calls.append({
            "op": "apply_style",
            "stems": str(stems_dir),
            "prompt": style_prompt,
            "mood": mood_tag,
            "output": str(output_path),
        })
        return True


class AceStepRemixBackend:
    """Real Demucs + ACE-Step backend.

    Expects two HTTP services:
      - Demucs at localhost:7867 with /separate endpoint
      - ACE-Step at localhost:7866 with /remix endpoint
    """

    def __init__(self, *,
                 demucs_url: str = "http://localhost:7867",
                 ace_url: str = "http://localhost:7866",
                 timeout_seconds: float = 300.0):
        self.demucs_url = demucs_url
        self.ace_url = ace_url
        self.timeout_seconds = timeout_seconds

    def stem_separate(self, source: pathlib.Path,
                      stems_dir: pathlib.Path) -> bool:
        try:
            import httpx
        except ImportError:
            log.error("httpx not installed; cannot use AceStepRemixBackend")
            return False

        try:
            with source.open("rb") as f:
                response = httpx.post(
                    f"{self.demucs_url}/separate",
                    files={"audio": f},
                    timeout=self.timeout_seconds,
                )
            if response.status_code != 200:
                log.warning("Demucs returned %d for %s",
                            response.status_code, source.name)
                return False

            stems_dir.mkdir(parents=True, exist_ok=True)
            data = response.json()
            for stem_name, stem_b64 in data.get("stems", {}).items():
                import base64
                (stems_dir / f"{stem_name}.wav").write_bytes(
                    base64.b64decode(stem_b64)
                )
            return True
        except Exception as e:
            log.warning("Demucs request failed: %s", e)
            return False

    def apply_style(self, *, stems_dir: pathlib.Path,
                    style_prompt: str, mood_tag: str,
                    duration_sec: float,
                    output_path: pathlib.Path) -> bool:
        try:
            import httpx
        except ImportError:
            return False

        try:
            payload = {
                "stems_dir": str(stems_dir),
                "style_prompt": style_prompt,
                "mood_tag": mood_tag,
                "duration_seconds": duration_sec,
            }
            response = httpx.post(
                f"{self.ace_url}/remix",
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                log.warning("ACE-Step remix returned %d", response.status_code)
                return False
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True
        except Exception as e:
            log.warning("ACE-Step remix failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# RemixPipeline
# ---------------------------------------------------------------------------

# Default mood-variant prompt templates. Filled with style_config values
# at runtime. Each track gets remixed once per (track, mood_variant) pair.
MOOD_VARIANT_TEMPLATES: dict[str, str] = {
    "daytime": (
        "Re-orchestrate this melody as: {primary_genre} hybrid, "
        "{lead_instruments}, {drum_kit}, "
        "warm + bright + active, full mid-range, looping 3-min "
        "Bastok-daytime feel. Maintain the original melodic motif throughout."
    ),
    "nighttime": (
        "Re-orchestrate this melody as: {primary_genre} hybrid, "
        "subdued, {bass_synth} dominant, slower tempo, less mid-range, "
        "more reverb tail, contemplative night ambient feel."
    ),
    "siege": (
        "Re-orchestrate this melody as: {primary_genre} hybrid, "
        "fast tempo, drums up, brass biting, sub-bass driving, "
        "tense building anxiety, anxious-but-not-panicked. "
        "Maintain the original melodic motif but in minor key."
    ),
    "aftermath": (
        "Re-orchestrate this melody as: {secondary_genre} only "
        "(strip the {primary_genre} elements), solo strings + "
        "lead instrument, slow, reverent, quiet dynamics, "
        "post-battle introspection feel."
    ),
    "battle": (
        "Re-orchestrate this melody as: {primary_genre} hybrid, "
        "fast tempo, percussion-forward, sustained tension, "
        "arena/boss-fight intensity. Drop the original melodic motif "
        "in fragments rather than complete."
    ),
}


class RemixPipeline:
    def __init__(self, *,
                 retail_extracted_dir: str | pathlib.Path,
                 output_dir: str | pathlib.Path,
                 style_config: t.Optional[dict] = None,
                 backend: str = "stub",
                 backend_kwargs: t.Optional[dict] = None):
        self.retail_extracted_dir = pathlib.Path(retail_extracted_dir)
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Default style config (placeholder until user provides YouTube reference)
        self.style_config = style_config or {
            "primary_genre": "modern_orchestral",
            "secondary_genre": "fantasy_orchestral",
            "lead_instruments": "brass + strings",
            "drum_kit": "modern_film_drums",
            "bass_synth": "low_orchestral_bass",
            "production_tags": ["wide_stereo", "modern_dynamics"],
        }

        if backend == "ace_step_remix":
            self.backend = AceStepRemixBackend(**(backend_kwargs or {}))
        elif backend == "stub":
            self.backend = StubRemixBackend()
        else:
            raise ValueError(f"unknown remix backend: {backend!r}")
        self.backend_name = backend

    def _compose_style_prompt(self, mood_variant: str) -> str:
        template = MOOD_VARIANT_TEMPLATES.get(
            mood_variant,
            "Re-orchestrate this melody as: {primary_genre} hybrid, "
            "fantasy game music, looping. Maintain the original motif."
        )
        return template.format(**self.style_config)

    def remix_track(self, *,
                    track_id: str,
                    mood_variant: str,
                    duration_sec: float = 180.0) -> RemixJob:
        """Stem-separate then style-transfer one retail track."""
        source_path = self.retail_extracted_dir / f"{track_id}.wav"
        stems_dir = self.output_dir / "stems" / track_id
        output_path = self.output_dir / "remix" / f"{track_id}_{mood_variant}.wav"

        started = time.time()
        style_prompt = self._compose_style_prompt(mood_variant)

        if not source_path.is_file():
            return RemixJob(
                track_id=track_id, mood_variant=mood_variant,
                backend=self.backend_name, source_path=source_path,
                output_path=output_path, style_prompt=style_prompt,
                success=False, started_at=started,
                finished_at=time.time(),
                error=f"source track not found: {source_path}",
            )

        # Step 1: stem separation (cached if already done)
        if not (stems_dir / "other.wav").is_file():
            ok_stem = self.backend.stem_separate(source_path, stems_dir)
            if not ok_stem:
                return RemixJob(
                    track_id=track_id, mood_variant=mood_variant,
                    backend=self.backend_name, source_path=source_path,
                    output_path=output_path, style_prompt=style_prompt,
                    success=False, started_at=started,
                    finished_at=time.time(),
                    error="stem separation failed",
                )

        # Step 2: style transfer
        ok_style = self.backend.apply_style(
            stems_dir=stems_dir,
            style_prompt=style_prompt,
            mood_tag=mood_variant,
            duration_sec=duration_sec,
            output_path=output_path,
        )

        finished = time.time()
        return RemixJob(
            track_id=track_id, mood_variant=mood_variant,
            backend=self.backend_name, source_path=source_path,
            output_path=output_path, style_prompt=style_prompt,
            success=ok_style, started_at=started, finished_at=finished,
            error=None if ok_style else "style transfer failed",
        )

    def remix_all_variants(self, track_id: str,
                           variants: t.Optional[list[str]] = None,
                           duration_sec: float = 180.0) -> list[RemixJob]:
        """Generate every requested mood variant for one track."""
        variants = variants or ["daytime", "nighttime", "siege", "aftermath"]
        return [self.remix_track(track_id=track_id, mood_variant=v,
                                  duration_sec=duration_sec)
                for v in variants]

    def write_manifest(self, jobs: list[RemixJob]) -> pathlib.Path:
        """Write a manifest the LSB runtime can read for variant selection."""
        manifest_path = self.output_dir / "manifest.json"
        manifest = {
            "remix_style_version": self.style_config.get(
                "primary_genre", "unknown"
            ) + "_v1",
            "tracks": {},
        }
        for j in jobs:
            track_entry = manifest["tracks"].setdefault(j.track_id, {
                "variants": [],
            })
            track_entry["variants"].append({
                "mood": j.mood_variant,
                "path": str(j.output_path),
                "success": j.success,
            })
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest_path
