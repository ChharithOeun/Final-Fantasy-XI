"""Tests for the voice pipeline.

Run:  python -m pytest server/tests/test_voice_pipeline.py -v
"""
import json
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.loader import AgentProfile
from voice_pipeline.pipeline import (
    StubBackend,
    VoicePipeline,
    _compose_conditioning_prompt,
)


def _resolve_callouts():
    """Find data/skillchain_callouts.yaml from the test location."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "data" / "skillchain_callouts.yaml",
        here.parent / "data" / "skillchain_callouts.yaml",
    ]
    return next((p for p in candidates if p.is_file()), candidates[0])


@pytest.fixture
def callouts_path():
    p = _resolve_callouts()
    if not p.is_file():
        pytest.skip(f"callouts file not present at {p}")
    return p


@pytest.fixture
def pipeline(callouts_path, tmp_path):
    return VoicePipeline(
        callouts_path=callouts_path,
        output_dir=tmp_path / "voices",
        backend="stub",
    )


@pytest.fixture
def fake_zaldon():
    return AgentProfile(
        id="vendor_zaldon",
        name="Zaldon",
        zone="bastok_markets",
        position=(-2400.0, -2400.0, 130.0),
        tier="2_reflection",
        role="vendor_zaldon",
        race="hume",
        gender="m",
        voice_profile="/Content/Voices/profiles/zaldon.wav",
        appearance="Weathered fisherman",
        raw={"id": "vendor_zaldon"},
    )


# ----------------------------------------------------------------------
# Conditioning prompt composition
# ----------------------------------------------------------------------

def test_conditioning_prompt_no_mood():
    prompt = _compose_conditioning_prompt(None, "chain_open")
    assert prompt == "natural delivery"


def test_conditioning_prompt_furious():
    prompt = _compose_conditioning_prompt("furious", "chain_open")
    assert "louder" in prompt
    assert "sharper" in prompt


def test_conditioning_prompt_level_3_close():
    prompt = _compose_conditioning_prompt("content", "level_3_close.light")
    assert "warm" in prompt
    assert "triumphant" in prompt


def test_conditioning_prompt_intervention():
    prompt = _compose_conditioning_prompt("alert", "intervention_cure")
    assert "crisp" in prompt
    assert "focused" in prompt


# ----------------------------------------------------------------------
# Pipeline enumeration
# ----------------------------------------------------------------------

def test_pipeline_enumerates_callouts(pipeline):
    lines = pipeline._enumerate_lines()
    assert len(lines) > 50  # we have ~95+ lines per the YAML

    # Spot-check expected lines exist
    texts = [t for _, _, t in lines]
    assert any("Skillchain open" in t for t in texts)
    assert any("Magic Burst" in t for t in texts)
    # Intervention added in chunk 5
    assert any("Cure burst" in t or "Cure!" in t for t in texts)


def test_pipeline_enumerates_moods(pipeline):
    lines = pipeline._enumerate_lines()
    moods = {mood for _, mood, _ in lines if mood}
    # Mood variants pulled in from level_1_close.liquefaction.mood_furious etc
    assert "furious" in moods or any("LIQUEFACTION" in t for _, _, t in lines)


# ----------------------------------------------------------------------
# Stub backend generation for an agent
# ----------------------------------------------------------------------

def test_generate_for_agent_stub(pipeline, fake_zaldon):
    job = pipeline.generate_for_agent(fake_zaldon)
    assert job.lines_planned > 50
    assert job.lines_generated == job.lines_planned
    assert job.failed_lines == []
    assert job.backend == "stub"
    assert job.output_dir.is_dir()

    # Manifest exists and is valid JSON
    assert job.manifest_path.is_file()
    manifest = json.loads(job.manifest_path.read_text())
    assert manifest["actor_id"] == "vendor_zaldon"
    assert manifest["lines_generated"] == job.lines_generated

    # Spot-check a few generated files exist
    files = list(job.output_dir.glob("*.wav"))
    assert len(files) > 50


def test_generate_without_voice_profile_raises(pipeline):
    no_voice = AgentProfile(
        id="x", name="X", zone="z", position=(0.0, 0.0, 0.0),
        tier="2_reflection", role="x", race="hume", gender="m",
        voice_profile=None,  # missing
        appearance=None, raw={"id": "x"},
    )
    with pytest.raises(ValueError, match="no voice_profile"):
        pipeline.generate_for_agent(no_voice)


# ----------------------------------------------------------------------
# Mob class generation
# ----------------------------------------------------------------------

def test_generate_for_mob_class(pipeline, tmp_path):
    """Generate stock voice for a mob class."""
    # Find a mob_class YAML
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "agents" / "_mob_classes",
        here.parent / "agents" / "_mob_classes",
    ]
    mob_dir = next((p for p in candidates if p.is_dir()), None)
    if mob_dir is None:
        pytest.skip("no mob_classes dir to test against")

    mob_yamls = sorted(mob_dir.glob("*.yaml"))
    if not mob_yamls:
        pytest.skip("no mob_class YAMLs to test against")

    job = pipeline.generate_for_mob_class(mob_yamls[0])
    assert job.actor_id == yaml.safe_load(mob_yamls[0].read_text())["mob_class"]
    assert job.lines_generated > 50


# ----------------------------------------------------------------------
# Player generation
# ----------------------------------------------------------------------

def test_generate_for_player(pipeline, tmp_path):
    fake_ref = tmp_path / "fake_player_voice.wav"
    fake_ref.write_bytes(b"")
    job = pipeline.generate_for_player(
        player_id="player_alice",
        reference_wav=str(fake_ref),
    )
    assert job.actor_id == "player_alice"
    assert job.output_dir.name == "player_alice"
    manifest = json.loads(job.manifest_path.read_text())
    assert manifest["voice_profile"] == str(fake_ref)


# ----------------------------------------------------------------------
# Backend selection
# ----------------------------------------------------------------------

def test_unknown_backend_raises(callouts_path, tmp_path):
    with pytest.raises(ValueError, match="unknown backend"):
        VoicePipeline(
            callouts_path=callouts_path,
            output_dir=tmp_path,
            backend="not_a_real_backend",
        )


def test_stub_backend_records_calls(callouts_path, tmp_path, fake_zaldon):
    pipe = VoicePipeline(
        callouts_path=callouts_path,
        output_dir=tmp_path / "voices",
        backend="stub",
    )
    job = pipe.generate_for_agent(fake_zaldon)
    # The stub backend tracks every call
    assert len(pipe.backend.calls) == job.lines_generated


def test_higgs_backend_unreachable_doesnt_crash(callouts_path, tmp_path,
                                                  fake_zaldon):
    """If Higgs isn't running, lines fail gracefully but the pipeline runs."""
    pipe = VoicePipeline(
        callouts_path=callouts_path,
        output_dir=tmp_path / "voices",
        backend="higgs",
        backend_kwargs={"url": "http://localhost:1", "timeout_seconds": 0.1},
    )
    # All lines fail (no Higgs server), but the job completes
    job = pipe.generate_for_agent(fake_zaldon)
    assert job.lines_generated == 0
    assert len(job.failed_lines) == job.lines_planned
