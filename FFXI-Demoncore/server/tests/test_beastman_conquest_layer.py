"""Tests for the beastman conquest layer."""
from __future__ import annotations

from server.beastman_conquest_layer import (
    BeastmanConquestLayer,
)
from server.beastman_playable_races import BeastmanRace


def test_record_kill():
    c = BeastmanConquestLayer()
    assert c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=100,
    )


def test_record_kill_zero_rejected():
    c = BeastmanConquestLayer()
    assert not c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=0,
    )


def test_record_kill_empty_nation_rejected():
    c = BeastmanConquestLayer()
    assert not c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="",
        points=100,
    )


def test_kill_credits_main_race():
    c = BeastmanConquestLayer()
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=100,
    )
    assert c.points_for(
        week_index=1, race=BeastmanRace.ORC,
    ) == 100


def test_kill_cross_faction_share():
    c = BeastmanConquestLayer(cross_share_pct=20)
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=100,
    )
    # Quadav is allied with Orc → gets 20%
    assert c.points_for(
        week_index=1, race=BeastmanRace.QUADAV,
    ) == 20


def test_yagudo_lamia_allied_share():
    c = BeastmanConquestLayer(cross_share_pct=20)
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.YAGUDO,
        victim_nation="windurst",
        points=100,
    )
    assert c.points_for(
        week_index=1, race=BeastmanRace.YAGUDO,
    ) == 100
    assert c.points_for(
        week_index=1, race=BeastmanRace.LAMIA,
    ) == 20


def test_no_cross_share_to_unrelated():
    c = BeastmanConquestLayer(cross_share_pct=20)
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=100,
    )
    assert c.points_for(
        week_index=1, race=BeastmanRace.YAGUDO,
    ) == 0


def test_record_objective():
    c = BeastmanConquestLayer()
    assert c.record_objective(
        week_index=1, race=BeastmanRace.LAMIA,
        points=50, label="held the cove",
    )
    assert c.points_for(
        week_index=1, race=BeastmanRace.LAMIA,
    ) == 50


def test_record_objective_zero_rejected():
    c = BeastmanConquestLayer()
    assert not c.record_objective(
        week_index=1, race=BeastmanRace.LAMIA,
        points=0,
    )


def test_standings_sorted_descending():
    c = BeastmanConquestLayer()
    c.record_objective(
        week_index=1, race=BeastmanRace.YAGUDO,
        points=300,
    )
    c.record_objective(
        week_index=1, race=BeastmanRace.ORC,
        points=100,
    )
    standings = c.standings_for_week(week_index=1)
    assert standings[0].race == BeastmanRace.YAGUDO
    assert standings[0].rank == 1


def test_standings_includes_all_races():
    c = BeastmanConquestLayer()
    standings = c.standings_for_week(week_index=99)
    races = {s.race for s in standings}
    assert races == set(BeastmanRace)


def test_leader_clear_winner():
    c = BeastmanConquestLayer()
    c.record_objective(
        week_index=1, race=BeastmanRace.ORC,
        points=500,
    )
    c.record_objective(
        week_index=1, race=BeastmanRace.YAGUDO,
        points=100,
    )
    leader = c.leader_for_week(week_index=1)
    assert leader == BeastmanRace.ORC


def test_leader_tied_returns_none():
    c = BeastmanConquestLayer()
    c.record_objective(
        week_index=1, race=BeastmanRace.ORC,
        points=200,
    )
    c.record_objective(
        week_index=1, race=BeastmanRace.YAGUDO,
        points=200,
    )
    leader = c.leader_for_week(week_index=1)
    assert leader is None


def test_leader_no_kills_returns_none():
    c = BeastmanConquestLayer()
    leader = c.leader_for_week(week_index=1)
    assert leader is None


def test_reset_week_clears_only_that_week():
    c = BeastmanConquestLayer()
    c.record_objective(
        week_index=1, race=BeastmanRace.ORC,
        points=100,
    )
    c.record_objective(
        week_index=2, race=BeastmanRace.ORC,
        points=200,
    )
    cleared = c.reset_week(week_index=1)
    assert cleared == 1
    assert c.points_for(
        week_index=2, race=BeastmanRace.ORC,
    ) == 200


def test_reset_week_no_data():
    c = BeastmanConquestLayer()
    cleared = c.reset_week(week_index=99)
    assert cleared == 0


def test_kill_low_points_no_share():
    c = BeastmanConquestLayer(cross_share_pct=20)
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=4,
    )
    # 4 * 20% = 0 (integer)
    assert c.points_for(
        week_index=1, race=BeastmanRace.QUADAV,
    ) == 0


def test_repeated_kills_accumulate():
    c = BeastmanConquestLayer()
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=50,
    )
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=70,
    )
    assert c.points_for(
        week_index=1, race=BeastmanRace.ORC,
    ) == 120


def test_total_entries():
    c = BeastmanConquestLayer()
    c.record_kill(
        week_index=1,
        killer_race=BeastmanRace.ORC,
        victim_nation="san_doria",
        points=100,
    )
    # Orc + Quadav cross-share = 2 entries
    assert c.total_entries() == 2


def test_per_week_isolation():
    c = BeastmanConquestLayer()
    c.record_objective(
        week_index=1, race=BeastmanRace.ORC,
        points=100,
    )
    standings_w2 = c.standings_for_week(week_index=2)
    # All zero in week 2
    assert all(s.points == 0 for s in standings_w2)
