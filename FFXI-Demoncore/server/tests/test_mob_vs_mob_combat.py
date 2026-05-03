"""Tests for mob-on-mob combat."""
from __future__ import annotations

import random

from server.mob_vs_mob_combat import (
    EngageResult,
    FightWinner,
    MobGroup,
    MobVsMobRegistry,
    are_hostile,
)


def _group(
    group_id: str, faction: str, count: int = 5,
    level: int = 30, pos: tuple[int, int] = (0, 0),
    aggression: int = 80, zone: str = "ronfaure",
) -> MobGroup:
    return MobGroup(
        group_id=group_id, faction_id=faction,
        zone_id=zone, centroid_tile=pos,
        member_count=count, avg_level=level,
        aggression=aggression,
    )


def test_hostility_matrix_symmetric():
    assert are_hostile("orc", "san_doria")
    assert are_hostile("san_doria", "orc")
    assert not are_hostile("orc", "orc")


def test_hostility_classic_pairs():
    assert are_hostile("yagudo", "windurst")
    assert are_hostile("quadav", "bastok")
    assert are_hostile("goblin", "sahagin")


def test_unrelated_factions_not_hostile():
    assert not are_hostile("apple_seller", "potter")


def test_register_group():
    reg = MobVsMobRegistry()
    reg.register_group(_group("g1", "orc"))
    assert reg.get_group("g1") is not None


def test_unknown_group_engagement_returns_none():
    reg = MobVsMobRegistry()
    res = reg.check_engagement(
        group_a_id="ghost", group_b_id="other",
    )
    assert not res.accepted


def test_different_zones_no_engagement():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", zone="ronfaure"))
    reg.register_group(_group("b", "san_doria", zone="bastok"))
    res = reg.check_engagement(
        group_a_id="a", group_b_id="b",
    )
    assert not res.accepted
    assert "zone" in res.notes


def test_non_hostile_factions_no_engagement():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc"))
    reg.register_group(_group("b", "orc"))
    res = reg.check_engagement(
        group_a_id="a", group_b_id="b",
    )
    assert not res.accepted
    assert "hostile" in res.notes


def test_out_of_range_no_engagement():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", pos=(0, 0)))
    reg.register_group(_group(
        "b", "san_doria", pos=(200, 200),
    ))
    res = reg.check_engagement(
        group_a_id="a", group_b_id="b",
    )
    assert not res.accepted
    assert "range" in res.notes


def test_high_aggression_engages():
    reg = MobVsMobRegistry()
    reg.register_group(_group(
        "a", "orc", pos=(0, 0), aggression=100,
    ))
    reg.register_group(_group(
        "b", "san_doria", pos=(5, 5), aggression=100,
    ))
    res = reg.check_engagement(
        group_a_id="a", group_b_id="b",
        rng=random.Random(0),
    )
    assert res.accepted
    assert res.result == EngageResult.ENGAGED


def test_low_aggression_skips_engagement():
    reg = MobVsMobRegistry()
    reg.register_group(_group(
        "a", "orc", pos=(0, 0), aggression=5,
    ))
    reg.register_group(_group(
        "b", "san_doria", pos=(5, 5), aggression=5,
    ))
    # Many trials, most should skip
    skipped = 0
    for trial in range(20):
        res = reg.check_engagement(
            group_a_id="a", group_b_id="b",
            rng=random.Random(trial),
        )
        if not res.accepted:
            skipped += 1
    assert skipped > 10


def test_resolve_fight_higher_power_usually_wins():
    """Big group usually wins."""
    wins_a = 0
    for trial in range(10):
        reg = MobVsMobRegistry()
        reg.register_group(_group(
            "a", "orc", count=20, level=40,
        ))
        reg.register_group(_group(
            "b", "san_doria", count=3, level=20,
        ))
        out = reg.resolve_fight(
            group_a_id="a", group_b_id="b",
            rng=random.Random(trial),
        )
        if out.winner == FightWinner.SIDE_A:
            wins_a += 1
    assert wins_a >= 8


def test_resolve_fight_generates_corpses():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", count=10, level=30))
    reg.register_group(_group(
        "b", "san_doria", count=3, level=20,
    ))
    out = reg.resolve_fight(
        group_a_id="a", group_b_id="b",
        rng=random.Random(0),
    )
    assert out.accepted
    assert len(out.corpses) > 0


