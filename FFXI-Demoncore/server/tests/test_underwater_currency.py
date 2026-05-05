"""Tests for underwater currency."""
from __future__ import annotations

from server.underwater_currency import (
    Currency,
    UnderwaterCurrency,
)


def test_initial_balance_zero():
    c = UnderwaterCurrency()
    assert c.balance(
        player_id="p", currency=Currency.CORAL_SHELL,
    ) == 0


def test_gain_happy():
    c = UnderwaterCurrency()
    r = c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=500,
    )
    assert r.accepted is True
    assert r.granted == 500
    assert r.truncated == 0
    assert r.new_balance == 500


def test_gain_blank_player():
    c = UnderwaterCurrency()
    r = c.gain(
        player_id="",
        currency=Currency.CORAL_SHELL,
        amount=10,
    )
    assert r.accepted is False


def test_gain_zero_amount_rejected():
    c = UnderwaterCurrency()
    r = c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=0,
    )
    assert r.accepted is False


def test_gain_truncates_at_cap():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=99_500,
    )
    r = c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=1_000,
    )
    assert r.accepted is True
    assert r.granted == 499
    assert r.truncated == 501
    assert r.new_balance == 99_999


def test_gain_at_cap_returns_zero_granted():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=99_999,
    )
    r = c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=100,
    )
    assert r.accepted is True
    assert r.granted == 0
    assert r.truncated == 100


def test_spend_happy():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=500,
    )
    r = c.spend(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=200,
    )
    assert r.accepted is True
    assert r.spent == 200
    assert r.new_balance == 300


def test_spend_insufficient():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=50,
    )
    r = c.spend(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=200,
    )
    assert r.accepted is False
    assert r.reason == "insufficient"


def test_spend_unknown_player():
    c = UnderwaterCurrency()
    r = c.spend(
        player_id="ghost",
        currency=Currency.CORAL_SHELL,
        amount=10,
    )
    assert r.accepted is False


def test_convert_happy():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=300,
    )
    r = c.convert_shells_to_pearls(
        player_id="p",
        shells_to_convert=300,
    )
    assert r.accepted is True
    assert r.shells_consumed == 300
    assert r.pearls_granted == 3
    assert r.new_shell_balance == 0
    assert r.new_pearl_balance == 3


def test_convert_must_be_multiple_of_100():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=200,
    )
    r = c.convert_shells_to_pearls(
        player_id="p",
        shells_to_convert=150,
    )
    assert r.accepted is False
    assert r.reason == "must be multiple of 100"


def test_convert_zero_amount():
    c = UnderwaterCurrency()
    r = c.convert_shells_to_pearls(
        player_id="p",
        shells_to_convert=0,
    )
    assert r.accepted is False


def test_convert_insufficient_shells():
    c = UnderwaterCurrency()
    r = c.convert_shells_to_pearls(
        player_id="p",
        shells_to_convert=100,
    )
    assert r.accepted is False


def test_pearl_cap_truncates_during_convert():
    c = UnderwaterCurrency()
    c.gain(
        player_id="p",
        currency=Currency.SEAPEARL,
        amount=9_999,
    )
    c.gain(
        player_id="p",
        currency=Currency.CORAL_SHELL,
        amount=200,
    )
    # converting 200 -> 2 pearls but cap is full -> 0 granted
    r = c.convert_shells_to_pearls(
        player_id="p",
        shells_to_convert=200,
    )
    assert r.accepted is True
    assert r.pearls_granted == 0
    # shells were still consumed (deliberate sink)
    assert r.new_shell_balance == 0
