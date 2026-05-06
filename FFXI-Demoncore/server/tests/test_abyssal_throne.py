"""Tests for abyssal throne."""
from __future__ import annotations

from server.abyssal_throne import (
    AbyssalThrone,
    BossTier,
    MIN_PARTY_SIZE,
)


def test_t1_solo_kill_happy():
    a = AbyssalThrone()
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    assert ok is True


def test_blank_player_blocked():
    a = AbyssalThrone()
    assert a.register_player_kill(
        player_id="", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=0, alliance_size=1,
    ) is False


def test_cannot_skip_tiers():
    a = AbyssalThrone()
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.TIDE_WURM,
        now_seconds=100, alliance_size=6,
    )
    assert ok is False


def test_can_progress_through_tiers():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.TIDE_WURM,
        now_seconds=200, alliance_size=6,
    )
    assert ok is True


def test_alliance_size_below_minimum_blocked():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.TIDE_WURM,
        now_seconds=200, alliance_size=3,  # < 6
    )
    assert ok is False


def test_min_party_sizes_canonical():
    assert MIN_PARTY_SIZE[BossTier.KRAKEN_SPAWN] == 1
    assert MIN_PARTY_SIZE[BossTier.THE_DROWNED_KING] == 64


def test_has_killed_after_register():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    assert a.has_killed(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
    ) is True


def test_has_not_killed_default():
    a = AbyssalThrone()
    assert a.has_killed(
        player_id="ghost", tier=BossTier.KRAKEN_SPAWN,
    ) is False


def test_can_attempt_kraken_spawn_always():
    a = AbyssalThrone()
    ok, _ = a.can_attempt(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
    )
    assert ok is True


def test_can_attempt_blocked_without_prereq():
    a = AbyssalThrone()
    ok, reason = a.can_attempt(
        player_id="p1", tier=BossTier.GULF_LEVIATHAN,
    )
    assert ok is False
    assert "SUNKEN_HIERARCH" in reason or "GULF" in reason or "TIDE_WURM" in reason


def test_world_first_records_first_kill():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="alice", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    a.register_player_kill(
        player_id="bob", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=200, alliance_size=1,
    )
    wf = a.world_first(tier=BossTier.KRAKEN_SPAWN)
    assert wf is not None
    assert wf.player_id == "alice"
    assert wf.killed_at == 100


def test_world_first_none_for_unkilled():
    a = AbyssalThrone()
    assert a.world_first(tier=BossTier.THE_DROWNED_KING) is None


def test_total_kills_count():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="alice", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    a.register_player_kill(
        player_id="bob", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=200, alliance_size=1,
    )
    assert a.total_kills(tier=BossTier.KRAKEN_SPAWN) == 2


def test_total_kills_zero_default():
    a = AbyssalThrone()
    assert a.total_kills(tier=BossTier.THE_DROWNED_KING) == 0


def test_progression_for_returns_sorted():
    a = AbyssalThrone()
    a.register_player_kill(
        player_id="p1", tier=BossTier.KRAKEN_SPAWN,
        now_seconds=100, alliance_size=1,
    )
    a.register_player_kill(
        player_id="p1", tier=BossTier.TIDE_WURM,
        now_seconds=200, alliance_size=6,
    )
    out = a.progression_for(player_id="p1")
    assert out == (BossTier.KRAKEN_SPAWN, BossTier.TIDE_WURM)


def test_drowned_king_requires_64_alliance():
    a = AbyssalThrone()
    # set up full prereq chain
    sizes = {
        BossTier.KRAKEN_SPAWN: 1, BossTier.TIDE_WURM: 6,
        BossTier.GULF_LEVIATHAN: 18, BossTier.SUNKEN_HIERARCH: 18,
        BossTier.ABYSS_HARBINGER: 24, BossTier.DEPTH_TYRANT: 36,
    }
    for tier in [
        BossTier.KRAKEN_SPAWN, BossTier.TIDE_WURM,
        BossTier.GULF_LEVIATHAN, BossTier.SUNKEN_HIERARCH,
        BossTier.ABYSS_HARBINGER, BossTier.DEPTH_TYRANT,
    ]:
        a.register_player_kill(
            player_id="p1", tier=tier,
            now_seconds=100 * tier.value,
            alliance_size=sizes[tier],
        )
    # 32-person attempt: blocked
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.THE_DROWNED_KING,
        now_seconds=10000, alliance_size=32,
    )
    assert ok is False
    # 64-person attempt: OK
    ok = a.register_player_kill(
        player_id="p1", tier=BossTier.THE_DROWNED_KING,
        now_seconds=10000, alliance_size=64,
    )
    assert ok is True
