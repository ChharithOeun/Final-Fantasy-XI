"""Tests for player_cooking_competition."""
from __future__ import annotations

from server.player_cooking_competition import (
    PlayerCookingCompetitionSystem, CompState,
)


def _announce(
    s: PlayerCookingCompetitionSystem,
    purse: int = 1000,
) -> str:
    return s.announce(
        organizer_id="naji",
        name="Sunbreeze Bake-off", purse_gil=purse,
    )


def _ready_to_judge(
    s: PlayerCookingCompetitionSystem,
    contestants: int = 3, judges: int = 2,
) -> str:
    cid = _announce(s)
    for i in range(contestants):
        s.enter_contestant(
            competition_id=cid,
            contestant_id=f"chef_{i}",
            dish_name=f"dish_{i}",
        )
    for i in range(judges):
        s.add_judge(
            competition_id=cid,
            judge_id=f"judge_{i}",
        )
    s.begin_judging(
        competition_id=cid, organizer_id="naji",
    )
    return cid


def test_announce_happy():
    s = PlayerCookingCompetitionSystem()
    assert _announce(s) is not None


def test_announce_zero_purse_blocked():
    s = PlayerCookingCompetitionSystem()
    assert _announce(s, purse=0) is None


def test_add_judge_happy():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    assert s.add_judge(
        competition_id=cid, judge_id="bob",
    ) is True


def test_add_judge_organizer_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    assert s.add_judge(
        competition_id=cid, judge_id="naji",
    ) is False


def test_add_judge_dup_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    s.add_judge(
        competition_id=cid, judge_id="bob",
    )
    assert s.add_judge(
        competition_id=cid, judge_id="bob",
    ) is False


def test_add_judge_cap_reached():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    for i in range(5):
        s.add_judge(
            competition_id=cid, judge_id=f"j_{i}",
        )
    assert s.add_judge(
        competition_id=cid, judge_id="overflow",
    ) is False


def test_enter_contestant_happy():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    assert s.enter_contestant(
        competition_id=cid, contestant_id="bob",
        dish_name="Bouillabaisse",
    ) is True


def test_enter_contestant_organizer_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    assert s.enter_contestant(
        competition_id=cid, contestant_id="naji",
        dish_name="x",
    ) is False


def test_enter_contestant_dup_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    s.enter_contestant(
        competition_id=cid, contestant_id="bob",
        dish_name="x",
    )
    assert s.enter_contestant(
        competition_id=cid, contestant_id="bob",
        dish_name="y",
    ) is False


def test_judge_cant_be_contestant():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    s.add_judge(
        competition_id=cid, judge_id="bob",
    )
    assert s.enter_contestant(
        competition_id=cid, contestant_id="bob",
        dish_name="x",
    ) is False


def test_begin_judging_happy():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    s.enter_contestant(
        competition_id=cid, contestant_id="a",
        dish_name="x",
    )
    s.enter_contestant(
        competition_id=cid, contestant_id="b",
        dish_name="y",
    )
    s.add_judge(
        competition_id=cid, judge_id="j",
    )
    assert s.begin_judging(
        competition_id=cid, organizer_id="naji",
    ) is True
    assert s.competition(
        competition_id=cid,
    ).state == CompState.JUDGING


def test_begin_judging_too_few_contestants():
    s = PlayerCookingCompetitionSystem()
    cid = _announce(s)
    s.enter_contestant(
        competition_id=cid, contestant_id="a",
        dish_name="x",
    )
    s.add_judge(
        competition_id=cid, judge_id="j",
    )
    assert s.begin_judging(
        competition_id=cid, organizer_id="naji",
    ) is False


def test_enter_contestant_after_judging_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert s.enter_contestant(
        competition_id=cid, contestant_id="late",
        dish_name="x",
    ) is False


def test_submit_score_happy():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert s.submit_score(
        competition_id=cid, judge_id="judge_0",
        contestant_id="chef_0", score=8,
    ) is True


def test_submit_score_non_judge_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert s.submit_score(
        competition_id=cid, judge_id="stranger",
        contestant_id="chef_0", score=8,
    ) is False


def test_submit_score_invalid_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert s.submit_score(
        competition_id=cid, judge_id="judge_0",
        contestant_id="chef_0", score=20,
    ) is False


def test_submit_score_double_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    s.submit_score(
        competition_id=cid, judge_id="judge_0",
        contestant_id="chef_0", score=8,
    )
    assert s.submit_score(
        competition_id=cid, judge_id="judge_0",
        contestant_id="chef_0", score=5,
    ) is False


def test_resolve_happy_returns_payouts():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    # chef_0 = 8+8 = 16, chef_1 = 5+5 = 10,
    # chef_2 = 2+2 = 4
    for j in range(2):
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_0", score=8,
        )
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_1", score=5,
        )
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_2", score=2,
        )
    payouts = s.resolve(
        competition_id=cid, organizer_id="naji",
    )
    # 1000 purse: 600/300/100
    assert payouts == {
        "chef_0": 600, "chef_1": 300, "chef_2": 100,
    }


def test_resolve_incomplete_scores_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    s.submit_score(
        competition_id=cid, judge_id="judge_0",
        contestant_id="chef_0", score=8,
    )
    assert s.resolve(
        competition_id=cid, organizer_id="naji",
    ) is None


def test_resolve_winner_recorded():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    for j in range(2):
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_0", score=10,
        )
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_1", score=5,
        )
        s.submit_score(
            competition_id=cid,
            judge_id=f"judge_{j}",
            contestant_id="chef_2", score=2,
        )
    s.resolve(
        competition_id=cid, organizer_id="naji",
    )
    assert s.competition(
        competition_id=cid,
    ).winner_id == "chef_0"


def test_contestants_listing():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert len(s.contestants(
        competition_id=cid,
    )) == 3


def test_judges_listing():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    assert len(s.judges(competition_id=cid)) == 2


def test_resolve_wrong_organizer_blocked():
    s = PlayerCookingCompetitionSystem()
    cid = _ready_to_judge(s)
    for j in range(2):
        for c in range(3):
            s.submit_score(
                competition_id=cid,
                judge_id=f"judge_{j}",
                contestant_id=f"chef_{c}", score=5,
            )
    assert s.resolve(
        competition_id=cid, organizer_id="bob",
    ) is None


def test_unknown_competition():
    s = PlayerCookingCompetitionSystem()
    assert s.competition(
        competition_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(CompState)) == 3
