"""Tests for the beastman bestiary inverse."""
from __future__ import annotations

from server.beastman_bestiary_inverse import (
    AdvRace,
    BeastmanBestiaryInverse,
    Threat,
)
from server.beastman_playable_races import BeastmanRace


def _seed(b):
    b.register_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
        threat=Threat.RAIDER,
        kill_quota=3,
        fame_per_kill=20,
        lore_fragment_id="lore_yaguDo_hume_a",
    )


def test_register_entry():
    b = BeastmanBestiaryInverse()
    _seed(b)
    assert b.total_entries() == 1


def test_register_zero_quota_rejected():
    b = BeastmanBestiaryInverse()
    res = b.register_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
        threat=Threat.RAIDER,
        kill_quota=0,
        fame_per_kill=10,
    )
    assert res is None


def test_register_negative_fame_rejected():
    b = BeastmanBestiaryInverse()
    res = b.register_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
        threat=Threat.RAIDER,
        kill_quota=3,
        fame_per_kill=-1,
    )
    assert res is None


def test_register_double_rejected():
    b = BeastmanBestiaryInverse()
    _seed(b)
    res = b.register_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
        threat=Threat.LEGEND,
        kill_quota=99,
        fame_per_kill=99,
    )
    assert res is None


def test_record_slay_increments():
    b = BeastmanBestiaryInverse()
    _seed(b)
    res = b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert res.accepted
    assert res.kills_recorded == 1
    assert not res.completed


def test_record_slay_unknown_entry():
    b = BeastmanBestiaryInverse()
    res = b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.GALKA,
    )
    assert not res.accepted


def test_record_slay_completes_at_quota():
    b = BeastmanBestiaryInverse()
    _seed(b)
    for _ in range(2):
        b.record_slay(
            player_id="brokenfang",
            race=BeastmanRace.YAGUDO,
            adv_race=AdvRace.HUME,
        )
    res = b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert res.completed
    assert b.has_completed(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )


def test_record_slay_after_complete_still_counts():
    b = BeastmanBestiaryInverse()
    _seed(b)
    for _ in range(3):
        b.record_slay(
            player_id="brokenfang",
            race=BeastmanRace.YAGUDO,
            adv_race=AdvRace.HUME,
        )
    res = b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert res.accepted
    assert res.kills_recorded == 4
    assert res.completed


def test_quota_progress_unknown_zero():
    b = BeastmanBestiaryInverse()
    cur, q = b.quota_progress(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert cur == 0
    assert q == 0


def test_quota_progress_with_entry():
    b = BeastmanBestiaryInverse()
    _seed(b)
    cur, q = b.quota_progress(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert cur == 0
    assert q == 3


def test_quota_progress_after_kills():
    b = BeastmanBestiaryInverse()
    _seed(b)
    b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    cur, q = b.quota_progress(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert cur == 1
    assert q == 3


def test_has_completed_false_initially():
    b = BeastmanBestiaryInverse()
    _seed(b)
    assert not b.has_completed(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )


def test_get_entry_lookup():
    b = BeastmanBestiaryInverse()
    _seed(b)
    e = b.get_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert e is not None
    assert e.threat == Threat.RAIDER


def test_get_unknown_returns_none():
    b = BeastmanBestiaryInverse()
    e = b.get_entry(
        race=BeastmanRace.ORC,
        adv_race=AdvRace.MITHRA,
    )
    assert e is None


def test_per_race_isolation():
    b = BeastmanBestiaryInverse()
    _seed(b)
    b.register_entry(
        race=BeastmanRace.ORC,
        adv_race=AdvRace.HUME,
        threat=Threat.WARLORD,
        kill_quota=5,
        fame_per_kill=30,
    )
    b.record_slay(
        player_id="brokenfang",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    cur_orc, _ = b.quota_progress(
        player_id="brokenfang",
        race=BeastmanRace.ORC,
        adv_race=AdvRace.HUME,
    )
    assert cur_orc == 0


def test_per_player_isolation():
    b = BeastmanBestiaryInverse()
    _seed(b)
    b.record_slay(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    cur_bob, _ = b.quota_progress(
        player_id="bob",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert cur_bob == 0


def test_total_kills_for_player():
    b = BeastmanBestiaryInverse()
    _seed(b)
    b.register_entry(
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.ELVAAN,
        threat=Threat.RAIDER,
        kill_quota=2,
        fame_per_kill=10,
    )
    b.record_slay(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    b.record_slay(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.ELVAAN,
    )
    assert b.total_kills_for(
        player_id="alice",
    ) == 2


def test_fame_awarded_per_kill():
    b = BeastmanBestiaryInverse()
    _seed(b)
    res = b.record_slay(
        player_id="alice",
        race=BeastmanRace.YAGUDO,
        adv_race=AdvRace.HUME,
    )
    assert res.fame_awarded == 20


def test_register_outlaw_kind():
    b = BeastmanBestiaryInverse()
    e = b.register_entry(
        race=BeastmanRace.ORC,
        adv_race=AdvRace.OUTLAW,
        threat=Threat.LEGEND,
        kill_quota=1,
        fame_per_kill=200,
    )
    assert e is not None


def test_threat_legend_high_quota():
    b = BeastmanBestiaryInverse()
    e = b.register_entry(
        race=BeastmanRace.QUADAV,
        adv_race=AdvRace.HUME,
        threat=Threat.LEGEND,
        kill_quota=20,
        fame_per_kill=500,
    )
    assert e.threat == Threat.LEGEND
    assert e.kill_quota == 20
