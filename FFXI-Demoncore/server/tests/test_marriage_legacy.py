"""Tests for marriage_legacy."""
from __future__ import annotations

from server.marriage_legacy import (
    MarriageLegacy, MarriageState,
)


def _wed(m, a="bob", b="cara", year=100, prop="bob"):
    return m.marry(
        spouse_a=a, spouse_b=b,
        ceremony_year=year, proposer=prop,
    )


def test_marry_happy():
    m = MarriageLegacy()
    assert _wed(m) is True
    assert m.marriage_state(
        spouse="bob",
    ) == MarriageState.MARRIED


def test_marry_blank_blocked():
    m = MarriageLegacy()
    assert m.marry(
        spouse_a="", spouse_b="cara",
        ceremony_year=100, proposer="cara",
    ) is False


def test_marry_self_blocked():
    m = MarriageLegacy()
    assert m.marry(
        spouse_a="bob", spouse_b="bob",
        ceremony_year=100, proposer="bob",
    ) is False


def test_marry_proposer_outside_couple_blocked():
    m = MarriageLegacy()
    assert m.marry(
        spouse_a="bob", spouse_b="cara",
        ceremony_year=100, proposer="dave",
    ) is False


def test_marry_already_married_blocked():
    m = MarriageLegacy()
    _wed(m, "bob", "cara")
    assert m.marry(
        spouse_a="bob", spouse_b="dave",
        ceremony_year=100, proposer="bob",
    ) is False


def test_deposit():
    m = MarriageLegacy()
    _wed(m)
    assert m.deposit(spouse="bob", slot_count=10) is True
    assert m.shared_inventory_used(spouse="cara") == 10


def test_deposit_overflow_blocked():
    m = MarriageLegacy()
    _wed(m)
    assert m.deposit(
        spouse="bob", slot_count=100,
    ) is False


def test_deposit_zero_blocked():
    m = MarriageLegacy()
    _wed(m)
    assert m.deposit(spouse="bob", slot_count=0) is False


def test_deposit_unknown_blocked():
    m = MarriageLegacy()
    assert m.deposit(
        spouse="ghost", slot_count=5,
    ) is False


def test_withdraw():
    m = MarriageLegacy()
    _wed(m)
    m.deposit(spouse="bob", slot_count=10)
    assert m.withdraw(
        spouse="cara", slot_count=4,
    ) is True
    assert m.shared_inventory_used(spouse="bob") == 6


def test_withdraw_more_than_avail_blocked():
    m = MarriageLegacy()
    _wed(m)
    m.deposit(spouse="bob", slot_count=5)
    assert m.withdraw(
        spouse="cara", slot_count=10,
    ) is False


def test_anniversary_year_zero_at_start():
    m = MarriageLegacy()
    _wed(m, year=100)
    assert m.anniversary_year(spouse="bob") == 0


def test_tick_year_grants_anniversary():
    m = MarriageLegacy()
    _wed(m, year=100)
    gifts = m.tick_year(now_year=101)
    assert len(gifts) == 1
    assert gifts[0].years_married == 1
    assert m.anniversary_year(spouse="bob") == 1


def test_tick_year_multiple_anniversaries():
    m = MarriageLegacy()
    _wed(m, year=100)
    gifts = m.tick_year(now_year=103)
    # 3 anniversaries fired
    assert len(gifts) == 3
    years = [g.years_married for g in gifts]
    assert years == [1, 2, 3]


def test_tick_year_grants_inventory_slots():
    m = MarriageLegacy()
    _wed(m, year=100)
    m.tick_year(now_year=101)
    mar = m.marriage(spouse="bob")
    # 30 base + 5 first anniversary
    assert mar.shared_inventory_capacity == 35


def test_initiate_divorce():
    m = MarriageLegacy()
    _wed(m)
    assert m.initiate_divorce(by_spouse="bob") is True
    assert m.marriage_state(
        spouse="bob",
    ) == MarriageState.DIVORCE_PENDING


def test_initiate_divorce_unknown():
    m = MarriageLegacy()
    assert m.initiate_divorce(
        by_spouse="ghost",
    ) is False


def test_accept_divorce_other_spouse():
    m = MarriageLegacy()
    _wed(m)
    m.initiate_divorce(by_spouse="bob")
    assert m.accept_divorce(by_spouse="cara") is True
    assert m.marriage_state(
        spouse="bob",
    ) == MarriageState.DIVORCED


def test_accept_divorce_initiator_blocked():
    """The divorce-initiator can't accept their own divorce."""
    m = MarriageLegacy()
    _wed(m)
    m.initiate_divorce(by_spouse="bob")
    assert m.accept_divorce(by_spouse="bob") is False


def test_accept_divorce_when_not_pending_blocked():
    m = MarriageLegacy()
    _wed(m)
    assert m.accept_divorce(by_spouse="cara") is False


def test_deposit_after_divorce_pending_blocked():
    m = MarriageLegacy()
    _wed(m)
    m.initiate_divorce(by_spouse="bob")
    assert m.deposit(
        spouse="cara", slot_count=5,
    ) is False


def test_divorce_clears_shared_inventory():
    m = MarriageLegacy()
    _wed(m)
    m.deposit(spouse="bob", slot_count=15)
    m.initiate_divorce(by_spouse="bob")
    m.accept_divorce(by_spouse="cara")
    mar = m.marriage(spouse="bob")
    assert mar.shared_inventory_used == 0
    assert mar.state == MarriageState.DIVORCED


def test_marriage_unknown_spouse():
    m = MarriageLegacy()
    assert m.marriage(spouse="ghost") is None


def test_three_marriage_states():
    assert len(list(MarriageState)) == 3
