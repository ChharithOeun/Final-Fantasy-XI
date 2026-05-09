"""Render queue — Movie Render Queue presets + EXR export.

Demoncore drives UE5's Movie Render Queue (MRQ) with named
presets:

    gameplay_realtime      — 60fps TSR, fast mp4 H.265
    cutscene_cinematic     — 24fps path-traced ProRes 4444
    trailer_master         — 24fps 16-bit half-float EXR,
                             ACES OCIO, no compression
    social_clip            — 60fps 4K AV1, mobile 8Mbps
    led_virtual_production — 24fps in-camera VFX (ICVFX)

The server selects a preset, ships it to UE5, queues the
sequence, and computes an estimated wall-clock time so the
producer knows whether the trailer master will finish before
the meeting.

Public surface
--------------
    RenderPreset dataclass (frozen)
    PRESETS dict
    RenderJob dataclass (frozen)
    RenderQueueSystem
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class RenderPreset:
    name: str
    fps: int
    resolution: tuple[int, int]
    codec: str
    bit_depth: int
    color_space: str
    output_format: str         # "mp4" / "mov" / "exr_seq"
    samples_per_pixel: int
    motion_blur_enabled: bool
    cost_factor: float         # wall-time per second of footage
    shutter_angle_deg: float = 180.0


PRESETS: dict[str, RenderPreset] = {p.name: p for p in (
    RenderPreset(
        name="gameplay_realtime",
        fps=60, resolution=(1920, 1080),
        codec="H.265", bit_depth=8,
        color_space="Rec.709",
        output_format="mp4",
        samples_per_pixel=1,
        motion_blur_enabled=False,
        cost_factor=1.0,
    ),
    RenderPreset(
        name="cutscene_cinematic",
        fps=24, resolution=(3840, 2160),
        codec="ProRes_4444", bit_depth=12,
        color_space="ACES_AP1",
        output_format="mov",
        samples_per_pixel=16,
        motion_blur_enabled=True,
        cost_factor=30.0,
        shutter_angle_deg=180.0,
    ),
    RenderPreset(
        name="trailer_master",
        fps=24, resolution=(3840, 2160),
        codec="EXR_uncompressed", bit_depth=16,
        color_space="ACES_AP0",
        output_format="exr_seq",
        samples_per_pixel=64,
        motion_blur_enabled=True,
        cost_factor=120.0,
        shutter_angle_deg=180.0,
    ),
    RenderPreset(
        name="social_clip",
        fps=60, resolution=(3840, 2160),
        codec="AV1", bit_depth=8,
        color_space="Rec.709",
        output_format="mp4",
        samples_per_pixel=1,
        motion_blur_enabled=False,
        cost_factor=2.0,
    ),
    RenderPreset(
        name="led_virtual_production",
        fps=24, resolution=(3840, 2160),
        codec="ProRes_422HQ", bit_depth=10,
        color_space="ACES_AP1",
        output_format="mov",
        samples_per_pixel=4,
        motion_blur_enabled=True,
        cost_factor=8.0,
        shutter_angle_deg=180.0,
    ),
)}


@dataclasses.dataclass(frozen=True)
class RenderJob:
    job_id: str
    preset: str
    sequence: str
    output_path: str


@dataclasses.dataclass
class RenderQueueSystem:
    _selected: t.Optional[RenderPreset] = None
    _jobs: list[RenderJob] = dataclasses.field(
        default_factory=list,
    )
    _next: int = 1

    def select_preset(self, name: str) -> RenderPreset:
        if name not in PRESETS:
            raise ValueError(f"unknown preset: {name}")
        self._selected = PRESETS[name]
        return self._selected

    @property
    def selected(self) -> t.Optional[RenderPreset]:
        return self._selected

    def output_path_for(
        self, preset: str, sequence: str,
    ) -> str:
        if preset not in PRESETS:
            raise ValueError(f"unknown preset: {preset}")
        if not sequence:
            raise ValueError("sequence id required")
        p = PRESETS[preset]
        # MRQ writes EXR sequences as a frame folder; mp4 /
        # mov as single files.
        if p.output_format == "exr_seq":
            return (
                f"renders/{preset}/{sequence}/"
                f"{sequence}.####.exr"
            )
        return f"renders/{preset}/{sequence}.{p.output_format}"

    def queue_render(
        self, *, preset: str, sequence: str,
        output_path: t.Optional[str] = None,
    ) -> t.Optional[str]:
        if preset not in PRESETS:
            return None
        if not sequence:
            return None
        path = (
            output_path
            if output_path is not None
            else self.output_path_for(preset, sequence)
        )
        jid = f"job_{self._next}"
        self._next += 1
        self._jobs.append(RenderJob(
            job_id=jid, preset=preset,
            sequence=sequence, output_path=path,
        ))
        return jid

    def jobs(self) -> tuple[RenderJob, ...]:
        return tuple(self._jobs)

    def get_estimated_time(
        self, *, seconds_of_footage: float,
        preset: t.Optional[str] = None,
    ) -> float:
        """Wall-clock estimate in seconds.

            estimate = seconds_of_footage * cost_factor

        cost_factor for trailer_master is 120x — i.e. 60s of
        footage takes 2 hours."""
        if seconds_of_footage <= 0:
            raise ValueError(
                "seconds_of_footage must be positive",
            )
        if preset is not None:
            if preset not in PRESETS:
                raise ValueError(f"unknown preset: {preset}")
            p = PRESETS[preset]
        else:
            if self._selected is None:
                raise RuntimeError("no preset selected")
            p = self._selected
        return seconds_of_footage * p.cost_factor

    def cancel(self, job_id: str) -> bool:
        for i, j in enumerate(self._jobs):
            if j.job_id == job_id:
                del self._jobs[i]
                return True
        return False


def list_presets() -> tuple[str, ...]:
    return tuple(sorted(PRESETS))


def preset(name: str) -> RenderPreset:
    if name not in PRESETS:
        raise ValueError(f"unknown preset: {name}")
    return PRESETS[name]


__all__ = [
    "RenderPreset", "PRESETS",
    "RenderJob", "RenderQueueSystem",
    "list_presets", "preset",
]
