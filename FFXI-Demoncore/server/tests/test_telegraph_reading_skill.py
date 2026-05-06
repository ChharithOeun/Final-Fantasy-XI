"""Tests for telegraph_reading_skill."""
from __future__ import annotations

from server.telegraph_reading_skill import (
    SKILL_CAP,
    TelegraphReadingSkill,
    Tier,
    XPSource,
)


def test_default_novice():
    s = TelegraphReadingSkill()
    assert s.tier(player_id="alice") == Tier.NOVICE
    assert s.skill(player_id="alice") == 0


def test_award_xp_dodge():
    s = TelegraphReadingSkill()
    gained = s.award_xp(
        player_id="alice", source=XPSource.DODGED_AOE,
    )
    assert gained == 5
    assert s.skill(player_id="alice") == 5


def test_award_xp_interrupt_higher():
    s = TelegraphReadingSkill()
    s.award_xp(player_id="alice", source=XPSource.INTERRUPTED_CAST)
    assert s.skill(player_id="alice") == 10


def test_missed_telegraph_still_grants_xp():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.MISSED_TELEGRAPH,
    )
    assert s.skill(player_id="alice") == 1


def test_xp_caps_at_skill_cap():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=1000,
    )
    assert s.skill(player_id="alice") == SKILL_CAP


def test_blank_player_no_xp():
    s = TelegraphReadingSkill()
    gained = s.award_xp(
        player_id="", source=XPSource.DODGED_AOE,
    )
    assert gained == 0


def test_tier_thresholds():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    # 300 xp → APPRENTICE
    assert s.tier(player_id="alice") == Tier.APPRENTICE
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    # 600 xp → ADEPT
    assert s.tier(player_id="alice") == Tier.ADEPT
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    # 900 xp → EXPERT
    assert s.tier(player_id="alice") == Tier.EXPERT
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    # 1200 xp → MASTER
    assert s.tier(player_id="alice") == Tier.MASTER


def test_warning_bonus_seconds_scales():
    s = TelegraphReadingSkill()
    assert s.warning_bonus_seconds(player_id="alice") == 0.0
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=120,
    )
    # MASTER
    assert s.warning_bonus_seconds(player_id="alice") == 1.6


def test_tag_bonus_pct_scales():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    assert s.tag_bonus_pct(player_id="alice") == 5
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=120,
    )
    assert s.tag_bonus_pct(player_id="alice") == 20


def test_prediction_count_scales():
    s = TelegraphReadingSkill()
    assert s.prediction_count(player_id="alice") == 0
    # push to EXPERT
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=90,
    )
    assert s.prediction_count(player_id="alice") == 1
    # push to MASTER
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=30,
    )
    assert s.prediction_count(player_id="alice") == 2


def test_decay_reduces_skill():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.INTERRUPTED_CAST,
        magnitude=10,
    )
    lost = s.decay(
        player_id="alice", days_since_last_practice=5,
    )
    assert lost == 5
    assert s.skill(player_id="alice") == 95


def test_decay_clamps_at_zero():
    s = TelegraphReadingSkill()
    s.award_xp(
        player_id="alice", source=XPSource.DODGED_AOE,
    )
    lost = s.decay(
        player_id="alice", days_since_last_practice=999,
    )
    assert s.skill(player_id="alice") == 0


def test_decay_unknown_player_zero():
    s = TelegraphReadingSkill()
    lost = s.decay(player_id="ghost", days_since_last_practice=10)
    assert lost == 0


def test_zero_magnitude_no_gain():
    s = TelegraphReadingSkill()
    gained = s.award_xp(
        player_id="alice", source=XPSource.DODGED_AOE,
        magnitude=0,
    )
    assert gained == 0


def test_unknown_player_default_warning_zero():
    s = TelegraphReadingSkill()
    assert s.warning_bonus_seconds(player_id="ghost") == 0.0
    assert s.tag_bonus_pct(player_id="ghost") == 0
    assert s.prediction_count(player_id="ghost") == 0


def test_5_distinct_tiers():
    assert len(list(Tier)) == 5
