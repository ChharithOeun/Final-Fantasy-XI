"""Tests for the beastman trust NPCs."""
from __future__ import annotations

from server.beastman_playable_races import BeastmanRace
from server.beastman_trust_npcs import (
    BeastmanTrustNpcs,
    TrustRole,
)


def _seed_yagudo_bishop(t):
    return t.register_trust(
        trust_id="trust_bishop_supreme",
        race=BeastmanRace.YAGUDO,
        role=TrustRole.HEALER,
        label="Bishop Supreme",
        unlock_quest_id="oztroja_bishop_quest",
        flavor="An elder yagudo whose hymn restores wounds",
    )


def test_register_trust():
    t = BeastmanTrustNpcs()
    npc = _seed_yagudo_bishop(t)
    assert npc is not None


def test_register_double_id_rejected():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    second = t.register_trust(
        trust_id="trust_bishop_supreme",
        race=BeastmanRace.YAGUDO,
        role=TrustRole.TANK,
        label="x", unlock_quest_id="y",
    )
    assert second is None


def test_register_empty_label_rejected():
    t = BeastmanTrustNpcs()
    res = t.register_trust(
        trust_id="x",
        race=BeastmanRace.YAGUDO,
        role=TrustRole.TANK,
        label="", unlock_quest_id="y",
    )
    assert res is None


def test_register_empty_quest_rejected():
    t = BeastmanTrustNpcs()
    res = t.register_trust(
        trust_id="x",
        race=BeastmanRace.YAGUDO,
        role=TrustRole.TANK,
        label="x", unlock_quest_id="",
    )
    assert res is None


def test_unlock_succeeds():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    res = t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert res.accepted


def test_unlock_unknown():
    t = BeastmanTrustNpcs()
    res = t.unlock(
        player_id="alice", trust_id="ghost",
    )
    assert not res.accepted


def test_unlock_double_rejected():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    res = t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert not res.accepted


def test_summon_only_if_unlocked():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    assert not t.summon(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert t.summon(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )


def test_summon_unknown():
    t = BeastmanTrustNpcs()
    assert not t.summon(
        player_id="alice", trust_id="ghost",
    )


def test_roster_for_race():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.register_trust(
        trust_id="trust_orc_warlord",
        race=BeastmanRace.ORC,
        role=TrustRole.DPS_MELEE,
        label="Orc Warlord",
        unlock_quest_id="orc_quest",
    )
    yagudo_roster = t.roster_for(
        race=BeastmanRace.YAGUDO,
    )
    assert len(yagudo_roster) == 1
    assert (
        yagudo_roster[0].trust_id
        == "trust_bishop_supreme"
    )


def test_available_for_only_unlocked():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.register_trust(
        trust_id="trust_yagudo_assassin",
        race=BeastmanRace.YAGUDO,
        role=TrustRole.DPS_MELEE,
        label="Yagudo Assassin",
        unlock_quest_id="assassin_quest",
    )
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    avail = t.available_for(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert len(avail) == 1
    assert (
        avail[0].trust_id == "trust_bishop_supreme"
    )


def test_available_for_no_unlocks():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    avail = t.available_for(
        player_id="bob", race=BeastmanRace.YAGUDO,
    )
    assert avail == ()


def test_has_unlocked_lookup():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    assert not t.has_unlocked(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert t.has_unlocked(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )


def test_get_trust_def():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    npc = t.get("trust_bishop_supreme")
    assert npc is not None
    assert npc.role == TrustRole.HEALER


def test_get_unknown_returns_none():
    t = BeastmanTrustNpcs()
    assert t.get("ghost") is None


def test_total_trusts_count():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.register_trust(
        trust_id="trust_quadav_forger",
        race=BeastmanRace.QUADAV,
        role=TrustRole.TANK,
        label="Quadav Forger",
        unlock_quest_id="forger_quest",
    )
    assert t.total_trusts() == 2


def test_total_unlocks_per_player():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert t.total_unlocks(player_id="alice") == 1
    assert t.total_unlocks(player_id="bob") == 0


def test_per_player_isolation():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.unlock(
        player_id="alice",
        trust_id="trust_bishop_supreme",
    )
    assert not t.has_unlocked(
        player_id="bob",
        trust_id="trust_bishop_supreme",
    )


def test_roster_filters_by_race():
    t = BeastmanTrustNpcs()
    _seed_yagudo_bishop(t)
    t.register_trust(
        trust_id="trust_lamia_witch",
        race=BeastmanRace.LAMIA,
        role=TrustRole.DPS_RANGED,
        label="Lamia Witch",
        unlock_quest_id="witch_quest",
    )
    lamia_roster = t.roster_for(
        race=BeastmanRace.LAMIA,
    )
    assert len(lamia_roster) == 1
