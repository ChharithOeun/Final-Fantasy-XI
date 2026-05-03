"""Tests for AI quest curator."""
from __future__ import annotations

from server.ai_quest_curator import (
    AIQuestCurator,
    PlayerProfile,
    QuestCard,
    QuestKind,
)


def _card(
    *, quest_id="q1", title="A quest",
    kind=QuestKind.AUTHORED,
    level=10, faction=None, min_rep=0,
    zone=None, tags=(), giver=None,
    revenge=False, target_player=None,
    base=50,
) -> QuestCard:
    return QuestCard(
        quest_id=quest_id, title=title, kind=kind,
        suggested_level=level, faction_id=faction,
        min_faction_rep=min_rep, zone_id=zone,
        tags=tags, npc_giver_id=giver,
        is_revenge_arc=revenge,
        target_player_id=target_player,
        base_score=base,
    )


def test_empty_curator_yields_nothing():
    cur = AIQuestCurator()
    res = cur.curate(player=PlayerProfile(player_id="alice"))
    assert res == ()


def test_add_card_then_curate():
    cur = AIQuestCurator()
    cur.add_card(_card())
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    assert len(res) == 1
    assert res[0].quest_id == "q1"


def test_double_add_rejected():
    cur = AIQuestCurator()
    assert cur.add_card(_card())
    assert not cur.add_card(_card())


def test_remove_card():
    cur = AIQuestCurator()
    cur.add_card(_card())
    assert cur.remove_card("q1")
    assert not cur.remove_card("q1")


def test_level_proximity_higher_score():
    cur = AIQuestCurator()
    cur.add_card(_card(quest_id="near", level=10))
    cur.add_card(_card(quest_id="far", level=50))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    # near should outrank far
    assert res[0].quest_id == "near"


def test_faction_rep_gate_blocks():
    cur = AIQuestCurator()
    cur.add_card(_card(
        quest_id="gated", faction="san_doria", min_rep=100,
    ))
    res = cur.curate(
        player=PlayerProfile(
            player_id="alice", level=10,
            faction_reputations={"san_doria": 0},
        ),
    )
    # Score gets the -50 penalty but might still surface
    # at low score. base 50 + level bonus 20 - 50 = 20
    # Still positive but lower than passing player would get
    cur.add_card(_card(
        quest_id="passing", faction="bastok", min_rep=10,
    ))
    res2 = cur.curate(
        player=PlayerProfile(
            player_id="alice", level=10,
            faction_reputations={
                "san_doria": 0, "bastok": 50,
            },
        ),
    )
    bastok_score = next(
        r.score for r in res2 if r.quest_id == "passing"
    )
    sandoria_score = next(
        r.score for r in res2 if r.quest_id == "gated"
    )
    assert bastok_score > sandoria_score


def test_zone_proximity_bonus():
    cur = AIQuestCurator()
    cur.add_card(_card(quest_id="here", zone="bastok_mines"))
    cur.add_card(_card(quest_id="there", zone="windurst_walls"))
    res = cur.curate(
        player=PlayerProfile(
            player_id="alice", level=10,
            current_zone_id="bastok_mines",
        ),
    )
    assert res[0].quest_id == "here"


def test_tag_affinity_bonus():
    cur = AIQuestCurator()
    cur.add_card(_card(
        quest_id="combat", tags=("combat", "kill"),
    ))
    cur.add_card(_card(quest_id="craft", tags=("craft",)))
    res = cur.curate(
        player=PlayerProfile(
            player_id="alice", level=10,
            completed_tags={"combat": 5, "kill": 3},
        ),
    )
    # combat should outrank craft
    assert res[0].quest_id == "combat"


def test_mood_preference_bonus():
    cur = AIQuestCurator()
    cur.add_card(_card(quest_id="combat", tags=("combat",)))
    cur.add_card(_card(quest_id="craft", tags=("craft",)))
    res = cur.curate(
        player=PlayerProfile(
            player_id="alice", level=10,
            mood_preference="craft",
        ),
    )
    assert res[0].quest_id == "craft"


def test_revenge_arc_for_target_player_only():
    cur = AIQuestCurator()
    cur.add_card(_card(
        quest_id="revenge", revenge=True,
        target_player="alice",
    ))
    # alice should see it
    res_a = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    assert len(res_a) == 1
    # bob should not
    res_b = cur.curate(
        player=PlayerProfile(player_id="bob", level=10),
    )
    assert res_b == ()


def test_max_results_cap():
    cur = AIQuestCurator(max_visible_quests=3)
    for i in range(10):
        cur.add_card(_card(
            quest_id=f"q_{i}", level=10,
        ))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    assert len(res) == 3


def test_custom_max_results_overrides():
    cur = AIQuestCurator(max_visible_quests=10)
    for i in range(10):
        cur.add_card(_card(
            quest_id=f"q_{i}", level=10,
        ))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
        max_results=2,
    )
    assert len(res) == 2


def test_zero_score_skipped():
    """A revenge arc for a different player has score 0;
    should not surface."""
    cur = AIQuestCurator()
    cur.add_card(_card(
        quest_id="not_for_alice", revenge=True,
        target_player="bob",
    ))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    assert res == ()


def test_total_cards_count():
    cur = AIQuestCurator()
    cur.add_card(_card(quest_id="a"))
    cur.add_card(_card(quest_id="b"))
    assert cur.total_cards() == 2


def test_far_level_quest_penalized():
    cur = AIQuestCurator()
    cur.add_card(_card(quest_id="elite", level=70))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    # Should still surface but with low score: 50 - 40 = 10
    assert res[0].score == 10


def test_daily_task_gets_small_bias():
    cur = AIQuestCurator()
    cur.add_card(_card(
        quest_id="daily", kind=QuestKind.DAILY_TASK,
    ))
    cur.add_card(_card(
        quest_id="authored", kind=QuestKind.AUTHORED,
    ))
    res = cur.curate(
        player=PlayerProfile(player_id="alice", level=10),
    )
    assert res[0].quest_id == "daily"
