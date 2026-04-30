"""Demoncore music generation pipeline.

Per MUSIC_PIPELINE.md (already designed). Wraps the cloned ACE-Step
v1.5 model + a stub backend so this can run in CI without GPU. Emits
zone BGM tracks + boss themes + skillchain stinger cues + cinematic
motifs.

Public surface:
    MusicPipeline(prompt_lib_path, output_dir, backend)
    MusicPipeline.generate_zone_bgm(zone_slug, atmosphere)
    MusicPipeline.generate_boss_theme(boss_id, mood_axes)
    MusicPipeline.generate_stinger(event_kind)
"""
from .pipeline import MusicJob, MusicPipeline

__all__ = ["MusicPipeline", "MusicJob"]
