"""HD remaster + custom authoring + variation generation for SFX.

Per SFX_PIPELINE.md. Two backends:
- "audiosr": real AudioSR HTTP service for super-resolution
- "stub":    CI-friendly; writes JSON manifest + placeholder files

The pipeline is INTENTIONALLY conservative for canonical assets.
The user's design rule: spell + WS sounds keep their canonical
character. We touch sample rate, bit depth, and surround
positioning metadata. We do NOT touch envelope, timbre, or
synthesis.
"""
from __future__ import annotations

import dataclasses
import enum
import json
import logging
import pathlib
import time
import typing as t


log = logging.getLogger("demoncore.sfx")


class SFXClass(str, enum.Enum):
    """Per SFX_PIPELINE.md."""
    CANONICAL_PRESERVED = "canonical_preserved"   # Class 1
    CANONICAL_REMASTERED = "canonical_remastered" # Class 2
    NEW_MECHANIC = "new_mechanic"                  # Class 3
    PROCEDURAL_VARIATION = "procedural_variation"  # Class 4


@dataclasses.dataclass
class SFXJob:
    asset_id: str
    sfx_class: SFXClass
    backend: str
    source_path: t.Optional[pathlib.Path]
    output_path: pathlib.Path
    metadata: dict
    success: bool
    started_at: float
    finished_at: float
    error: t.Optional[str] = None

    @property
    def wall_seconds(self) -> float:
        return self.finished_at - self.started_at


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class StubBackend:
    """Writes a placeholder file + records the operation."""

    def __init__(self):
        self.calls: list[dict] = []

    def upscale(self, source: pathlib.Path, output: pathlib.Path,
                target_sample_rate: int = 48000) -> bool:
        self.calls.append({
            "op": "upscale",
            "source": str(source),
            "output": str(output),
            "target_sample_rate": target_sample_rate,
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            f"# stub upscaled SFX\n"
            f"source: {source.name}\n"
            f"target_sr: {target_sample_rate}\n"
        )
        return True

    def author_new(self, prompt: str, output: pathlib.Path,
                   duration_sec: float) -> bool:
        self.calls.append({
            "op": "author_new",
            "prompt": prompt,
            "duration_sec": duration_sec,
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            f"# stub authored SFX\n"
            f"prompt: {prompt}\n"
            f"duration: {duration_sec}s\n"
        )
        return True

    def vary(self, base: pathlib.Path, output: pathlib.Path,
             pitch_cents: float = 0, time_stretch_pct: float = 0) -> bool:
        self.calls.append({
            "op": "vary",
            "base": str(base),
            "pitch_cents": pitch_cents,
            "time_stretch_pct": time_stretch_pct,
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            f"# stub variation\n"
            f"base: {base.name}\n"
            f"pitch_cents: {pitch_cents}\n"
            f"time_stretch_pct: {time_stretch_pct}\n"
        )
        return True


class AudioSRBackend:
    """Real AudioSR backend via local HTTP service.

    Expects:
      - AudioSR at localhost:7868 with /upscale endpoint (super-resolution)
      - Optional audio-gen model (Stable Audio etc) at /author for new sounds
    """

    def __init__(self, *,
                 audiosr_url: str = "http://localhost:7868",
                 author_url: str = "http://localhost:7869",
                 timeout_seconds: float = 60.0):
        self.audiosr_url = audiosr_url
        self.author_url = author_url
        self.timeout_seconds = timeout_seconds

    def upscale(self, source: pathlib.Path, output: pathlib.Path,
                target_sample_rate: int = 48000) -> bool:
        try:
            import httpx
        except ImportError:
            return False
        try:
            with source.open("rb") as f:
                response = httpx.post(
                    f"{self.audiosr_url}/upscale",
                    files={"audio": f},
                    data={"target_sample_rate": str(target_sample_rate)},
                    timeout=self.timeout_seconds,
                )
            if response.status_code != 200:
                log.warning("AudioSR returned %d for %s",
                            response.status_code, source.name)
                return False
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(response.content)
            return True
        except Exception as e:
            log.warning("AudioSR request failed: %s", e)
            return False

    def author_new(self, prompt: str, output: pathlib.Path,
                   duration_sec: float) -> bool:
        try:
            import httpx
        except ImportError:
            return False
        try:
            response = httpx.post(
                f"{self.author_url}/author",
                json={"prompt": prompt, "duration_seconds": duration_sec},
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                return False
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(response.content)
            return True
        except Exception as e:
            log.warning("author request failed: %s", e)
            return False

    def vary(self, base: pathlib.Path, output: pathlib.Path,
             pitch_cents: float = 0, time_stretch_pct: float = 0) -> bool:
        # Variations don't need an external service — librosa locally.
        try:
            import librosa
            import soundfile as sf
            import numpy as np
        except ImportError:
            log.warning("librosa not installed; cannot generate variations")
            return False
        try:
            y, sr = librosa.load(str(base), sr=None)
            if pitch_cents:
                y = librosa.effects.pitch_shift(
                    y, sr=sr, n_steps=pitch_cents / 100.0,
                )
            if time_stretch_pct:
                rate = 1.0 + (time_stretch_pct / 100.0)
                y = librosa.effects.time_stretch(y, rate=rate)
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output), y, sr)
            return True
        except Exception as e:
            log.warning("variation failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

# Per-class spatializer config defaults. Matches the metadata spec
# in SFX_PIPELINE.md.
DEFAULT_SPATIALIZER_CONFIG: dict[SFXClass, dict] = {
    SFXClass.CANONICAL_PRESERVED: {
        "type": "3d_spatialized",
        "early_reflections": True,
        "reverb_send": "ambient_per_zone",
        "mood_aware": False,
    },
    SFXClass.CANONICAL_REMASTERED: {
        "type": "3d_spatialized",
        "early_reflections": True,
        "reverb_send": "ambient_per_zone",
        "mood_aware": True,    # ambient sounds DO modulate with actor mood
    },
    SFXClass.NEW_MECHANIC: {
        "type": "3d_spatialized",
        "early_reflections": True,
        "reverb_send": "mechanic_specific",
        "mood_aware": True,
    },
    SFXClass.PROCEDURAL_VARIATION: {
        "type": "3d_spatialized",
        "early_reflections": True,
        "reverb_send": "ambient_per_zone",
        "mood_aware": True,    # footstep weight modulates with mood
        "auto_select_variation": True,
    },
}


class SFXPipeline:
    def __init__(self, *,
                 retail_extracted_dir: t.Optional[str | pathlib.Path] = None,
                 output_dir: str | pathlib.Path,
                 backend: str = "stub",
                 backend_kwargs: t.Optional[dict] = None):
        self.retail_extracted_dir = (
            pathlib.Path(retail_extracted_dir) if retail_extracted_dir
            else None
        )
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if backend == "audiosr":
            self.backend = AudioSRBackend(**(backend_kwargs or {}))
        elif backend == "stub":
            self.backend = StubBackend()
        else:
            raise ValueError(f"unknown sfx backend: {backend!r}")
        self.backend_name = backend

    # ------------------------------------------------------------------
    # Class 1 + 2: canonical upscaling
    # ------------------------------------------------------------------

    def upscale_canonical(self, *,
                           asset_id: str,
                           sfx_class: SFXClass = SFXClass.CANONICAL_PRESERVED,
                           target_sample_rate: int = 48000,
                           extra_metadata: t.Optional[dict] = None) -> SFXJob:
        """Class 1/2: take a retail SFX and HD-upscale it.

        For Class 1 (preserved) we do minimum-touch upscale.
        For Class 2 (remastered) we do upscale + tonal balance.

        Source path is auto-resolved from retail_extracted_dir +
        asset_id (e.g. "spells/fire" -> retail/spells/fire.wav).
        """
        if self.retail_extracted_dir is None:
            raise ValueError("retail_extracted_dir not set; cannot upscale")

        source = self.retail_extracted_dir / f"{asset_id}.wav"
        sub_dir = "preserved" if sfx_class == SFXClass.CANONICAL_PRESERVED \
                  else "remastered"
        output = self.output_dir / sub_dir / f"{asset_id}.wav"

        started = time.time()
        if not source.is_file():
            return SFXJob(
                asset_id=asset_id, sfx_class=sfx_class,
                backend=self.backend_name,
                source_path=source, output_path=output,
                metadata={}, success=False,
                started_at=started, finished_at=time.time(),
                error=f"source not found: {source}",
            )

        success = self.backend.upscale(source, output, target_sample_rate)
        finished = time.time()

        spat_config = dict(DEFAULT_SPATIALIZER_CONFIG[sfx_class])
        if extra_metadata:
            spat_config.update(extra_metadata)

        metadata = {
            "asset_id": asset_id,
            "class": sfx_class.value,
            "source_format": "stereo_48khz_24bit"
                              if target_sample_rate == 48000
                              else f"native_{target_sample_rate}",
            "spatializer": spat_config,
        }

        return SFXJob(
            asset_id=asset_id, sfx_class=sfx_class,
            backend=self.backend_name,
            source_path=source, output_path=output,
            metadata=metadata, success=success,
            started_at=started, finished_at=finished,
            error=None if success else "upscale failed",
        )

    # ------------------------------------------------------------------
    # Class 3: new mechanic sounds
    # ------------------------------------------------------------------

    def author_new_mechanic_sound(self, *,
                                   mechanic_id: str,
                                   prompt: str,
                                   duration_sec: float = 2.0) -> SFXJob:
        """Class 3: generate a new SFX from a text prompt.

        Used for sounds that don't exist in retail FFXI (NIN
        chakra flow, intervention MB shimmer, dual-cast bell,
        master-synthesis crit-repair particle layer, etc).
        """
        output = self.output_dir / "authored" / f"{mechanic_id}.wav"
        started = time.time()
        success = self.backend.author_new(prompt, output, duration_sec)
        finished = time.time()

        spat_config = dict(DEFAULT_SPATIALIZER_CONFIG[SFXClass.NEW_MECHANIC])
        metadata = {
            "asset_id": mechanic_id,
            "class": SFXClass.NEW_MECHANIC.value,
            "authored_prompt": prompt,
            "duration_seconds": duration_sec,
            "spatializer": spat_config,
        }

        return SFXJob(
            asset_id=mechanic_id, sfx_class=SFXClass.NEW_MECHANIC,
            backend=self.backend_name,
            source_path=None, output_path=output,
            metadata=metadata, success=success,
            started_at=started, finished_at=finished,
            error=None if success else "author failed",
        )

    # ------------------------------------------------------------------
    # Class 4: procedural variation
    # ------------------------------------------------------------------

    def generate_variation_set(self, *,
                                base_sfx_id: str,
                                base_path: pathlib.Path,
                                num_variations: int = 5,
                                pitch_range_cents: float = 100,
                                time_stretch_range_pct: float = 5) -> list[SFXJob]:
        """Class 4: produce N variations of one base sample.

        Used for footsteps, hit sounds, mob roars where consecutive
        plays should sound different. Variations are produced by
        small pitch shifts + time stretches, not new synthesis.
        """
        import random
        rng = random.Random(hash(base_sfx_id) % (2**32))
        jobs: list[SFXJob] = []
        for i in range(num_variations):
            pitch_cents = rng.uniform(-pitch_range_cents, pitch_range_cents)
            time_stretch_pct = rng.uniform(-time_stretch_range_pct,
                                            time_stretch_range_pct)
            output = self.output_dir / "variations" / \
                     f"{base_sfx_id}_var{i}.wav"
            started = time.time()
            success = self.backend.vary(
                base_path, output,
                pitch_cents=pitch_cents,
                time_stretch_pct=time_stretch_pct,
            )
            finished = time.time()
            metadata = {
                "asset_id": f"{base_sfx_id}_var{i}",
                "class": SFXClass.PROCEDURAL_VARIATION.value,
                "base_asset_id": base_sfx_id,
                "pitch_cents": round(pitch_cents, 2),
                "time_stretch_pct": round(time_stretch_pct, 2),
                "spatializer": dict(
                    DEFAULT_SPATIALIZER_CONFIG[SFXClass.PROCEDURAL_VARIATION]
                ),
            }
            jobs.append(SFXJob(
                asset_id=f"{base_sfx_id}_var{i}",
                sfx_class=SFXClass.PROCEDURAL_VARIATION,
                backend=self.backend_name,
                source_path=base_path, output_path=output,
                metadata=metadata, success=success,
                started_at=started, finished_at=finished,
                error=None if success else "variation failed",
            ))
        return jobs

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def write_metadata_manifest(self, jobs: list[SFXJob]) -> pathlib.Path:
        """Write the spatializer-config YAML/JSON the UE5 runtime reads."""
        manifest_path = self.output_dir / "_manifest.json"
        manifest = {
            "asset_count": len(jobs),
            "by_class": {},
            "assets": [],
        }
        for j in jobs:
            cls_str = j.sfx_class.value
            manifest["by_class"][cls_str] = manifest["by_class"].get(cls_str, 0) + 1
            manifest["assets"].append({
                "asset_id": j.asset_id,
                "class": cls_str,
                "output_path": str(j.output_path),
                "success": j.success,
                "metadata": j.metadata,
            })
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest_path
