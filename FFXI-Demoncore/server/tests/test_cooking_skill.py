"""Tests for cooking_skill."""
from __future__ import annotations

from server.cooking_skill import (
    CookingSkillRegistry, CookOutcome, SkillRank,
)


def test_grant_baseline_happy():
    r = CookingSkillRegistry()
    assert r.grant_baseline(player_id="alice") is True
    assert r.skill_of(player_id="alice") == 0


def test_grant_baseline_blank_blocked():
    r = CookingSkillRegistry()
    assert r.grant_baseline(player_id="") is False


def test_grant_baseline_duplicate_blocked():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    assert r.grant_baseline(player_id="alice") is False


def test_skill_of_unknown_zero():
    r = CookingSkillRegistry()
    assert r.skill_of(player_id="ghost") == 0


def test_rank_none_at_zero():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    assert r.rank_of(player_id="alice") == SkillRank.NONE


def test_rank_progression():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=5)
    assert r.rank_of(player_id="alice") == SkillRank.NOVICE
    r.add_xp(player_id="alice", amount=20)
    assert r.rank_of(player_id="alice") == SkillRank.JOURNEYMAN
    r.add_xp(player_id="alice", amount=30)
    assert r.rank_of(player_id="alice") == SkillRank.ARTISAN
    r.add_xp(player_id="alice", amount=30)
    assert r.rank_of(player_id="alice") == SkillRank.MASTER


def test_can_attempt_at_threshold():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=20)
    assert r.can_attempt(
        player_id="alice", min_skill_required=20,
    ) is True
    assert r.can_attempt(
        player_id="alice", min_skill_required=21,
    ) is False


def test_attempt_below_min_skill_fails():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=10,
        min_skill_required=50, roll_pct=99,
    )
    assert out.outcome == CookOutcome.FAILED
    assert out.skill_xp_gained == 0


def test_high_margin_never_fails():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=80)
    # difficulty 10, skill 80 → margin 70, roll 0 should still pass
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=10,
        min_skill_required=0, roll_pct=0,
    )
    assert out.outcome != CookOutcome.FAILED


def test_negative_margin_can_fail():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=10)
    # difficulty 50, skill 10 → margin -40, fail_threshold = 5 + 60 = 65
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=50,
        min_skill_required=0, roll_pct=30,
    )
    assert out.outcome == CookOutcome.FAILED


def test_basic_outcome_default():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=50)
    # margin 50, low roll → success but BASIC
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=0,
        min_skill_required=0, roll_pct=50,
    )
    assert out.outcome == CookOutcome.BASIC


def test_good_outcome_at_high_roll():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=50)
    # margin 40 (>=10), roll 85 (>=80) → GOOD
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=10,
        min_skill_required=0, roll_pct=85,
    )
    assert out.outcome == CookOutcome.GOOD


def test_hq_outcome_at_perfect_roll():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=50)
    # margin 30 (>=20), roll 96 (>=95) → HQ
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=20,
        min_skill_required=0, roll_pct=96,
    )
    assert out.outcome == CookOutcome.HQ


def test_xp_grows_more_on_hard_recipes():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=20)
    # cook above your level → margin negative → +5 xp
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=30,
        min_skill_required=0, roll_pct=99,
    )
    assert out.skill_xp_gained == 5


def test_xp_grows_less_on_easy_recipes():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=80)
    # margin 70 → trivial → 1 xp
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=10,
        min_skill_required=0, roll_pct=50,
    )
    assert out.skill_xp_gained == 1


def test_xp_caps_at_100():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    new = r.add_xp(player_id="alice", amount=999)
    assert new == 100


def test_no_xp_at_max_skill():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.add_xp(player_id="alice", amount=100)
    out = r.resolve_attempt(
        player_id="alice", recipe_difficulty=10,
        min_skill_required=0, roll_pct=50,
    )
    assert out.skill_xp_gained == 0


def test_add_xp_zero_no_op():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    new = r.add_xp(player_id="alice", amount=0)
    assert new == 0


def test_add_xp_blank_player():
    r = CookingSkillRegistry()
    new = r.add_xp(player_id="", amount=10)
    assert new == 0


def test_five_skill_ranks():
    assert len(list(SkillRank)) == 5


def test_four_cook_outcomes():
    assert len(list(CookOutcome)) == 4


def test_total_known_players():
    r = CookingSkillRegistry()
    r.grant_baseline(player_id="alice")
    r.grant_baseline(player_id="bob")
    assert r.total_known_players() == 2
