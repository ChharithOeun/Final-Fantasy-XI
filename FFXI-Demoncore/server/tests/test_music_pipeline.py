"""Tests for the music pipeline.

Run:  python -m pytest server/tests/test_music_pipeline.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from music_pipeline.pipeline import (
    AceStepBackend,
    MusicPipeline,
    StubBackend,
    _compose_prompt,
)


@pytest.fixture
def pipe(tmp_path):
    return MusicPipeline(
        output_dir=tmp_path / "music",
        backend="stub",
    )


# ---------------------- prompt composition ----------------------

def test_compose_bgm_prompt():
    prompt = _compose_prompt("bgm", {
        "mood": "industrial warmth",
        "tempo": "medium",
        "instrumentation": "brass + percussion",
        "location": "Bastok Markets",
    })
    assert "industrial warmth" in prompt
    assert "Bastok Markets" in prompt
    assert "brass" in prompt
    assert "looping" in prompt


def test_compose_boss_prompt():
    prompt = _compose_prompt("boss", {
        "personality": "stern monk who tests apprentices",
        "mood_axes": ["content", "gruff", "mischievous"],
        "intensity": "high",
    })
    assert "stern monk" in prompt
    assert "boss battle theme" in prompt
    assert "mischievous" in prompt


def test_compose_stinger_known_event():
    prompt = _compose_prompt("stinger", {
        "event_kind": "intervention_save",
    })
    assert "redemptive" in prompt
    assert "fanfare" in prompt


def test_compose_stinger_unknown_event_falls_back():
    prompt = _compose_prompt("stinger", {
        "event_kind": "bizarre_unknown_event",
        "duration_seconds": 5.0,
    })
    assert "5" in prompt or "stinger" in prompt


# ---------------------- backend stubs ----------------------

def test_stub_backend_writes_placeholder(tmp_path):
    backend = StubBackend()
    output = tmp_path / "test.wav"
    ok = backend.synthesize(
        prompt="test prompt",
        output_path=output,
        duration_seconds=10.0,
    )
    assert ok is True
    assert output.is_file()
    assert "test prompt" in output.read_text()
    assert len(backend.calls) == 1


def test_unknown_backend_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown backend"):
        MusicPipeline(output_dir=tmp_path, backend="not_real")


# ---------------------- pipeline generation ----------------------

def test_generate_zone_bgm(pipe):
    job = pipe.generate_zone_bgm("bastok_markets", {
        "mood": "industrial warmth",
        "tempo": "medium",
        "instrumentation": "brass + percussion + low strings",
    })
    assert job.success is True
    assert job.asset_id == "bgm_bastok_markets"
    assert job.asset_kind == "bgm"
    assert job.duration_seconds_target == 180.0
    assert job.output_path.is_file()
    assert "bastok_markets" in str(job.output_path)


def test_generate_boss_theme(pipe):
    job = pipe.generate_boss_theme(
        "hero_maat",
        personality="stern monk, retired captain",
        mood_axes=["content", "gruff", "mischievous", "furious"],
        intensity="high",
    )
    assert job.success is True
    assert job.asset_id == "boss_hero_maat"
    assert job.duration_seconds_target == 120.0
    assert "Bastok" not in job.prompt_used  # we didn't pass a location


def test_generate_stinger(pipe):
    job = pipe.generate_stinger("skillchain_close", duration_seconds=3.0)
    assert job.success is True
    assert job.asset_id == "stinger_skillchain_close"


def test_canonical_stinger_set(pipe):
    jobs = pipe.generate_canonical_stinger_set()
    assert len(jobs) == 8
    asset_ids = {j.asset_id for j in jobs}
    assert "stinger_skillchain_close" in asset_ids
    assert "stinger_intervention_save" in asset_ids
    assert "stinger_boss_defeat" in asset_ids
    assert all(j.success for j in jobs)


# ---------------------- ACE-Step graceful failure ----------------------

def test_ace_step_unreachable_doesnt_crash(tmp_path):
    pipe = MusicPipeline(
        output_dir=tmp_path / "music",
        backend="ace_step",
        backend_kwargs={"url": "http://localhost:1", "timeout_seconds": 0.1},
    )
    job = pipe.generate_zone_bgm("test_zone", {
        "mood": "test", "tempo": "fast", "instrumentation": "synth",
    })
    assert job.success is False
    assert job.error is not None
