"""Tests for the beastman arena circuit."""
from __future__ import annotations

from server.beastman_arena_circuit import (
    ArenaCity,
    BeastmanArenaCircuit,
    BoutOutcome,
    SeasonState,
    WeightClass,
)


def _seed(c):
    c.open_season(
        season_id="oz_s1",
        city=ArenaCity.OZTROJA,
        weight_class=WeightClass.MEDIUM,
        length_days=30,
        now_seconds=0,
    )
    c.register(player_id="kraw", season_id="oz_s1")
    c.register(player_id="zlar", season_id="oz_s1")


def test_open_season():
    c = BeastmanArenaCircuit()
    _seed(c)
    assert c.total_seasons() == 1


def test_open_season_duplicate():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.open_season(
        season_id="oz_s1",
        city=ArenaCity.OZTROJA,
        weight_class=WeightClass.LIGHT,
        length_days=30,
        now_seconds=0,
    )
    assert res is None


def test_open_season_zero_length():
    c = BeastmanArenaCircuit()
    res = c.open_season(
        season_id="bad",
        city=ArenaCity.OZTROJA,
        weight_class=WeightClass.LIGHT,
        length_days=0,
        now_seconds=0,
    )
    assert res is None


def test_register():
    c = BeastmanArenaCircuit()
    _seed(c)
    assert c.standing_for(
        player_id="kraw", season_id="oz_s1",
    ).points == 0


def test_register_double_rejected():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.register(player_id="kraw", season_id="oz_s1")
    assert not res


def test_register_unknown_season():
    c = BeastmanArenaCircuit()
    res = c.register(player_id="x", season_id="ghost")
    assert not res


def test_record_bout_win():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.WIN,
    )
    assert res.accepted
    assert res.attacker_points == 3
    assert res.defender_points == 0


def test_record_bout_draw():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.DRAW,
    )
    assert res.attacker_points == 1
    assert res.defender_points == 1


def test_record_bout_forfeit():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.FORFEIT,
    )
    assert res.attacker_points == 3
    assert res.defender_points == 0  # clamped at 0


def test_record_bout_same_combatant():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="kraw",
        outcome=BoutOutcome.WIN,
    )
    assert not res.accepted


def test_record_bout_unregistered():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="ghost",
        defender_id="kraw",
        outcome=BoutOutcome.WIN,
    )
    assert not res.accepted


def test_record_bout_after_close():
    c = BeastmanArenaCircuit()
    _seed(c)
    c.close_season(season_id="oz_s1", now_seconds=100)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.WIN,
    )
    assert not res.accepted


def test_standing_unknown():
    c = BeastmanArenaCircuit()
    _seed(c)
    assert c.standing_for(
        player_id="ghost", season_id="oz_s1",
    ) is None


def test_standing_bouts_played():
    c = BeastmanArenaCircuit()
    _seed(c)
    c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.WIN,
    )
    s = c.standing_for(
        player_id="kraw", season_id="oz_s1",
    )
    assert s.bouts_played == 1


def test_top_three_ordering():
    c = BeastmanArenaCircuit()
    c.open_season(
        season_id="s",
        city=ArenaCity.HALVUNG,
        weight_class=WeightClass.HEAVY,
        length_days=30,
        now_seconds=0,
    )
    for p in ("a", "b", "c", "d"):
        c.register(player_id=p, season_id="s")
    # a beats b and c; d beats a once; c draws d
    c.record_bout(
        season_id="s",
        attacker_id="a", defender_id="b",
        outcome=BoutOutcome.WIN,
    )
    c.record_bout(
        season_id="s",
        attacker_id="a", defender_id="c",
        outcome=BoutOutcome.WIN,
    )
    c.record_bout(
        season_id="s",
        attacker_id="d", defender_id="a",
        outcome=BoutOutcome.WIN,
    )
    c.record_bout(
        season_id="s",
        attacker_id="c", defender_id="d",
        outcome=BoutOutcome.DRAW,
    )
    top = c.top_three(season_id="s")
    # a: 6, d: 4, c: 1, b: 0
    assert top[0][0] == "a"
    assert top[0][1] == 6
    assert top[1][0] == "d"
    assert top[2][0] == "c"


def test_close_season():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.close_season(season_id="oz_s1", now_seconds=100)
    assert res
    res2 = c.close_season(season_id="oz_s1", now_seconds=200)
    assert not res2


def test_register_after_close():
    c = BeastmanArenaCircuit()
    _seed(c)
    c.close_season(season_id="oz_s1", now_seconds=100)
    res = c.register(player_id="newcomer", season_id="oz_s1")
    assert not res


def test_top_three_unknown_season():
    c = BeastmanArenaCircuit()
    assert c.top_three(season_id="ghost") == []


def test_record_bout_unknown_season():
    c = BeastmanArenaCircuit()
    res = c.record_bout(
        season_id="ghost",
        attacker_id="a", defender_id="b",
        outcome=BoutOutcome.WIN,
    )
    assert not res.accepted


def test_loss_outcome_credits_defender():
    c = BeastmanArenaCircuit()
    _seed(c)
    res = c.record_bout(
        season_id="oz_s1",
        attacker_id="kraw",
        defender_id="zlar",
        outcome=BoutOutcome.LOSS,
    )
    assert res.attacker_points == 0
    assert res.defender_points == 3
