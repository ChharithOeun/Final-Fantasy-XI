"""The voice generation pipeline.

Two backends are supported:
  - "higgs": Higgs Audio v2 via local HTTP API (production)
  - "stub":  records what would have been generated to a manifest
             but does not produce audio (dev / CI)

The stub backend is the default so the pipeline can run in
environments without GPU + model weights. Enable real synthesis
by passing `backend="higgs"` and pointing at a running Higgs
service.

Usage:

    from agent_orchestrator.loader import load_agent_yaml
    from voice_pipeline import VoicePipeline

    pipe = VoicePipeline(
        callouts_path="data/skillchain_callouts.yaml",
        output_dir="generated/voices",
        backend="stub",   # or "higgs"
    )
    profile = load_agent_yaml("agents/zaldon.yaml")
    job = pipe.generate_for_agent(profile)
    print(f"{job.lines_generated} / {job.lines_planned} lines")
    print(f"Output dir: {job.output_dir}")
"""
from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import time
import typing as t

import yaml


log = logging.getLogger("demoncore.voice")


@dataclasses.dataclass
class VoiceLine:
    """One line slated for synthesis."""
    line_id: str             # e.g. "level_3_close.light.0"
    text: str                # the spoken words
    category: str            # e.g. "level_3_close.light"
    mood: t.Optional[str]    # mood variant, if any
    output_path: pathlib.Path  # where the WAV will land


@dataclasses.dataclass
class VoiceJob:
    """Result of one generate_for_X call."""
    actor_id: str
    backend: str
    output_dir: pathlib.Path
    lines_planned: int
    lines_generated: int
    failed_lines: list[str]
    started_at: float
    finished_at: float
    manifest_path: pathlib.Path

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at


# ----------------------------------------------------------------------------
# Backends
# ----------------------------------------------------------------------------

class StubBackend:
    """Writes a JSON manifest entry per line; produces no audio."""

    def __init__(self):
        self.calls: list[dict] = []

    def synthesize(self, *, line: VoiceLine, voice_profile: str,
                   mood_tone: t.Optional[str] = None) -> bool:
        """Record what we would have synthesized. Always returns True."""
        self.calls.append({
            "line_id": line.line_id,
            "text": line.text,
            "voice_profile": voice_profile,
            "mood_tone": mood_tone,
            "output_path": str(line.output_path),
            "category": line.category,
        })
        # Write a tiny placeholder file so downstream code can verify
        # the path exists during pipeline tests.
        line.output_path.parent.mkdir(parents=True, exist_ok=True)
        line.output_path.write_text(
            f"# stub voice line\nline_id: {line.line_id}\ntext: {line.text}\n"
        )
        return True


