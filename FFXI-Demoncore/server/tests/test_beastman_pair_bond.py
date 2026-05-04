"""Tests for the beastman pair bond."""
from __future__ import annotations

from server.beastman_pair_bond import (
    BeastmanPairBond,
    BondPhase,
)


_FULL_OFFERINGS = {
    "prime_feather": 1,
    "coral_scale": 1,
    "lacquered_stone": 1,
    "reaver_bone": 1,
}


def test_propose_basic():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    assert res.accepted
    assert res.bond_id == 1


def test_propose_self_rejected():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="kraw", now_day=0,
    )
    assert not res.accepted


def test_propose_double_active_blocked():
    b = BeastmanPairBond()
    b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    res = b.propose(
        proposer_id="kraw", partner_id="zlar", now_day=1,
    )
    assert not res.accepted


def test_propose_partner_already_bonded():
    b = BeastmanPairBond()
    b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    res = b.propose(
        proposer_id="zlar", partner_id="syrene", now_day=1,
    )
    assert not res.accepted


def test_accept_basic():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    a = b.accept(
        partner_id="syrene", bond_id=res.bond_id, now_day=2,
    )
    assert a.accepted
    assert a.phase == BondPhase.PROPOSED


def test_accept_wrong_partner():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    a = b.accept(
        partner_id="zlar", bond_id=res.bond_id, now_day=2,
    )
    assert not a.accepted


def test_accept_after_lapse():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    a = b.accept(
        partner_id="syrene", bond_id=res.bond_id, now_day=10,
    )
    assert not a.accepted
    assert a.phase == BondPhase.DISSOLVED


def test_accept_unknown_bond():
    b = BeastmanPairBond()
    a = b.accept(
        partner_id="syrene", bond_id=999, now_day=0,
    )
    assert not a.accepted


def test_consecrate_full_offerings():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    c = b.consecrate(
        bond_id=res.bond_id,
        offerings=_FULL_OFFERINGS,
        now_day=2,
    )
    assert c.accepted
    assert c.phase == BondPhase.CONSECRATED


def test_consecrate_missing_offering():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    partial = dict(_FULL_OFFERINGS)
    partial.pop("reaver_bone")
    c = b.consecrate(
        bond_id=res.bond_id,
        offerings=partial,
        now_day=2,
    )
    assert not c.accepted


def test_consecrate_wrong_phase():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    b.consecrate(
        bond_id=res.bond_id,
        offerings=_FULL_OFFERINGS,
        now_day=2,
    )
    c = b.consecrate(
        bond_id=res.bond_id,
        offerings=_FULL_OFFERINGS,
        now_day=3,
    )
    assert not c.accepted


def test_seal_basic():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    b.consecrate(
        bond_id=res.bond_id,
        offerings=_FULL_OFFERINGS,
        now_day=2,
    )
    s = b.seal(bond_id=res.bond_id, now_day=3)
    assert s.accepted
    assert s.phase == BondPhase.SEALED


def test_seal_before_consecrate():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    s = b.seal(bond_id=res.bond_id, now_day=2)
    assert not s.accepted


def test_dissolve_basic():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    b.consecrate(
        bond_id=res.bond_id,
        offerings=_FULL_OFFERINGS,
        now_day=2,
    )
    b.seal(bond_id=res.bond_id, now_day=3)
    d = b.dissolve(
        bond_id=res.bond_id,
        initiator_id="kraw",
        now_day=10,
    )
    assert d.accepted
    assert d.phase == BondPhase.DISSOLVED


def test_dissolve_by_partner():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    d = b.dissolve(
        bond_id=res.bond_id,
        initiator_id="syrene",
        now_day=2,
    )
    assert d.accepted


def test_dissolve_by_outsider_blocked():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    d = b.dissolve(
        bond_id=res.bond_id,
        initiator_id="zlar",
        now_day=2,
    )
    assert not d.accepted


def test_propose_during_cooldown():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    b.dissolve(
        bond_id=res.bond_id,
        initiator_id="kraw",
        now_day=5,
    )
    res2 = b.propose(
        proposer_id="kraw", partner_id="zlar", now_day=10,
    )
    assert not res2.accepted


def test_propose_after_cooldown_clears():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    b.dissolve(
        bond_id=res.bond_id,
        initiator_id="kraw",
        now_day=5,
    )
    res2 = b.propose(
        proposer_id="kraw", partner_id="zlar", now_day=40,
    )
    assert res2.accepted


def test_bond_for_active():
    b = BeastmanPairBond()
    res = b.propose(
        proposer_id="kraw", partner_id="syrene", now_day=0,
    )
    bond = b.bond_for(player_id="syrene")
    assert bond is not None
    assert bond.bond_id == res.bond_id


def test_bond_for_none():
    b = BeastmanPairBond()
    assert b.bond_for(player_id="ghost") is None


def test_dissolve_unknown():
    b = BeastmanPairBond()
    d = b.dissolve(
        bond_id=999,
        initiator_id="kraw",
        now_day=0,
    )
    assert not d.accepted
