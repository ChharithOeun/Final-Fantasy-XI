"""Tests for player_sculpture."""
from __future__ import annotations

from server.player_sculpture import (
    PlayerSculptureSystem, SculptureStage, StoneKind,
)


def _begin(
    s: PlayerSculptureSystem,
    skill: int = 80,
    stone: StoneKind = StoneKind.MARBLE,
) -> str:
    return s.begin_sculpture(
        sculptor_id="naji", title="The Maiden",
        stone=stone, sculptor_skill=skill,
    )


def test_begin_happy():
    s = PlayerSculptureSystem()
    sid = _begin(s)
    assert sid is not None


def test_begin_empty_sculptor():
    s = PlayerSculptureSystem()
    assert s.begin_sculpture(
        sculptor_id="", title="X",
        stone=StoneKind.MARBLE, sculptor_skill=70,
    ) is None


def test_begin_invalid_skill():
    s = PlayerSculptureSystem()
    assert s.begin_sculpture(
        sculptor_id="a", title="X",
        stone=StoneKind.MARBLE, sculptor_skill=0,
    ) is None


def test_starting_stage_is_block():
    s = PlayerSculptureSystem()
    sid = _begin(s)
    assert s.sculpture(
        sculpture_id=sid,
    ).stage == SculptureStage.BLOCK


def test_advance_to_rough_cut_high_skill():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    nxt = s.advance_stage(sculpture_id=sid, seed=0)
    assert nxt == SculptureStage.ROUGH_CUT


def test_advance_full_chain_high_skill():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    s.advance_stage(sculpture_id=sid, seed=0)
    s.advance_stage(sculpture_id=sid, seed=0)
    s.advance_stage(sculpture_id=sid, seed=0)
    assert s.sculpture(
        sculpture_id=sid,
    ).stage == SculptureStage.POLISHED


def test_low_skill_can_crack():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=1)
    # Crack pressure for rough_cut = 30 - 1 = 29
    # Seed 0 -> roll 0 -> 0 < 29 -> crack
    nxt = s.advance_stage(sculpture_id=sid, seed=0)
    assert nxt == SculptureStage.CRACKED


def test_advance_after_crack_blocked():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=1)
    s.advance_stage(sculpture_id=sid, seed=0)
    assert s.advance_stage(
        sculpture_id=sid, seed=0,
    ) is None


def test_advance_after_polished_blocked():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    for _ in range(3):
        s.advance_stage(sculpture_id=sid, seed=0)
    assert s.advance_stage(
        sculpture_id=sid, seed=0,
    ) is None


def test_advance_grows_quality():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100, stone=StoneKind.MARBLE)
    before = s.sculpture(
        sculpture_id=sid,
    ).quality_score
    s.advance_stage(sculpture_id=sid, seed=0)
    after = s.sculpture(
        sculpture_id=sid,
    ).quality_score
    assert after > before


def test_install_happy():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    for _ in range(3):
        s.advance_stage(sculpture_id=sid, seed=0)
    assert s.install(
        sculpture_id=sid,
        install_location="bastok_plaza",
    ) is True


def test_install_before_polish_blocked():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    s.advance_stage(sculpture_id=sid, seed=0)
    assert s.install(
        sculpture_id=sid,
        install_location="bastok_plaza",
    ) is False


def test_install_empty_location():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    for _ in range(3):
        s.advance_stage(sculpture_id=sid, seed=0)
    assert s.install(
        sculpture_id=sid, install_location="",
    ) is False


def test_install_after_crack_blocked():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=1)
    s.advance_stage(sculpture_id=sid, seed=0)
    assert s.install(
        sculpture_id=sid,
        install_location="bastok_plaza",
    ) is False


def test_installed_at_lookup():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    for _ in range(3):
        s.advance_stage(sculpture_id=sid, seed=0)
    s.install(
        sculpture_id=sid,
        install_location="bastok_plaza",
    )
    assert len(
        s.installed_at(install_location="bastok_plaza"),
    ) == 1
    assert len(
        s.installed_at(install_location="elsewhere"),
    ) == 0


def test_obsidian_higher_starting_quality():
    s = PlayerSculptureSystem()
    lime_sid = _begin(s, stone=StoneKind.LIMESTONE)
    obs_sid = _begin(s, stone=StoneKind.OBSIDIAN)
    assert (
        s.sculpture(sculpture_id=obs_sid).quality_score
        > s.sculpture(sculpture_id=lime_sid).quality_score
    )


def test_days_worked_accumulates():
    s = PlayerSculptureSystem()
    sid = _begin(s, skill=100)
    s.advance_stage(sculpture_id=sid, seed=0)
    s.advance_stage(sculpture_id=sid, seed=0)
    assert s.sculpture(
        sculpture_id=sid,
    ).days_worked == 2


def test_unknown_sculpture():
    s = PlayerSculptureSystem()
    assert s.sculpture(sculpture_id="ghost") is None
    assert s.advance_stage(
        sculpture_id="ghost", seed=0,
    ) is None


def test_enum_counts():
    assert len(list(StoneKind)) == 4
    assert len(list(SculptureStage)) == 6
