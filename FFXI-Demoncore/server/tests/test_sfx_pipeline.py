"""Tests for the SFX pipeline.

Run:  python -m pytest server/tests/test_sfx_pipeline.py -v
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from sfx_pipeline.pipeline import (
    DEFAULT_SPATIALIZER_CONFIG,
    SFXClass,
    SFXPipeline,
    StubBackend,
)


# ---------- fixtures ----------

@pytest.fixture
def fake_retail(tmp_path):
    """Mock a retail-extracted SFX dir with a few placeholder WAVs."""
    retail = tmp_path / "sfx_retail"
    retail.mkdir()
    for category in ("spells", "weapon_skills", "ambient", "ui"):
        (retail / category).mkdir()
    (retail / "spells" / "fire.wav").write_text("# fake retail wav")
    (retail / "spells" / "cure.wav").write_text("# fake retail wav")
    (retail / "weapon_skills" / "crescent_moon.wav").write_text("# fake retail wav")
    (retail / "ambient" / "bastok_marketplace.wav").write_text("# fake retail wav")
    (retail / "ui" / "tab_flip.wav").write_text("# fake retail wav")
    return retail


@pytest.fixture
def pipe(fake_retail, tmp_path):
    return SFXPipeline(
        retail_extracted_dir=fake_retail,
        output_dir=tmp_path / "sfx_out",
        backend="stub",
    )


# ---------- spatializer config ----------

def test_default_spatializer_config_per_class():
    """Each SFX class has a distinct spatializer default."""
    classes = [
        SFXClass.CANONICAL_PRESERVED,
        SFXClass.CANONICAL_REMASTERED,
        SFXClass.NEW_MECHANIC,
        SFXClass.PROCEDURAL_VARIATION,
    ]
    for cls in classes:
        assert cls in DEFAULT_SPATIALIZER_CONFIG
        config = DEFAULT_SPATIALIZER_CONFIG[cls]
        assert config["type"] == "3d_spatialized"


def test_canonical_preserved_is_not_mood_aware():
    """The user's hard rule: spell sounds don't change with mood."""
    cfg = DEFAULT_SPATIALIZER_CONFIG[SFXClass.CANONICAL_PRESERVED]
    assert cfg["mood_aware"] is False


def test_other_classes_are_mood_aware():
    """Ambient + new mechanic + variations DO modulate with mood."""
    for cls in (SFXClass.CANONICAL_REMASTERED,
                SFXClass.NEW_MECHANIC,
                SFXClass.PROCEDURAL_VARIATION):
        assert DEFAULT_SPATIALIZER_CONFIG[cls]["mood_aware"] is True


# ---------- Class 1 / 2: upscale ----------

def test_upscale_canonical_preserved(pipe):
    """Spell sound HD upscale lands in preserved/."""
    job = pipe.upscale_canonical(
        asset_id="spells/fire",
        sfx_class=SFXClass.CANONICAL_PRESERVED,
    )
    assert job.success is True
    assert job.sfx_class == SFXClass.CANONICAL_PRESERVED
    assert "preserved" in str(job.output_path)
    assert job.output_path.is_file()
    assert job.metadata["spatializer"]["mood_aware"] is False


def test_upscale_canonical_remastered(pipe):
    """Ambient sound HD remaster lands in remastered/."""
    job = pipe.upscale_canonical(
        asset_id="ambient/bastok_marketplace",
        sfx_class=SFXClass.CANONICAL_REMASTERED,
    )
    assert job.success is True
    assert "remastered" in str(job.output_path)
    assert job.metadata["spatializer"]["mood_aware"] is True


def test_upscale_missing_source_returns_error(pipe):
    job = pipe.upscale_canonical(asset_id="spells/nonexistent_spell")
    assert job.success is False
    assert "source not found" in job.error


def test_upscale_extra_metadata_propagates(pipe):
    job = pipe.upscale_canonical(
        asset_id="weapon_skills/crescent_moon",
        sfx_class=SFXClass.CANONICAL_PRESERVED,
        extra_metadata={"sync_to_anim_notify": "WS_CrescentMoon_Impact",
                        "attenuation_curve": "weapon_swing"},
    )
    assert job.success is True
    assert job.metadata["spatializer"]["sync_to_anim_notify"] == \
           "WS_CrescentMoon_Impact"


def test_upscale_no_retail_dir_raises(tmp_path):
    pipe = SFXPipeline(
        retail_extracted_dir=None,
        output_dir=tmp_path / "out",
        backend="stub",
    )
    with pytest.raises(ValueError, match="retail_extracted_dir not set"):
        pipe.upscale_canonical(asset_id="spells/fire")


# ---------- Class 3: new mechanic sounds ----------

def test_author_new_mechanic_sound(pipe):
    job = pipe.author_new_mechanic_sound(
        mechanic_id="nin_chakra_flow",
        prompt="4-second blue chakra ambient hum, ramping brightness",
        duration_sec=4.0,
    )
    assert job.success is True
    assert job.sfx_class == SFXClass.NEW_MECHANIC
    assert "authored" in str(job.output_path)
    assert job.metadata["authored_prompt"].startswith("4-second blue chakra")
    assert job.metadata["duration_seconds"] == 4.0


def test_author_intervention_save_sound(pipe):
    """The apex moment SFX per INTERVENTION_MB.md."""
    job = pipe.author_new_mechanic_sound(
        mechanic_id="intervention_mb_cure_v_light",
        prompt="gold harp glissando + choir 'ah' + bell chime + warm "
               "breath, 1.5 second cue, full ensemble shimmer",
        duration_sec=1.5,
    )
    assert job.success is True
    assert "intervention" in job.asset_id


# ---------- Class 4: procedural variations ----------

def test_generate_variation_set(pipe, fake_retail):
    base = fake_retail / "weapon_skills" / "crescent_moon.wav"
    jobs = pipe.generate_variation_set(
        base_sfx_id="ws_crescent_moon",
        base_path=base,
        num_variations=5,
    )
    assert len(jobs) == 5
    assert all(j.success for j in jobs)
    # Each variation has a distinct output path
    paths = {str(j.output_path) for j in jobs}
    assert len(paths) == 5
    # Pitch + time vary across the set
    pitches = {j.metadata["pitch_cents"] for j in jobs}
    assert len(pitches) > 1   # actually varies


def test_variations_seeded_by_asset_id(pipe, fake_retail):
    """Same asset_id produces the same variation parameters (deterministic)."""
    base = fake_retail / "weapon_skills" / "crescent_moon.wav"
    jobs1 = pipe.generate_variation_set(
        base_sfx_id="ws_crescent_moon", base_path=base, num_variations=3,
    )
    jobs2 = pipe.generate_variation_set(
        base_sfx_id="ws_crescent_moon", base_path=base, num_variations=3,
    )
    pitches1 = [j.metadata["pitch_cents"] for j in jobs1]
    pitches2 = [j.metadata["pitch_cents"] for j in jobs2]
    assert pitches1 == pitches2


# ---------- manifest ----------

def test_manifest_aggregates_jobs(pipe, fake_retail):
    jobs = []
    jobs.append(pipe.upscale_canonical(asset_id="spells/fire"))
    jobs.append(pipe.upscale_canonical(asset_id="spells/cure"))
    jobs.append(pipe.upscale_canonical(
        asset_id="ambient/bastok_marketplace",
        sfx_class=SFXClass.CANONICAL_REMASTERED,
    ))
    jobs.append(pipe.author_new_mechanic_sound(
        mechanic_id="dual_cast_bell",
        prompt="single bright bell, half-second decay",
        duration_sec=0.5,
    ))
    jobs.extend(pipe.generate_variation_set(
        base_sfx_id="ws_crescent_moon",
        base_path=fake_retail / "weapon_skills" / "crescent_moon.wav",
        num_variations=3,
    ))
    manifest_path = pipe.write_metadata_manifest(jobs)
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["asset_count"] == 7
    assert manifest["by_class"]["canonical_preserved"] == 2
    assert manifest["by_class"]["canonical_remastered"] == 1
    assert manifest["by_class"]["new_mechanic"] == 1
    assert manifest["by_class"]["procedural_variation"] == 3


# ---------- backend selection ----------

def test_unknown_backend_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown sfx backend"):
        SFXPipeline(
            retail_extracted_dir=None,
            output_dir=tmp_path / "out",
            backend="not_real",
        )


def test_audiosr_unreachable_doesnt_crash(fake_retail, tmp_path):
    pipe = SFXPipeline(
        retail_extracted_dir=fake_retail,
        output_dir=tmp_path / "out",
        backend="audiosr",
        backend_kwargs={
            "audiosr_url": "http://localhost:1",
            "author_url": "http://localhost:1",
            "timeout_seconds": 0.1,
        },
    )
    job = pipe.upscale_canonical(asset_id="spells/fire")
    assert job.success is False
    assert job.error is not None


# ---------- stub backend operation log ----------

def test_stub_backend_records_operations(pipe, fake_retail):
    pipe.upscale_canonical(asset_id="spells/fire")
    pipe.author_new_mechanic_sound(
        mechanic_id="nin_chakra_flow",
        prompt="test", duration_sec=1.0,
    )
    base = fake_retail / "weapon_skills" / "crescent_moon.wav"
    pipe.generate_variation_set(
        base_sfx_id="ws_test", base_path=base, num_variations=2,
    )
    ops = [c["op"] for c in pipe.backend.calls]
    assert "upscale" in ops
    assert "author_new" in ops
    assert "vary" in ops
