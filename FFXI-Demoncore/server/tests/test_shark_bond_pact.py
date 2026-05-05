"""Tests for shark bond pact."""
from __future__ import annotations

from server.shark_bond_pact import (
    BondRank,
    COOLDOWN_SECONDS,
    SharkBondPact,
)


def test_grant_pact_happy():
    s = SharkBondPact()
    ok = s.grant_pact(player_id="p", now_seconds=0)
    assert ok is True
    assert s.status(player_id="p").has_pact is True


def test_grant_pact_blank_player():
    s = SharkBondPact()
    ok = s.grant_pact(player_id="", now_seconds=0)
    assert ok is False


def test_grant_pact_duplicate():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    ok = s.grant_pact(player_id="p", now_seconds=10)
    assert ok is False


def test_summon_no_pact():
    s = SharkBondPact()
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=0,
    )
    assert r.accepted is False
    assert r.reason == "no pact"


def test_summon_happy():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=10,
    )
    assert r.accepted is True
    assert r.rank == BondRank.R1
    assert r.duration_seconds == 60
    assert r.expires_at == 10 + 60


def test_summon_blocked_above_water():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    r = s.summon(
        player_id="p", zone_id="bastok_port",
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "must summon underwater"


def test_summon_blocked_when_active():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=10,
    )
    # try to resummon while shark is alive
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=30,
    )
    assert r.accepted is False
    assert r.reason == "already active"


def test_cooldown_blocks_recast():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=0,
    )
    # let the active duration end (60s for R1)
    # but still inside cooldown (10 min)
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=120,
    )
    assert r.accepted is False
    assert r.reason == "on cooldown"


def test_cooldown_expires():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=0,
    )
    # 10 min + 1s later, cooldown is past
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=COOLDOWN_SECONDS + 1,
    )
    assert r.accepted is True


def test_record_assist_advances_rank():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    # gate to R2 is 5 assists
    for _ in range(5):
        s.record_assist(
            player_id="p", kill_zone_id="abyss_trench",
        )
    assert s.status(player_id="p").rank == BondRank.R2


def test_record_assist_caps_at_r5():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    # accumulate enough to push through all ranks (5+15+30+60 = 110)
    for _ in range(120):
        s.record_assist(
            player_id="p", kill_zone_id="abyss_trench",
        )
    assert s.status(player_id="p").rank == BondRank.R5


def test_record_assist_above_water_rejected():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    ok = s.record_assist(
        player_id="p", kill_zone_id="bastok_port",
    )
    assert ok is False


def test_record_assist_no_pact():
    s = SharkBondPact()
    ok = s.record_assist(
        player_id="p", kill_zone_id="abyss_trench",
    )
    assert ok is False


def test_summon_uses_higher_rank_duration():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    # advance to R2
    for _ in range(5):
        s.record_assist(
            player_id="p", kill_zone_id="abyss_trench",
        )
    r = s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=10,
    )
    assert r.rank == BondRank.R2
    assert r.duration_seconds == 120


def test_recall_ends_summon_early():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    s.summon(
        player_id="p", zone_id="abyss_trench",
        now_seconds=0,
    )
    ok = s.recall(player_id="p", now_seconds=10)
    assert ok is True


def test_recall_when_inactive():
    s = SharkBondPact()
    s.grant_pact(player_id="p", now_seconds=0)
    ok = s.recall(player_id="p", now_seconds=100)
    assert ok is False
