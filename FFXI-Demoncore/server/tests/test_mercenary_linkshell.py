"""Tests for mercenary_linkshell."""
from __future__ import annotations

from server.mercenary_linkshell import (
    MercenaryLinkshellSystem, Specialization,
    LinkshellState,
)


def _register(s: MercenaryLinkshellSystem) -> str:
    return s.register_ls(
        name="Iron Blades", founder_id="naji",
        specialization=Specialization.CONTENT_CARRY,
    )


def test_register_happy():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    assert lid is not None


def test_register_duplicate_name_blocked():
    s = MercenaryLinkshellSystem()
    _register(s)
    assert s.register_ls(
        name="Iron Blades", founder_id="other",
        specialization=Specialization.GENERALIST,
    ) is None


def test_register_empty_name_blocked():
    s = MercenaryLinkshellSystem()
    assert s.register_ls(
        name="", founder_id="naji",
        specialization=Specialization.GENERALIST,
    ) is None


def test_founder_is_first_member():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    ls = s.linkshell(ls_id=lid)
    assert "naji" in ls.members
    assert len(ls.members) == 1


def test_add_member_happy():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    assert s.add_member(
        ls_id=lid, member_id="bob",
    ) is True


def test_add_duplicate_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    assert s.add_member(
        ls_id=lid, member_id="bob",
    ) is False


def test_add_member_cap():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    # Founder + 11 = 12 (cap)
    for i in range(11):
        s.add_member(ls_id=lid, member_id=f"m{i}")
    assert s.add_member(
        ls_id=lid, member_id="overflow",
    ) is False


def test_remove_member_happy():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    assert s.remove_member(
        ls_id=lid, member_id="bob",
    ) is True


def test_remove_founder_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    assert s.remove_member(
        ls_id=lid, member_id="naji",
    ) is False


def test_transfer_founder_happy():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    assert s.transfer_founder(
        ls_id=lid, current_founder="naji",
        new_founder="bob",
    ) is True


def test_transfer_to_non_member_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    assert s.transfer_founder(
        ls_id=lid, current_founder="naji",
        new_founder="cara",
    ) is False


def test_transfer_wrong_current_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    assert s.transfer_founder(
        ls_id=lid, current_founder="bob",
        new_founder="bob",
    ) is False


def test_can_accept_below_min_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    # Only founder, below min of 2
    assert s.can_accept_kind(
        ls_id=lid, kind="craft_order",
    ) is False


def test_can_accept_at_min_ok():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    assert s.can_accept_kind(
        ls_id=lid, kind="craft_order",
    ) is True


def test_credit_completion_grows_pool():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.credit_completion(
        ls_id=lid, payout_gil=10000,
    )
    ls = s.linkshell(ls_id=lid)
    assert ls.pool_gil == 10000
    assert ls.contracts_completed == 1


def test_credit_below_min_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    # Solo — below min
    assert s.credit_completion(
        ls_id=lid, payout_gil=10000,
    ) is False


def test_distribute_pool_evenly():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.add_member(ls_id=lid, member_id="cara")
    # 3 members, 9000 gil → 3000 each
    s.credit_completion(ls_id=lid, payout_gil=9000)
    per = s.distribute_pool_evenly(
        ls_id=lid, founder_id="naji",
    )
    assert per == 3000
    assert s.linkshell(ls_id=lid).pool_gil == 0


def test_distribute_remainder_stays():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.add_member(ls_id=lid, member_id="cara")
    # 3 members, 10000 gil → 3333 each, 1 remainder
    s.credit_completion(ls_id=lid, payout_gil=10000)
    per = s.distribute_pool_evenly(
        ls_id=lid, founder_id="naji",
    )
    assert per == 3333
    assert s.linkshell(ls_id=lid).pool_gil == 1


def test_distribute_wrong_founder_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.credit_completion(ls_id=lid, payout_gil=2000)
    assert s.distribute_pool_evenly(
        ls_id=lid, founder_id="bob",
    ) is None


def test_disband_happy():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.credit_completion(ls_id=lid, payout_gil=5000)
    final = s.disband(
        ls_id=lid, founder_id="naji",
    )
    assert final == 5000
    assert s.linkshell(
        ls_id=lid,
    ).state == LinkshellState.DISBANDED


def test_disband_wrong_founder_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    assert s.disband(
        ls_id=lid, founder_id="bob",
    ) is None


def test_actions_after_disband_blocked():
    s = MercenaryLinkshellSystem()
    lid = _register(s)
    s.add_member(ls_id=lid, member_id="bob")
    s.disband(ls_id=lid, founder_id="naji")
    assert s.add_member(
        ls_id=lid, member_id="cara",
    ) is False
    assert s.credit_completion(
        ls_id=lid, payout_gil=1000,
    ) is False


def test_lses_by_specialization():
    s = MercenaryLinkshellSystem()
    s.register_ls(
        name="Iron Blades", founder_id="a",
        specialization=Specialization.CONTENT_CARRY,
    )
    s.register_ls(
        name="Gold Hands", founder_id="b",
        specialization=Specialization.CRAFT_ORDER,
    )
    s.register_ls(
        name="Silver Carriers", founder_id="c",
        specialization=Specialization.CONTENT_CARRY,
    )
    carriers = s.lses_by_specialization(
        specialization=Specialization.CONTENT_CARRY,
    )
    assert len(carriers) == 2


def test_unknown_ls():
    s = MercenaryLinkshellSystem()
    assert s.linkshell(ls_id="ghost") is None


def test_enum_counts():
    assert len(list(Specialization)) == 7
    assert len(list(LinkshellState)) == 3
