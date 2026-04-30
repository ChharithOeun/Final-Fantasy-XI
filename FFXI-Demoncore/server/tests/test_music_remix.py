"""Tests for the music remix pipeline.

Run:  python -m pytest server/tests/test_music_remix.py -v
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from music_pipeline.remix import (
    AceStepRemixBackend,
    MOOD_VARIANT_TEMPLATES,
    RemixPipeline,
    StubRemixBackend,
)


# ---------- fixtures ----------

@pytest.fixture
def fake_retail(tmp_path):
    """Mock a retail-extracted music dir with a placeholder WAV."""
    retail_dir = tmp_path / "music_retail"
    retail_dir.mkdir()
    (retail_dir / "bgm_bastok_markets.wav").write_text("# fake retail wav")
    (retail_dir / "bgm_san_doria.wav").write_text("# fake retail wav")
    (retail_dir / "bgm_battle_versus_the_shadow_lord.wav").write_text("# fake")
    return retail_dir


@pytest.fixture
def pipe(fake_retail, tmp_path):
    return RemixPipeline(
        retail_extracted_dir=fake_retail,
        output_dir=tmp_path / "remix_out",
        backend="stub",
    )


# ---------- prompt template selection ----------

def test_default_mood_templates_exist():
    expected = {"daytime", "nighttime", "siege", "aftermath", "battle"}
    assert expected.issubset(set(MOOD_VARIANT_TEMPLATES.keys()))


def test_compose_daytime_prompt(pipe):
    prompt = pipe._compose_style_prompt("daytime")
    assert "warm" in prompt or "bright" in prompt
    assert "modern_orchestral" in prompt   # default style_config primary_genre


def test_compose_aftermath_prompt(pipe):
    prompt = pipe._compose_style_prompt("aftermath")
    assert "fantasy_orchestral" in prompt   # secondary_genre
    assert "reverent" in prompt or "introspection" in prompt


def test_compose_unknown_variant_falls_back(pipe):
    prompt = pipe._compose_style_prompt("unknown_mood_variant")
    # Should still produce a valid prompt via fallback
    assert "modern_orchestral" in prompt
    assert "fantasy game music" in prompt


def test_custom_style_config_propagates(fake_retail, tmp_path):
    custom = {
        "primary_genre": "synthwave",
        "secondary_genre": "lofi",
        "lead_instruments": "analog synth",
        "drum_kit": "808 + clap",
        "bass_synth": "moog_bass",
        "production_tags": [],
    }
    pipe = RemixPipeline(
        retail_extracted_dir=fake_retail,
        output_dir=tmp_path / "out",
        style_config=custom,
        backend="stub",
    )
    prompt = pipe._compose_style_prompt("daytime")
    assert "synthwave" in prompt
    assert "808" in prompt
    assert "analog synth" in prompt


# ---------- remix execution (stub backend) ----------

def test_remix_track_writes_stems_and_output(pipe):
    job = pipe.remix_track(track_id="bgm_bastok_markets",
                            mood_variant="daytime")
    assert job.success is True
    assert job.error is None
    assert job.track_id == "bgm_bastok_markets"
    assert job.mood_variant == "daytime"

    # Stems landed
    stems_dir = pipe.output_dir / "stems" / "bgm_bastok_markets"
    assert stems_dir.is_dir()
    for stem in ("vocals", "bass", "drums", "other"):
        assert (stems_dir / f"{stem}.wav").is_file()

    # Output landed
    assert job.output_path.is_file()
    output_content = job.output_path.read_text()
    assert "modern_orchestral" in output_content


def test_remix_track_missing_source_returns_error(pipe):
    job = pipe.remix_track(track_id="bgm_doesnt_exist",
                            mood_variant="daytime")
    assert job.success is False
    assert "source track not found" in job.error


def test_remix_track_skips_stem_separation_on_cache(pipe):
    """Re-running on the same track skips re-stemming (cached)."""
    pipe.remix_track(track_id="bgm_bastok_markets", mood_variant="daytime")
    initial_calls = len(pipe.backend.calls)

    # Re-run a different mood variant — stems should be cached
    pipe.remix_track(track_id="bgm_bastok_markets", mood_variant="nighttime")
    new_calls = len(pipe.backend.calls)

    # Only 1 new apply_style call, no stem_separate call
    new_call_ops = [c["op"] for c in pipe.backend.calls[initial_calls:]]
    assert "stem_separate" not in new_call_ops
    assert new_call_ops == ["apply_style"]


def test_remix_all_variants(pipe):
    jobs = pipe.remix_all_variants(track_id="bgm_bastok_markets")
    assert len(jobs) == 4
    moods = {j.mood_variant for j in jobs}
    assert moods == {"daytime", "nighttime", "siege", "aftermath"}
    assert all(j.success for j in jobs)


def test_remix_all_variants_custom_subset(pipe):
    jobs = pipe.remix_all_variants(
        track_id="bgm_san_doria",
        variants=["daytime", "battle"],
    )
    assert len(jobs) == 2
    assert {j.mood_variant for j in jobs} == {"daytime", "battle"}


# ---------- manifest ----------

def test_write_manifest(pipe):
    jobs = pipe.remix_all_variants(track_id="bgm_bastok_markets")
    jobs.extend(pipe.remix_all_variants(track_id="bgm_san_doria"))
    manifest_path = pipe.write_manifest(jobs)
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text())
    assert "tracks" in manifest
    assert "bgm_bastok_markets" in manifest["tracks"]
    assert "bgm_san_doria" in manifest["tracks"]
    bastok_variants = manifest["tracks"]["bgm_bastok_markets"]["variants"]
    assert len(bastok_variants) == 4


# ---------- backend selection ----------

def test_unknown_backend_raises(fake_retail, tmp_path):
    with pytest.raises(ValueError, match="unknown remix backend"):
        RemixPipeline(
            retail_extracted_dir=fake_retail,
            output_dir=tmp_path / "out",
            backend="not_real",
        )


def test_ace_step_remix_unreachable_doesnt_crash(fake_retail, tmp_path):
    """Real backend with unreachable services fails gracefully."""
    pipe = RemixPipeline(
        retail_extracted_dir=fake_retail,
        output_dir=tmp_path / "out",
        backend="ace_step_remix",
        backend_kwargs={
            "demucs_url": "http://localhost:1",
            "ace_url": "http://localhost:1",
            "timeout_seconds": 0.1,
        },
    )
    job = pipe.remix_track(track_id="bgm_bastok_markets",
                            mood_variant="daytime")
    assert job.success is False
    assert job.error in ("stem separation failed", "style transfer failed")