class HiggsBackend:
    """Real Higgs Audio v2 backend.

    Requires the Higgs service running (typically on localhost:7860).
    Uses HTTP POST to the /tts endpoint. Conditioning prompt includes
    the voice reference audio path + optional mood tone hint.
    """

    def __init__(self, *, url: str = "http://localhost:7860",
                 timeout_seconds: float = 30.0):
        self.url = url
        self.timeout_seconds = timeout_seconds

    def synthesize(self, *, line: VoiceLine, voice_profile: str,
                   mood_tone: t.Optional[str] = None) -> bool:
        try:
            import httpx
        except ImportError:
            log.error("httpx not installed; cannot use HiggsBackend")
            return False

        try:
            payload = {
                "text": line.text,
                "reference_audio_path": voice_profile,
                "conditioning_prompt": _compose_conditioning_prompt(
                    mood_tone, line.category
                ),
                "output_format": "wav",
            }
            response = httpx.post(
                f"{self.url}/tts", json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                log.warning("Higgs returned %d for %s: %s",
                            response.status_code, line.line_id,
                            response.text[:200])
                return False

            line.output_path.parent.mkdir(parents=True, exist_ok=True)
            line.output_path.write_bytes(response.content)
            return True

        except Exception as e:
            log.warning("Higgs request failed for %s: %s", line.line_id, e)
            return False


def _compose_conditioning_prompt(mood_tone: t.Optional[str],
                                  category: str) -> str:
    """Build the Higgs conditioning prompt.

    Per AUDIBLE_CALLOUTS.md, mood-aware tone matters. We compose a
    short prompt that biases the synthesis toward the right delivery.
    """
    base_prompts = {
        "content":      "warm, confident, even tone",
        "gruff":        "clipped, lower register, terse",
        "furious":      "louder, sharper, faster",
        "fearful":      "higher pitch, shaky, callouts shorter or unfinished",
        "alert":        "crisp, professional, military",
        "drunk":        "slurred, drawling",
        "mischievous":  "playful, slight upward inflection",
        "contemplative":"slower, lower energy",
        "weary":        "slower, lower energy, breathy",
        "fierce":       "sharp, decisive, controlled volume",
    }
    parts = []
    if mood_tone in base_prompts:
        parts.append(base_prompts[mood_tone])

    # Category hints — combat callouts are sharper than schedule barks
    if category.startswith("level_3_close"):
        parts.append("triumphant, urgent")
    elif category.startswith("magic_burst"):
        parts.append("crisp, clearly enunciated")
    elif category.startswith("intervention_"):
        parts.append("sharp, focused")
    elif category.startswith("chain_fail"):
        parts.append("frustrated, brief")

    return ", ".join(parts) if parts else "natural delivery"


# ----------------------------------------------------------------------------
# The pipeline
# ----------------------------------------------------------------------------

class VoicePipeline:
    """Walks the callout library, synthesizes lines per actor."""

    def __init__(self, *,
                 callouts_path: str | pathlib.Path,
                 output_dir: str | pathlib.Path,
                 backend: str = "stub",
                 backend_kwargs: t.Optional[dict] = None):
        self.callouts_path = pathlib.Path(callouts_path)
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if backend == "higgs":
            self.backend = HiggsBackend(**(backend_kwargs or {}))
        elif backend == "stub":
            self.backend = StubBackend()
        else:
            raise ValueError(f"unknown backend: {backend!r}")

        self.backend_name = backend
        self._callouts = self._load_callouts()

    def _load_callouts(self) -> dict:
        if not self.callouts_path.is_file():
            raise FileNotFoundError(self.callouts_path)
        with self.callouts_path.open() as f:
            return yaml.safe_load(f)

    # ------------------------------------------------------------------
    # Line enumeration — extracts (category, mood, text) tuples from
    # the callouts YAML
    # ------------------------------------------------------------------

    def _enumerate_lines(self) -> list[tuple[str, t.Optional[str], str]]:
        """Walk the callouts data and produce a flat list of all lines.

        Returns:
            List of (category, mood, text) tuples, where mood is None
            for the "default" variant.
        """
        lines: list[tuple[str, t.Optional[str], str]] = []
        for category, content in self._callouts.items():
            if category.startswith("_"):
                continue
            if not isinstance(content, dict):
                continue
            # Two shapes:
            # (1) { mood_label: [lines] }              # flat moods
            # (2) { sub_key: { mood_label: [lines] } } # nested
            for k, v in content.items():
                if k == "notes":  # author notes; skip
                    continue
                if isinstance(v, list):
                    # Shape 1: e.g. chain_open.default = [...]
                    mood = None if k == "default" else k.replace("mood_", "")
                    cat = category
                    for line_text in v:
                        lines.append((cat, mood, line_text))
                elif isinstance(v, dict):
                    # Shape 2: e.g. level_1_close.liquefaction.default = [...]
                    sub_cat = f"{category}.{k}"
                    for inner_k, inner_v in v.items():
                        if not isinstance(inner_v, list):
                            continue
                        mood = (None if inner_k == "default"
                                else inner_k.replace("mood_", ""))
                        for line_text in inner_v:
                            lines.append((sub_cat, mood, line_text))
        return lines

    # ------------------------------------------------------------------
    # Public synthesis API
    # ------------------------------------------------------------------

    def generate_for_agent(self, profile) -> VoiceJob:
        """Generate the full voice library for one Tier-2 / Tier-3 agent."""
        if profile.voice_profile is None:
            raise ValueError(
                f"agent {profile.id} has no voice_profile; cannot synthesize"
            )
        return self._generate(
            actor_id=profile.id,
            voice_profile=profile.voice_profile,
        )

    def generate_for_mob_class(self,
                                mob_class_yaml_path: str | pathlib.Path) -> VoiceJob:
        """Generate a stock voice library for one mob class."""
        mob_path = pathlib.Path(mob_class_yaml_path)
        with mob_path.open() as f:
            data = yaml.safe_load(f)
        return self._generate(
            actor_id=data["mob_class"],
            voice_profile=data.get("voice_profile_stock") or "",
        )

    def generate_for_player(self,
                             player_id: str,
                             reference_wav: str) -> VoiceJob:
        """Generate the full voice library for a new player from their
        character-creation reference recording."""
        return self._generate(
            actor_id=player_id,
            voice_profile=reference_wav,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _generate(self, *, actor_id: str, voice_profile: str) -> VoiceJob:
        all_lines = self._enumerate_lines()

        actor_dir = self.output_dir / actor_id
        actor_dir.mkdir(parents=True, exist_ok=True)

        started = time.time()
        generated = 0
        failed: list[str] = []
        manifest: list[dict] = []

        for i, (category, mood, text) in enumerate(all_lines):
            line_id = f"{category}.{mood or 'default'}.{i}"
            output_path = actor_dir / f"{line_id}.wav"
            line = VoiceLine(
                line_id=line_id,
                text=text,
                category=category,
                mood=mood,
                output_path=output_path,
            )
            ok = self.backend.synthesize(
                line=line,
                voice_profile=voice_profile,
                mood_tone=mood,
            )
            if ok:
                generated += 1
                manifest.append({
                    "line_id": line_id,
                    "text": text,
                    "mood": mood,
                    "category": category,
                    "output_path": str(output_path),
                })
            else:
                failed.append(line_id)

        finished = time.time()
        manifest_path = actor_dir / "_manifest.json"
        manifest_path.write_text(json.dumps({
            "actor_id": actor_id,
            "voice_profile": voice_profile,
            "backend": self.backend_name,
            "lines_generated": generated,
            "lines_failed": len(failed),
            "started_at": started,
            "finished_at": finished,
            "lines": manifest,
        }, indent=2))

        log.info("voice job for %s: %d/%d generated (%s)",
                 actor_id, generated, len(all_lines), self.backend_name)

        return VoiceJob(
            actor_id=actor_id,
            backend=self.backend_name,
            output_dir=actor_dir,
            lines_planned=len(all_lines),
            lines_generated=generated,
            failed_lines=failed,
            started_at=started,
            finished_at=finished,
            manifest_path=manifest_path,
        )
