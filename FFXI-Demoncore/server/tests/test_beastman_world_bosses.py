"""Tests for the beastman world bosses."""
from __future__ import annotations

from server.beastman_world_bosses import (
    BeastmanWorldBosses,
    BossState,
    BossTier,
)


def _seed(b):
    b.register_boss(
        boss_id="abyss_titan",
        tier=BossTier.T2,
        zone_id="shadow_abyss",
        alliance_min=6,
        window_hours=2,
        cooldown_hours=24,
        level_required=99,
    )


def test_register_boss():
    b = BeastmanWorldBosses()
    _seed(b)
    assert b.total_bosses() == 1


def test_register_boss_duplicate():
    b = BeastmanWorldBosses()
    _seed(b)
    res = b.register_boss(
        boss_id="abyss_titan",
        tier=BossTier.T1,
        zone_id="other",
        alliance_min=6,
        window_hours=2,
        cooldown_hours=24,
        level_required=99,
    )
    assert res is None


def test_register_boss_zero_alliance():
    b = BeastmanWorldBosses()
    res = b.register_boss(
        boss_id="bad",
        tier=BossTier.T1,
        zone_id="z",
        alliance_min=0,
        window_hours=2,
        cooldown_hours=24,
        level_required=99,
    )
    assert res is None


def test_register_boss_out_of_range_level():
    b = BeastmanWorldBosses()
    res = b.register_boss(
        boss_id="bad",
        tier=BossTier.T1,
        zone_id="z",
        alliance_min=6,
        window_hours=2,
        cooldown_hours=24,
        level_required=999,
    )
    assert res is None


def test_open_window():
    b = BeastmanWorldBosses()
    _seed(b)
    assert b.open_window(boss_id="abyss_titan", now_seconds=0)
    assert b.state_for(
        boss_id="abyss_titan", now_seconds=0,
    ) == BossState.WINDOW_OPEN


def test_open_window_unknown():
    b = BeastmanWorldBosses()
    assert not b.open_window(boss_id="ghost", now_seconds=0)


def test_engage_basic():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    res = b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    assert res.accepted
    assert res.state == BossState.ENGAGED


def test_engage_alliance_too_small():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    res = b.engage(
        boss_id="abyss_titan",
        alliance_size=3,
        level_min=99,
        now_seconds=10,
    )
    assert not res.accepted


def test_engage_under_level():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    res = b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=50,
        now_seconds=10,
    )
    assert not res.accepted


def test_engage_window_closed():
    b = BeastmanWorldBosses()
    _seed(b)
    res = b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    assert not res.accepted


def test_engage_window_expired():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    res = b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10_000,  # > 2hr
    )
    assert not res.accepted


def test_record_kill_basic():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    res = b.record_kill(
        boss_id="abyss_titan",
        killers=("a", "b", "c", "d", "e", "f"),
        now_seconds=600,
    )
    assert res.accepted
    assert res.state == BossState.COOLDOWN
    assert res.kill_count == 1


def test_record_kill_not_engaged():
    b = BeastmanWorldBosses()
    _seed(b)
    res = b.record_kill(
        boss_id="abyss_titan",
        killers=("a",) * 6,
        now_seconds=0,
    )
    assert not res.accepted


def test_record_kill_too_few_killers():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    res = b.record_kill(
        boss_id="abyss_titan",
        killers=("a", "b"),
        now_seconds=600,
    )
    assert not res.accepted


def test_claim_shard_basic():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    b.record_kill(
        boss_id="abyss_titan",
        killers=("kraw", "b", "c", "d", "e", "f"),
        now_seconds=600,
    )
    res = b.claim_shard(
        player_id="kraw", boss_id="abyss_titan",
    )
    assert res.accepted
    assert res.shard_id.endswith("_k1")


def test_claim_shard_double_blocked():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    b.record_kill(
        boss_id="abyss_titan",
        killers=("kraw", "b", "c", "d", "e", "f"),
        now_seconds=600,
    )
    b.claim_shard(player_id="kraw", boss_id="abyss_titan")
    res = b.claim_shard(player_id="kraw", boss_id="abyss_titan")
    assert not res.accepted


def test_claim_shard_not_killer():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    b.record_kill(
        boss_id="abyss_titan",
        killers=("kraw", "b", "c", "d", "e", "f"),
        now_seconds=600,
    )
    res = b.claim_shard(
        player_id="not_in_party", boss_id="abyss_titan",
    )
    assert not res.accepted


def test_claim_shard_no_kill():
    b = BeastmanWorldBosses()
    _seed(b)
    res = b.claim_shard(
        player_id="kraw", boss_id="abyss_titan",
    )
    assert not res.accepted


def test_state_for_cooldown_then_dormant():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    b.record_kill(
        boss_id="abyss_titan",
        killers=("a",) * 6,
        now_seconds=600,
    )
    # 24hr cooldown — well within
    assert b.state_for(
        boss_id="abyss_titan", now_seconds=12 * 3600,
    ) == BossState.COOLDOWN
    # past cooldown
    assert b.state_for(
        boss_id="abyss_titan", now_seconds=600 + 24 * 3600 + 1,
    ) == BossState.DORMANT


def test_state_for_window_expires_to_dormant():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    s = b.state_for(
        boss_id="abyss_titan", now_seconds=3 * 3600,
    )
    assert s == BossState.DORMANT


def test_open_window_blocked_during_cooldown():
    b = BeastmanWorldBosses()
    _seed(b)
    b.open_window(boss_id="abyss_titan", now_seconds=0)
    b.engage(
        boss_id="abyss_titan",
        alliance_size=6,
        level_min=99,
        now_seconds=10,
    )
    b.record_kill(
        boss_id="abyss_titan",
        killers=("a",) * 6,
        now_seconds=600,
    )
    res = b.open_window(boss_id="abyss_titan", now_seconds=1000)
    assert not res


def test_kill_count_increments():
    b = BeastmanWorldBosses()
    _seed(b)
    for cycle in range(2):
        offset = cycle * (24 * 3600 + 1000)
        b.open_window(
            boss_id="abyss_titan", now_seconds=offset,
        )
        b.engage(
            boss_id="abyss_titan",
            alliance_size=6,
            level_min=99,
            now_seconds=offset + 10,
        )
        b.record_kill(
            boss_id="abyss_titan",
            killers=("a",) * 6,
            now_seconds=offset + 600,
        )
    assert b.get_boss("abyss_titan").kill_count == 2
