"""Tests for the squadron system."""
from __future__ import annotations

from server.squadron_system import (
    Contract,
    ContractKind,
    ContractStatus,
    MAX_SQUADRON_SIZE,
    SquadronRegistry,
    SquadronSlot,
)


def test_form_squadron_basic():
    reg = SquadronRegistry()
    sq = reg.form_squadron(
        captain_id="alice", name="Demoncore Vanguard",
    )
    assert sq is not None
    assert sq.captain_id == "alice"
    assert reg.total_squadrons() == 1


def test_double_squadron_per_captain_rejected():
    reg = SquadronRegistry()
    reg.form_squadron(captain_id="alice", name="A")
    second = reg.form_squadron(captain_id="alice", name="B")
    assert second is None


def test_invalid_share_pct_rejected():
    reg = SquadronRegistry()
    assert reg.form_squadron(
        captain_id="alice", name="A",
        captain_share_pct=200,
    ) is None


def test_recruit_basic():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    res = reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK, daily_wage_gil=200,
    )
    assert res.accepted
    assert res.member.npc_id == "tank_1"


def test_recruit_unknown_squadron():
    reg = SquadronRegistry()
    res = reg.recruit(
        squadron_id="ghost", npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    assert not res.accepted


def test_recruit_full_squadron_rejected():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    slots = list(SquadronSlot)
    for i, slot in enumerate(slots):
        reg.recruit(
            squadron_id=sq.squadron_id, npc_id=f"npc_{i}",
            slot=slot,
        )
    extra = reg.recruit(
        squadron_id=sq.squadron_id, npc_id="extra",
        slot=SquadronSlot.TANK,
    )
    assert not extra.accepted


def test_recruit_taken_slot_rejected():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    res = reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_2",
        slot=SquadronSlot.TANK,
    )
    assert not res.accepted


def test_recruit_duplicate_npc_rejected():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    res = reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.HEALER,
    )
    assert not res.accepted


def test_dismiss_member():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    assert reg.dismiss(
        squadron_id=sq.squadron_id, npc_id="tank_1",
    )
    assert sq.members == []


def test_dismiss_unknown_returns_false():
    reg = SquadronRegistry()
    assert not reg.dismiss(
        squadron_id="ghost", npc_id="x",
    )


def test_pay_wages_underfunded():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK, daily_wage_gil=200,
    )
    res = reg.pay_wages(
        squadron_id=sq.squadron_id, now_seconds=100.0,
    )
    assert not res.accepted
    assert res.underfunded


def test_pay_wages_success():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK, daily_wage_gil=200,
    )
    reg.deposit(squadron_id=sq.squadron_id, gil=500)
    res = reg.pay_wages(
        squadron_id=sq.squadron_id, now_seconds=100.0,
    )
    assert res.accepted
    assert res.paid_gil == 200
    assert res.captain_balance_after == 300


def test_accept_contract_no_members_rejected():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    res = reg.accept_contract(
        squadron_id=sq.squadron_id,
        contract=Contract(
            contract_id="c1", kind=ContractKind.HUNT,
            payout_gil=10000,
        ),
    )
    assert not res.accepted


def test_accept_contract_with_members():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    res = reg.accept_contract(
        squadron_id=sq.squadron_id,
        contract=Contract(
            contract_id="c1", kind=ContractKind.HUNT,
            payout_gil=10000,
        ),
    )
    assert res.accepted
    assert res.contract.status == ContractStatus.ACCEPTED


def test_complete_contract_pays_out():
    reg = SquadronRegistry()
    sq = reg.form_squadron(
        captain_id="alice", name="A",
        captain_share_pct=60,
    )
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_1",
        slot=SquadronSlot.TANK,
    )
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="healer_1",
        slot=SquadronSlot.HEALER,
    )
    reg.accept_contract(
        squadron_id=sq.squadron_id,
        contract=Contract(
            contract_id="c1", kind=ContractKind.HUNT,
            payout_gil=10000,
        ),
    )
    res = reg.complete_contract(
        squadron_id=sq.squadron_id, contract_id="c1",
    )
    assert res.accepted
    # 60% to captain = 6000; 4000 split between 2 members = 2000 each
    assert res.captain_payout == 6000
    assert res.member_share_each == 2000
    assert sq.treasury_gil == 6000


def test_complete_unaccepted_contract_rejected():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    res = reg.complete_contract(
        squadron_id=sq.squadron_id, contract_id="ghost",
    )
    assert not res.accepted


def test_fail_contract():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="m",
        slot=SquadronSlot.DPS_MELEE,
    )
    reg.accept_contract(
        squadron_id=sq.squadron_id,
        contract=Contract(
            contract_id="c1", kind=ContractKind.RAID,
            payout_gil=5000,
        ),
    )
    assert reg.fail_contract(contract_id="c1")


def test_squadron_for_player_lookup():
    reg = SquadronRegistry()
    sq = reg.form_squadron(captain_id="alice", name="A")
    assert reg.squadron_for_player("alice") is sq
    assert reg.squadron_for_player("bob") is None


def test_max_squadron_size():
    """Constant should match what the test expects."""
    assert MAX_SQUADRON_SIZE == 5


def test_full_lifecycle_squadron_runs_a_contract():
    """Form, recruit, deposit, accept contract, complete,
    pay wages."""
    reg = SquadronRegistry()
    sq = reg.form_squadron(
        captain_id="alice", name="The Vanguard",
        captain_share_pct=50,
    )
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="tank_a",
        slot=SquadronSlot.TANK, daily_wage_gil=150,
    )
    reg.recruit(
        squadron_id=sq.squadron_id, npc_id="healer_b",
        slot=SquadronSlot.HEALER, daily_wage_gil=200,
    )
    reg.accept_contract(
        squadron_id=sq.squadron_id,
        contract=Contract(
            contract_id="hunt_zerde",
            kind=ContractKind.HUNT,
            payout_gil=20000,
        ),
    )
    out = reg.complete_contract(
        squadron_id=sq.squadron_id,
        contract_id="hunt_zerde",
    )
    assert out.accepted
    # Captain takes 10000; members split 10000 -> 5000 each
    assert out.captain_payout == 10000
    assert out.member_share_each == 5000
    # Treasury only stores captain's share for wages
    assert sq.treasury_gil == 10000
    # Pay daily wages (350 total)
    wages = reg.pay_wages(
        squadron_id=sq.squadron_id, now_seconds=100.0,
    )
    assert wages.accepted
    assert wages.paid_gil == 350
    assert sq.treasury_gil == 9650
