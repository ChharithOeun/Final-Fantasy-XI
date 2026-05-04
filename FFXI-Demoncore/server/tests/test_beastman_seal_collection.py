"""Tests for the beastman seal collection."""
from __future__ import annotations

from server.beastman_seal_collection import (
    BeastmanSealCollection,
    SealRank,
    SealSlot,
)


def test_grant_seal():
    s = BeastmanSealCollection()
    res = s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=5,
    )
    assert res.accepted
    assert res.new_balance == 5


def test_grant_zero_rejected():
    s = BeastmanSealCollection()
    res = s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=0,
    )
    assert not res.accepted


def test_grant_negative_rejected():
    s = BeastmanSealCollection()
    res = s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=-3,
    )
    assert not res.accepted


def test_grant_accumulates():
    s = BeastmanSealCollection()
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=3,
    )
    res = s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=2,
    )
    assert res.new_balance == 5


def test_balance_default_zero():
    s = BeastmanSealCollection()
    assert s.balance(
        player_id="ghost",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
    ) == 0


def test_register_recipe():
    s = BeastmanSealCollection()
    res = s.register_recipe(
        piece_id="yagudo_af_head",
        slot=SealSlot.HEAD,
        crested_cost=5,
        ascended_cost=1,
    )
    assert res is not None
    assert s.total_recipes() == 1


def test_register_recipe_duplicate():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="x",
        slot=SealSlot.HEAD,
        crested_cost=5, ascended_cost=1,
    )
    res = s.register_recipe(
        piece_id="x",
        slot=SealSlot.BODY,
        crested_cost=10, ascended_cost=2,
    )
    assert res is None


def test_register_recipe_zero_total():
    s = BeastmanSealCollection()
    res = s.register_recipe(
        piece_id="x",
        slot=SealSlot.HEAD,
        crested_cost=0, ascended_cost=0,
    )
    assert res is None


def test_register_recipe_negative_cost():
    s = BeastmanSealCollection()
    res = s.register_recipe(
        piece_id="x",
        slot=SealSlot.HEAD,
        crested_cost=-1, ascended_cost=1,
    )
    assert res is None


def test_redeem_basic():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=5, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=5,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
        count=1,
    )
    res = s.redeem(player_id="kraw", piece_id="head_af")
    assert res.accepted


def test_redeem_consumes_seals():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=5, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=10,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
        count=2,
    )
    s.redeem(player_id="kraw", piece_id="head_af")
    assert s.balance(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
    ) == 5
    assert s.balance(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
    ) == 1


def test_redeem_insufficient_crested():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=5, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=2,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
        count=1,
    )
    res = s.redeem(player_id="kraw", piece_id="head_af")
    assert not res.accepted


def test_redeem_insufficient_ascended():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=5, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=10,
    )
    res = s.redeem(player_id="kraw", piece_id="head_af")
    assert not res.accepted


def test_redeem_unknown_piece():
    s = BeastmanSealCollection()
    res = s.redeem(player_id="kraw", piece_id="ghost")
    assert not res.accepted


def test_redeem_double_blocked():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=2, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=10,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
        count=10,
    )
    s.redeem(player_id="kraw", piece_id="head_af")
    res = s.redeem(player_id="kraw", piece_id="head_af")
    assert not res.accepted


def test_has_redeemed():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="head_af",
        slot=SealSlot.HEAD,
        crested_cost=2, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=2,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.ASCENDED,
        count=1,
    )
    s.redeem(player_id="kraw", piece_id="head_af")
    assert s.has_redeemed(
        player_id="kraw", piece_id="head_af",
    )


def test_per_slot_seal_isolation():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="body_af",
        slot=SealSlot.BODY,
        crested_cost=5, ascended_cost=1,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=10,
    )
    res = s.redeem(player_id="kraw", piece_id="body_af")
    # Wrong slot — should fail
    assert not res.accepted


def test_per_player_isolation():
    s = BeastmanSealCollection()
    s.grant_seal(
        player_id="alice",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
        count=5,
    )
    assert s.balance(
        player_id="bob",
        slot=SealSlot.HEAD,
        rank=SealRank.CRESTED,
    ) == 0


def test_zero_ascended_recipe_works():
    s = BeastmanSealCollection()
    s.register_recipe(
        piece_id="cheap_piece",
        slot=SealSlot.FEET,
        crested_cost=3, ascended_cost=0,
    )
    s.grant_seal(
        player_id="kraw",
        slot=SealSlot.FEET,
        rank=SealRank.CRESTED,
        count=3,
    )
    res = s.redeem(player_id="kraw", piece_id="cheap_piece")
    assert res.accepted


def test_total_recipes():
    s = BeastmanSealCollection()
    for slot in SealSlot:
        s.register_recipe(
            piece_id=f"af_{slot.value}",
            slot=slot,
            crested_cost=5, ascended_cost=1,
        )
    assert s.total_recipes() == 5
