"""Tests for the beastman alt-currency converter."""
from __future__ import annotations

from server.beastman_alt_currency import (
    BeastmanAltCurrency,
    BeastmanCurrency,
)


def test_grant_basic():
    a = BeastmanAltCurrency()
    res = a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=100,
    )
    assert res.accepted
    assert res.new_balance == 100


def test_grant_accumulates():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=100,
    )
    res = a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=50,
    )
    assert res.new_balance == 150


def test_grant_zero_rejected():
    a = BeastmanAltCurrency()
    res = a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=0,
    )
    assert not res.accepted


def test_balance_default_zero():
    a = BeastmanAltCurrency()
    assert a.balance(
        player_id="ghost",
        currency=BeastmanCurrency.CORAL_SCALE,
    ) == 0


def test_exchange_feather_to_bytne():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=100,
    )
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=100,
    )
    assert res.accepted
    assert res.src_consumed == 100
    assert res.dst_received == 60
    assert res.src_balance_after == 0
    assert res.dst_balance_after == 60


def test_exchange_round_trip_loses_value():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=1000,
    )
    a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=1000,
    )
    # 1000 → 600 bytnes → back to 180 feathers
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.SHADOW_BYTNE,
        dst=BeastmanCurrency.PRIME_FEATHER,
        src_amount=600,
    )
    assert res.dst_received == 180
    # Final balance: 0 feathers traded → 180 feathers = 82% loss
    assert a.balance(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
    ) == 180


def test_exchange_insufficient_balance():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=10,
    )
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=100,
    )
    assert not res.accepted


def test_exchange_no_rate():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=100,
    )
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.CORAL_SCALE,
        src_amount=50,
    )
    assert not res.accepted


def test_exchange_same_currency_rejected():
    a = BeastmanAltCurrency()
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.PRIME_FEATHER,
        src_amount=10,
    )
    assert not res.accepted


def test_exchange_zero_amount_rejected():
    a = BeastmanAltCurrency()
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=0,
    )
    assert not res.accepted


def test_exchange_too_small_for_rate():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.SHADOW_BYTNE,
        amount=2,
    )
    # 2 * 30 / 100 = 0 — rounds to 0, rejected
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.SHADOW_BYTNE,
        dst=BeastmanCurrency.PRIME_FEATHER,
        src_amount=2,
    )
    assert not res.accepted


def test_set_rate_updates():
    a = BeastmanAltCurrency()
    assert a.set_rate(
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        rate_pct=80,
    )
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=100,
    )
    res = a.exchange(
        player_id="kraw",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=100,
    )
    assert res.dst_received == 80


def test_set_rate_same_currency_rejected():
    a = BeastmanAltCurrency()
    res = a.set_rate(
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.PRIME_FEATHER,
        rate_pct=100,
    )
    assert not res


def test_set_rate_out_of_range_rejected():
    a = BeastmanAltCurrency()
    res = a.set_rate(
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        rate_pct=500,
    )
    assert not res


def test_get_rate_known():
    a = BeastmanAltCurrency()
    assert a.get_rate(
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
    ) == 60


def test_get_rate_unknown():
    a = BeastmanAltCurrency()
    assert a.get_rate(
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.CORAL_SCALE,
    ) is None


def test_per_player_isolation():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="alice",
        currency=BeastmanCurrency.REAVER_BONE,
        amount=50,
    )
    assert a.balance(
        player_id="bob",
        currency=BeastmanCurrency.REAVER_BONE,
    ) == 0


def test_total_currencies_held():
    a = BeastmanAltCurrency()
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.PRIME_FEATHER,
        amount=10,
    )
    a.grant(
        player_id="kraw",
        currency=BeastmanCurrency.LACQUERED_STONE,
        amount=20,
    )
    assert a.total_currencies_held(player_id="kraw") == 30


def test_all_four_races_to_bytne():
    a = BeastmanAltCurrency()
    for c in (
        BeastmanCurrency.PRIME_FEATHER,
        BeastmanCurrency.LACQUERED_STONE,
        BeastmanCurrency.CORAL_SCALE,
        BeastmanCurrency.REAVER_BONE,
    ):
        a.grant(player_id="kraw", currency=c, amount=100)
        res = a.exchange(
            player_id="kraw",
            src=c,
            dst=BeastmanCurrency.SHADOW_BYTNE,
            src_amount=100,
        )
        assert res.accepted
    assert a.balance(
        player_id="kraw",
        currency=BeastmanCurrency.SHADOW_BYTNE,
    ) == 240


def test_exchange_unknown_player_no_balance():
    a = BeastmanAltCurrency()
    res = a.exchange(
        player_id="ghost",
        src=BeastmanCurrency.PRIME_FEATHER,
        dst=BeastmanCurrency.SHADOW_BYTNE,
        src_amount=10,
    )
    assert not res.accepted
