"""Tests for NPC assassin contracts."""
from __future__ import annotations

from server.npc_assassin_contracts import (
    ContractStatus,
    ContractTargetKind,
    MAX_HANDLER_FEE_PCT,
    MIN_PAYOUT_GIL,
    NPCAssassinContracts,
)


def test_post_contract():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="merchant_a",
        target_id="rival_merchant",
        target_kind=ContractTargetKind.NPC,
        payout_gil=10000,
    )
    assert c is not None
    assert c.status == ContractStatus.OPEN


def test_post_self_target_rejected():
    a = NPCAssassinContracts()
    assert a.post_contract(
        poster_id="alice", target_id="alice",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    ) is None


def test_post_below_min_payout_rejected():
    a = NPCAssassinContracts()
    assert a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=MIN_PAYOUT_GIL - 1,
    ) is None


def test_post_zero_expiry_rejected():
    a = NPCAssassinContracts()
    assert a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
        expires_in_seconds=0,
    ) is None


def test_post_invalid_handler_fee_rejected():
    a = NPCAssassinContracts()
    assert a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
        handler_fee_pct=MAX_HANDLER_FEE_PCT + 1,
    ) is None


def test_accept_succeeds():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
        posted_at_seconds=0.0,
        expires_in_seconds=100.0,
    )
    assert a.accept(
        contract_id=c.contract_id,
        assassin_id="killer",
        now_seconds=10.0,
    )
    assert a.get(c.contract_id).status == ContractStatus.ACCEPTED


def test_accept_target_self_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert not a.accept(
        contract_id=c.contract_id, assassin_id="bob",
    )


def test_accept_poster_self_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert not a.accept(
        contract_id=c.contract_id, assassin_id="alice",
    )


def test_accept_after_expiry():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
        posted_at_seconds=0.0,
        expires_in_seconds=10.0,
    )
    assert not a.accept(
        contract_id=c.contract_id, assassin_id="killer",
        now_seconds=100.0,
    )


def test_accept_unknown():
    a = NPCAssassinContracts()
    assert not a.accept(
        contract_id="ghost", assassin_id="x",
    )


def test_double_accept_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    a.accept(
        contract_id=c.contract_id, assassin_id="k1",
    )
    assert not a.accept(
        contract_id=c.contract_id, assassin_id="k2",
    )


def test_complete_pays_split():
    a = NPCAssassinContracts(
        default_handler_fee_pct=10,
    )
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    a.accept(
        contract_id=c.contract_id, assassin_id="killer",
    )
    payout = a.complete(
        contract_id=c.contract_id, assassin_id="killer",
    )
    assert payout is not None
    # 10% handler = 100, assassin 900
    assert payout.gil_to_handler == 100
    assert payout.gil_to_assassin == 900


def test_complete_wrong_assassin_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    a.accept(
        contract_id=c.contract_id, assassin_id="real",
    )
    assert a.complete(
        contract_id=c.contract_id, assassin_id="impostor",
    ) is None


def test_complete_unaccepted_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert a.complete(
        contract_id=c.contract_id, assassin_id="anyone",
    ) is None


def test_cancel_by_poster():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert a.cancel(
        contract_id=c.contract_id, by_id="alice",
    )
    assert a.get(c.contract_id).status == ContractStatus.CANCELED


def test_cancel_by_other_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert not a.cancel(
        contract_id=c.contract_id, by_id="dave",
    )


def test_seize_active_contract():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert a.seize(contract_id=c.contract_id)
    assert a.get(c.contract_id).status == ContractStatus.SEIZED


def test_seize_completed_rejected():
    a = NPCAssassinContracts()
    c = a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    a.accept(
        contract_id=c.contract_id, assassin_id="k",
    )
    a.complete(
        contract_id=c.contract_id, assassin_id="k",
    )
    assert not a.seize(contract_id=c.contract_id)


def test_open_contracts_against_target():
    a = NPCAssassinContracts()
    a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    a.post_contract(
        poster_id="dave", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=2000,
    )
    open_against_bob = a.open_contracts_against(
        target_id="bob",
    )
    assert len(open_against_bob) == 2


def test_tick_expires_open():
    a = NPCAssassinContracts()
    a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
        posted_at_seconds=0.0,
        expires_in_seconds=10.0,
    )
    expired = a.tick(now_seconds=100.0)
    assert len(expired) == 1


def test_total_contracts():
    a = NPCAssassinContracts()
    a.post_contract(
        poster_id="alice", target_id="bob",
        target_kind=ContractTargetKind.NPC,
        payout_gil=1000,
    )
    assert a.total_contracts() == 1
