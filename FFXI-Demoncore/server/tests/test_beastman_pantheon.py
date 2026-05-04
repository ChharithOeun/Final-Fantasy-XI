"""Tests for the beastman pantheon."""
from __future__ import annotations

from server.beastman_pantheon import (
    BeastmanPantheon,
    DeityKind,
    PilgrimageStage,
)
from server.beastman_playable_races import BeastmanRace


def test_pledge_to_shathar():
    p = BeastmanPantheon()
    assert p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert p.is_devotee(player_id="alice")


def test_pledge_double_rejected():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert not p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )


def test_advance_pilgrimage_in_order():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    res = p.advance_pilgrimage_stage(
        player_id="alice",
        stage=PilgrimageStage.OUTCAST_TEMPLE,
    )
    assert res.accepted
    assert not res.is_complete


def test_advance_pilgrimage_out_of_order():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    res = p.advance_pilgrimage_stage(
        player_id="alice",
        stage=PilgrimageStage.SHATHAR_VOICE,
    )
    assert not res.accepted


def test_pilgrimage_completes_on_final_stage():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    for stage in (
        PilgrimageStage.OUTCAST_TEMPLE,
        PilgrimageStage.HOLLOW_THRONE,
        PilgrimageStage.BROKEN_VEIL,
        PilgrimageStage.SHATHAR_VOICE,
    ):
        p.advance_pilgrimage_stage(
            player_id="alice", stage=stage,
        )
    assert p.pilgrimage_complete(player_id="alice")


def test_advance_after_complete_rejected():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    for stage in PilgrimageStage:
        p.advance_pilgrimage_stage(
            player_id="alice", stage=stage,
        )
    res = p.advance_pilgrimage_stage(
        player_id="alice",
        stage=PilgrimageStage.OUTCAST_TEMPLE,
    )
    assert not res.accepted


def test_advance_without_pledge():
    p = BeastmanPantheon()
    res = p.advance_pilgrimage_stage(
        player_id="alice",
        stage=PilgrimageStage.OUTCAST_TEMPLE,
    )
    assert not res.accepted


def test_praise_tavnazian_hero():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    n = p.praise_tavnazian_hero(player_id="alice")
    assert n == 1
    n2 = p.praise_tavnazian_hero(player_id="alice")
    assert n2 == 2


def test_praise_without_pledge():
    p = BeastmanPantheon()
    assert p.praise_tavnazian_hero(
        player_id="alice",
    ) is None


def test_times_praised_lookup():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    p.praise_tavnazian_hero(player_id="alice")
    p.praise_tavnazian_hero(player_id="alice")
    assert p.times_hero_praised(player_id="alice") == 2


def test_declare_goblin():
    p = BeastmanPantheon()
    assert p.declare_goblin(npc_id="goblin_smithy")
    assert p.is_goblin_neutral(
        npc_id="goblin_smithy",
    )


def test_declare_goblin_empty_rejected():
    p = BeastmanPantheon()
    assert not p.declare_goblin(npc_id="")


def test_declare_goblin_double_rejected():
    p = BeastmanPantheon()
    p.declare_goblin(npc_id="g1")
    assert not p.declare_goblin(npc_id="g1")


def test_goblin_neutral_trade():
    p = BeastmanPantheon()
    p.declare_goblin(npc_id="g1")
    assert p.mark_goblin_neutral_trade(
        buyer_id="alice", seller_id="g1",
    )
    partners = p.goblin_partners_for(buyer_id="alice")
    assert "g1" in partners


def test_trade_with_non_goblin_rejected():
    p = BeastmanPantheon()
    assert not p.mark_goblin_neutral_trade(
        buyer_id="alice", seller_id="not_a_goblin",
    )


def test_trade_self_rejected():
    p = BeastmanPantheon()
    p.declare_goblin(npc_id="alice")
    assert not p.mark_goblin_neutral_trade(
        buyer_id="alice", seller_id="alice",
    )


def test_trade_double_rejected():
    p = BeastmanPantheon()
    p.declare_goblin(npc_id="g1")
    p.mark_goblin_neutral_trade(
        buyer_id="alice", seller_id="g1",
    )
    assert not p.mark_goblin_neutral_trade(
        buyer_id="alice", seller_id="g1",
    )


def test_devotion_records_deity_shathar():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.QUADAV,
    )
    d = p._devotions["alice"]
    assert d.deity == DeityKind.SHATHAR


def test_total_counts():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    p.pledge_to_shathar(
        player_id="bob", race=BeastmanRace.ORC,
    )
    p.declare_goblin(npc_id="g1")
    p.declare_goblin(npc_id="g2")
    assert p.total_devotees() == 2
    assert p.total_goblin_npcs() == 2


def test_per_player_isolation():
    p = BeastmanPantheon()
    p.pledge_to_shathar(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    p.praise_tavnazian_hero(player_id="alice")
    assert p.times_hero_praised(player_id="bob") == 0