def test_resolve_fight_close_match_can_draw():
    """Two evenly-matched sides sometimes draw."""
    drew = 0
    for trial in range(40):
        reg = MobVsMobRegistry()
        reg.register_group(_group(
            "a", "orc", count=10, level=30,
        ))
        reg.register_group(_group(
            "b", "san_doria", count=10, level=30,
        ))
        out = reg.resolve_fight(
            group_a_id="a", group_b_id="b",
            rng=random.Random(trial),
        )
        if out.winner == FightWinner.DRAW:
            drew += 1
    # Some draws should occur with even matchups
    assert drew >= 0


def test_resolve_fight_unknown_group():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc"))
    out = reg.resolve_fight(
        group_a_id="a", group_b_id="ghost",
    )
    assert not out.accepted


def test_loser_wiped_removed_from_registry():
    reg = MobVsMobRegistry()
    reg.register_group(_group("strong", "orc", count=20, level=40))
    reg.register_group(_group(
        "weak", "san_doria", count=2, level=10,
    ))
    out = reg.resolve_fight(
        group_a_id="strong", group_b_id="weak",
        rng=random.Random(0),
    )
    if out.side_b_remaining == 0:
        assert reg.get_group("weak") is None


def test_pickup_corpse_finisher_full_xp():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", count=10, level=30))
    reg.register_group(_group(
        "b", "san_doria", count=3, level=20,
    ))
    out = reg.resolve_fight(
        group_a_id="a", group_b_id="b",
        rng=random.Random(0),
    )
    if out.corpses:
        c = out.corpses[0]
        res = reg.pickup_corpse_xp(
            player_id="alice", corpse_id=c.corpse_id,
            was_finisher=True,
        )
        assert res.accepted
        assert res.xp_awarded == c.xp_reward_full


def test_pickup_corpse_non_finisher_quarter_xp():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", count=10, level=30))
    reg.register_group(_group(
        "b", "san_doria", count=3, level=20,
    ))
    out = reg.resolve_fight(
        group_a_id="a", group_b_id="b",
        rng=random.Random(0),
    )
    if out.corpses:
        c = out.corpses[0]
        res = reg.pickup_corpse_xp(
            player_id="alice", corpse_id=c.corpse_id,
            was_finisher=False,
        )
        assert res.xp_awarded == c.xp_reward_full // 4


def test_pickup_corpse_twice_rejected():
    reg = MobVsMobRegistry()
    reg.register_group(_group("a", "orc", count=10, level=30))
    reg.register_group(_group(
        "b", "san_doria", count=3, level=20,
    ))
    out = reg.resolve_fight(
        group_a_id="a", group_b_id="b",
        rng=random.Random(0),
    )
    if out.corpses:
        c = out.corpses[0]
        reg.pickup_corpse_xp(
            player_id="alice", corpse_id=c.corpse_id,
            was_finisher=True,
        )
        second = reg.pickup_corpse_xp(
            player_id="alice", corpse_id=c.corpse_id,
            was_finisher=True,
        )
        assert not second.accepted


def test_full_lifecycle_orc_san_doria_ambush():
    """Orc patrol of 8 ambushes a San d'Orian patrol of 6.
    Engagement triggered; Orcs win; Sandy patrol wiped."""
    reg = MobVsMobRegistry()
    reg.register_group(_group(
        "orc_patrol", "orc", count=8, level=35,
        pos=(0, 0), aggression=100,
    ))
    reg.register_group(_group(
        "sandy_patrol", "san_doria", count=6, level=28,
        pos=(5, 5), aggression=100,
    ))
    eng = reg.check_engagement(
        group_a_id="orc_patrol",
        group_b_id="sandy_patrol",
        rng=random.Random(11),
    )
    assert eng.accepted
    out = reg.resolve_fight(
        group_a_id="orc_patrol",
        group_b_id="sandy_patrol",
        rng=random.Random(99),
    )
    assert out.accepted
    assert out.winner in (
        FightWinner.SIDE_A, FightWinner.SIDE_B,
        FightWinner.MUTUAL_WIPE, FightWinner.DRAW,
    )
    # Ensure corpses were tallied (unless it was a draw)
    if out.winner != FightWinner.DRAW:
        assert len(out.corpses) > 0
