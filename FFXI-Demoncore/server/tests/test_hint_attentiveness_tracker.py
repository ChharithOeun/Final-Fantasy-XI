"""Tests for hint_attentiveness_tracker."""
from __future__ import annotations

from server.hint_attentiveness_tracker import (
    AttentivenessLevel,
    HintAttentivenessTracker,
)


def test_new_player_oblivious():
    t = HintAttentivenessTracker()
    assert t.level(player_id="p1") == AttentivenessLevel.OBLIVIOUS
    assert t.score(player_id="p1") == 0


def test_msq_chapter_award():
    t = HintAttentivenessTracker()
    assert t.award_msq_chapter(player_id="p1", chapter=1) is True
    assert t.score(player_id="p1") == 10


def test_dup_msq_blocked():
    t = HintAttentivenessTracker()
    t.award_msq_chapter(player_id="p1", chapter=1)
    assert t.award_msq_chapter(player_id="p1", chapter=1) is False


def test_side_quest_award():
    t = HintAttentivenessTracker()
    t.award_side_quest(player_id="p1", quest_id="sq1")
    assert t.score(player_id="p1") == 3


def test_zone_npc_bestiary():
    t = HintAttentivenessTracker()
    t.award_zone_discovered(player_id="p1", zone_id="bastok")
    t.award_npc_talked(player_id="p1", npc_id="ayame")
    t.award_bestiary(player_id="p1", species_id="bee")
    assert t.score(player_id="p1") == 4


def test_observant_threshold():
    t = HintAttentivenessTracker()
    # 5 MSQ chapters = 50 score → OBSERVANT
    for ch in range(1, 6):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    assert t.level(player_id="p1") == AttentivenessLevel.OBSERVANT


def test_perceptive_threshold():
    t = HintAttentivenessTracker()
    for ch in range(1, 13):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    assert t.level(player_id="p1") == AttentivenessLevel.PERCEPTIVE


def test_attuned_threshold():
    t = HintAttentivenessTracker()
    for ch in range(1, 21):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    assert t.level(player_id="p1") == AttentivenessLevel.ATTUNED


def test_enlightened_threshold():
    t = HintAttentivenessTracker()
    for ch in range(1, 31):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    assert t.level(player_id="p1") == AttentivenessLevel.ENLIGHTENED


def test_can_see_oblivious_blocks_subtle_hint():
    t = HintAttentivenessTracker()
    assert t.can_see(player_id="p1", subtlety=5) is False


def test_can_see_observant_sees_easy():
    t = HintAttentivenessTracker()
    for ch in range(1, 6):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    assert t.can_see(player_id="p1", subtlety=4) is True
    assert t.can_see(player_id="p1", subtlety=5) is False


def test_can_see_enlightened_sees_all():
    t = HintAttentivenessTracker()
    for ch in range(1, 31):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    for q in range(20):
        t.award_side_quest(player_id="p1", quest_id=f"sq{q}")
    assert t.can_see(player_id="p1", subtlety=10) is True


def test_can_see_msq_gate_blocks():
    t = HintAttentivenessTracker()
    # ENLIGHTENED but only chapter 1 MSQ
    t.award_msq_chapter(player_id="p1", chapter=1)
    for q in range(100):
        t.award_side_quest(player_id="p1", quest_id=f"sq{q}")
    # required chapter 5 — blocks
    assert t.can_see(
        player_id="p1", subtlety=2, required_msq_chapter=5,
    ) is False


def test_can_see_side_quest_gate():
    t = HintAttentivenessTracker()
    for ch in range(1, 31):
        t.award_msq_chapter(player_id="p1", chapter=ch)
    # 0 side quests
    assert t.can_see(
        player_id="p1", subtlety=2, required_side_quests=10,
    ) is False
    for q in range(15):
        t.award_side_quest(player_id="p1", quest_id=f"sq{q}")
    assert t.can_see(
        player_id="p1", subtlety=2, required_side_quests=10,
    ) is True


def test_blank_player_blocked():
    t = HintAttentivenessTracker()
    assert t.award_msq_chapter(player_id="", chapter=1) is False


def test_invalid_chapter_blocked():
    t = HintAttentivenessTracker()
    assert t.award_msq_chapter(player_id="p1", chapter=0) is False


def test_completion_counters():
    t = HintAttentivenessTracker()
    t.award_msq_chapter(player_id="p1", chapter=3)
    t.award_side_quest(player_id="p1", quest_id="q")
    t.award_side_quest(player_id="p1", quest_id="q2")
    assert t.msq_chapters_completed(player_id="p1") == 1
    assert t.side_quests_completed(player_id="p1") == 2


def test_score_aggregates_across_signals():
    t = HintAttentivenessTracker()
    t.award_msq_chapter(player_id="p1", chapter=1)  # 10
    t.award_side_quest(player_id="p1", quest_id="q1")  # 3
    t.award_cutscene_watched(player_id="p1", cutscene_id="c1")  # 2
    t.award_zone_discovered(player_id="p1", zone_id="z1")  # 2
    t.award_npc_talked(player_id="p1", npc_id="n1")  # 1
    t.award_bestiary(player_id="p1", species_id="bee")  # 1
    assert t.score(player_id="p1") == 19
