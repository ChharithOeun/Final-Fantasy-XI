"""Tests for skill decay."""
from __future__ import annotations

from server.skill_decay import (
    DECAY_GRACE_SECONDS,
    SkillDecayRegistry,
)


def test_register_skill():
    reg = SkillDecayRegistry()
    rec = reg.register_skill(
        player_id="alice", skill_id="sword",
        level=200,
    )
    assert rec is not None
    assert rec.level == 200
    assert rec.historical_peak == 200


def test_double_register_rejected():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=100,
    )
    second = reg.register_skill(
        player_id="alice", skill_id="sword", level=300,
    )
    assert second is None


def test_level_lookup():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
    )
    assert reg.level(
        player_id="alice", skill_id="sword",
    ) == 200


def test_unknown_skill_level_zero():
    reg = SkillDecayRegistry()
    assert reg.level(
        player_id="alice", skill_id="ghost",
    ) == 0


def test_practice_increments_level():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
    )
    new_lvl = reg.practice(
        player_id="alice", skill_id="sword", gain=5,
    )
    assert new_lvl == 205
    assert reg.level(
        player_id="alice", skill_id="sword",
    ) == 205


def test_practice_updates_peak():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
    )
    reg.practice(
        player_id="alice", skill_id="sword", gain=10,
    )
    rec = reg._records[("alice", "sword")]
    assert rec.historical_peak == 210


def test_no_decay_within_grace():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
        now_seconds=0.0,
    )
    decays = reg.tick(now_seconds=DECAY_GRACE_SECONDS - 1)
    assert decays == ()


def test_decay_after_grace():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
        now_seconds=0.0,
    )
    # 7-day grace + 5 days of decay = 5 points
    days_5 = DECAY_GRACE_SECONDS + 5 * 24 * 3600
    decays = reg.tick(now_seconds=days_5)
    assert len(decays) == 1
    assert decays[0].decayed == 5
    assert decays[0].new_level == 195


def test_decay_floor_protects_progress():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
        now_seconds=0.0,
    )
    # Massive elapsed time
    huge = DECAY_GRACE_SECONDS + 10000 * 24 * 3600
    reg.tick(now_seconds=huge)
    rec = reg._records[("alice", "sword")]
    # Floor is 200 * 0.8 = 160
    assert rec.level == 160


def test_decay_only_dispatches_when_change():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=10,
        now_seconds=0.0,
    )
    # Level=10, peak=10, floor=8. After 30 days past grace:
    # decays toward floor. But at floor (8), no further decay.
    far = DECAY_GRACE_SECONDS + 100 * 24 * 3600
    reg.tick(now_seconds=far)
    decays = reg.tick(now_seconds=far + 24 * 3600)
    assert decays == ()


def test_practice_after_decay_roosts_back():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
        now_seconds=0.0,
    )
    # Force decay
    elapsed = DECAY_GRACE_SECONDS + 30 * 24 * 3600
    reg.tick(now_seconds=elapsed)
    decayed_level = reg.level(
        player_id="alice", skill_id="sword",
    )
    assert decayed_level == 170
    # Roost: 1-point practice should jump by ROOST_RECOVERY_RATE
    new_lvl = reg.practice(
        player_id="alice", skill_id="sword", gain=1,
        now_seconds=elapsed + 1,
    )
    assert new_lvl > decayed_level + 1


def test_roost_caps_at_historical_peak():
    """Single roost-mode practice should not overshoot the
    historical peak. Normal training resumes only after the
    skill has fully roosted back."""
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
        now_seconds=0.0,
    )
    elapsed = DECAY_GRACE_SECONDS + 30 * 24 * 3600
    reg.tick(now_seconds=elapsed)
    # Decayed to 170. One practice with huge gain should
    # clamp to historical peak 200, not overshoot.
    new_lvl = reg.practice(
        player_id="alice", skill_id="sword", gain=999,
        now_seconds=elapsed + 1,
    )
    assert new_lvl == 200


def test_floor_for_lookup():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
    )
    floor = reg.floor_for(
        player_id="alice", skill_id="sword",
    )
    assert floor == 160


def test_floor_for_unknown_returns_none():
    reg = SkillDecayRegistry()
    assert reg.floor_for(
        player_id="ghost", skill_id="x",
    ) is None


def test_practice_unknown_returns_none():
    reg = SkillDecayRegistry()
    assert reg.practice(
        player_id="ghost", skill_id="x", gain=1,
    ) is None


def test_practice_zero_gain_rejected():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=10,
    )
    assert reg.practice(
        player_id="alice", skill_id="sword", gain=0,
    ) is None


def test_total_skills_tracked():
    reg = SkillDecayRegistry()
    reg.register_skill(
        player_id="alice", skill_id="sword", level=200,
    )
    reg.register_skill(
        player_id="alice", skill_id="archery", level=180,
    )
    reg.register_skill(
        player_id="bob", skill_id="sword", level=220,
    )
    assert reg.total_skills_tracked() == 3


def test_negative_starting_level_clamped():
    reg = SkillDecayRegistry()
    rec = reg.register_skill(
        player_id="alice", skill_id="sword", level=-5,
    )
    assert rec.level == 0
