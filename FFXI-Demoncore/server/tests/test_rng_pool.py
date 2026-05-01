"""Tests for the deterministic RNG pool."""
from __future__ import annotations

import pytest

from server.rng_pool import (
    KNOWN_STREAMS,
    STREAM_BOSS_CRITIC,
    STREAM_FOMOR_GEAR,
    STREAM_LOOT_DROPS,
    RngPool,
)


# -- determinism -------------------------------------------------------

def test_same_seed_yields_same_first_draw():
    a = RngPool(world_seed=42)
    b = RngPool(world_seed=42)
    assert a.randint(STREAM_LOOT_DROPS, 0, 1_000_000) == \
           b.randint(STREAM_LOOT_DROPS, 0, 1_000_000)


def test_same_seed_long_sequence_matches():
    a = RngPool(world_seed=1234)
    b = RngPool(world_seed=1234)
    a_seq = [a.randint(STREAM_BOSS_CRITIC, 0, 99) for _ in range(50)]
    b_seq = [b.randint(STREAM_BOSS_CRITIC, 0, 99) for _ in range(50)]
    assert a_seq == b_seq


def test_different_world_seeds_diverge():
    a = RngPool(world_seed=1)
    b = RngPool(world_seed=2)
    a_seq = [a.randint(STREAM_LOOT_DROPS, 0, 99) for _ in range(20)]
    b_seq = [b.randint(STREAM_LOOT_DROPS, 0, 99) for _ in range(20)]
    assert a_seq != b_seq


def test_streams_are_independent():
    """Drawing from one stream must NOT consume entropy of another.

    This is the core anti-tampering property: a loot roll cannot
    accidentally shift the boss-critic stream's next draw."""
    pool = RngPool(world_seed=7)
    boss_baseline = [pool.randint(STREAM_BOSS_CRITIC, 0, 999_999)
                     for _ in range(10)]

    pool2 = RngPool(world_seed=7)
    # Drain a different stream first.
    for _ in range(50):
        pool2.randint(STREAM_LOOT_DROPS, 0, 999_999)
    # Now read boss critic — should match.
    boss_after = [pool2.randint(STREAM_BOSS_CRITIC, 0, 999_999)
                  for _ in range(10)]

    assert boss_baseline == boss_after


def test_known_streams_constant_includes_core_use_cases():
    assert STREAM_LOOT_DROPS in KNOWN_STREAMS
    assert STREAM_BOSS_CRITIC in KNOWN_STREAMS
    assert STREAM_FOMOR_GEAR in KNOWN_STREAMS


def test_stream_names_collide_safely():
    """Even similar-looking names must derive distinct seeds."""
    a = RngPool(world_seed=99)
    seq_a = [a.randint("foo", 0, 999) for _ in range(20)]

    b = RngPool(world_seed=99)
    seq_b = [b.randint("foo_", 0, 999) for _ in range(20)]
    assert seq_a != seq_b


# -- convenience draws -------------------------------------------------

def test_randint_respects_bounds():
    pool = RngPool(world_seed=0)
    for _ in range(100):
        v = pool.randint(STREAM_LOOT_DROPS, 5, 10)
        assert 5 <= v <= 10


def test_uniform_respects_bounds():
    pool = RngPool(world_seed=0)
    for _ in range(100):
        v = pool.uniform(STREAM_LOOT_DROPS, 1.0, 3.0)
        assert 1.0 <= v <= 3.0


def test_choice_returns_one_of_inputs():
    pool = RngPool(world_seed=0)
    items = ["raise", "raise_ii", "raise_iii", "tractor"]
    for _ in range(50):
        pick = pool.choice(STREAM_LOOT_DROPS, items)
        assert pick in items


def test_choice_empty_raises():
    pool = RngPool(world_seed=0)
    with pytest.raises(IndexError):
        pool.choice(STREAM_LOOT_DROPS, [])


def test_roll_pct_is_inclusive_0_to_100():
    pool = RngPool(world_seed=0)
    for _ in range(500):
        v = pool.roll_pct(STREAM_LOOT_DROPS)
        assert 0 <= v <= 100


def test_gate_zero_is_always_false():
    pool = RngPool(world_seed=0)
    for _ in range(100):
        assert pool.gate(STREAM_BOSS_CRITIC, 0.0) is False


def test_gate_one_is_always_true():
    pool = RngPool(world_seed=0)
    for _ in range(100):
        assert pool.gate(STREAM_BOSS_CRITIC, 1.0) is True


def test_gate_invalid_probability_raises():
    pool = RngPool(world_seed=0)
    with pytest.raises(ValueError):
        pool.gate(STREAM_BOSS_CRITIC, -0.1)
    with pytest.raises(ValueError):
        pool.gate(STREAM_BOSS_CRITIC, 1.1)


def test_gate_50_50_is_both_true_and_false_over_many_draws():
    """Sanity check — not testing rate exactly, just that it isn't
    stuck on one outcome."""
    pool = RngPool(world_seed=12345)
    results = [pool.gate(STREAM_LOOT_DROPS, 0.5) for _ in range(200)]
    assert True in results
    assert False in results


# -- replay control ----------------------------------------------------

def test_reset_one_stream_replays_same_sequence():
    pool = RngPool(world_seed=999)
    first = [pool.randint(STREAM_BOSS_CRITIC, 0, 1000) for _ in range(10)]
    pool.reset(STREAM_BOSS_CRITIC)
    replayed = [pool.randint(STREAM_BOSS_CRITIC, 0, 1000)
                for _ in range(10)]
    assert first == replayed


def test_reset_one_stream_does_not_affect_others():
    pool = RngPool(world_seed=999)
    # Drain boss_critic
    for _ in range(10):
        pool.randint(STREAM_BOSS_CRITIC, 0, 1000)
    # Take a fomor_gear sample
    fg_first = [pool.randint(STREAM_FOMOR_GEAR, 0, 1000)
                for _ in range(5)]
    pool.reset(STREAM_BOSS_CRITIC)
    # fomor_gear continues from where it was, not from the start.
    fg_next = [pool.randint(STREAM_FOMOR_GEAR, 0, 1000)
               for _ in range(5)]
    assert fg_first != fg_next


def test_reset_all_replays_everything():
    pool = RngPool(world_seed=999)
    a = [pool.randint(STREAM_BOSS_CRITIC, 0, 1000) for _ in range(5)]
    b = [pool.randint(STREAM_LOOT_DROPS, 0, 1000) for _ in range(5)]
    pool.reset_all()
    a2 = [pool.randint(STREAM_BOSS_CRITIC, 0, 1000) for _ in range(5)]
    b2 = [pool.randint(STREAM_LOOT_DROPS, 0, 1000) for _ in range(5)]
    assert a == a2
    assert b == b2


# -- introspection -----------------------------------------------------

def test_active_streams_reports_only_used_streams():
    pool = RngPool(world_seed=0)
    assert pool.active_streams() == ()
    pool.randint(STREAM_LOOT_DROPS, 0, 1)
    pool.randint(STREAM_BOSS_CRITIC, 0, 1)
    assert set(pool.active_streams()) == {
        STREAM_LOOT_DROPS, STREAM_BOSS_CRITIC,
    }


def test_stream_returns_same_random_instance_for_same_name():
    """Calling stream() twice must return the same Random object,
    not re-seed mid-flight."""
    pool = RngPool(world_seed=0)
    a = pool.stream(STREAM_BOSS_CRITIC)
    b = pool.stream(STREAM_BOSS_CRITIC)
    assert a is b


# -- composition ------------------------------------------------------

def test_full_replay_scene():
    """Simulated boss fight: roll boss-critic gate, draw a loot
    item, draw a fomor gear color. Reset, replay, observe identical
    outcomes."""
    pool = RngPool(world_seed=0xDECAFBAD)
    items = ["mythril_sword", "ridill", "kraken_club"]
    colors = ["red", "blue", "green", "violet"]

    take1 = (
        pool.gate(STREAM_BOSS_CRITIC, 0.30),
        pool.choice(STREAM_LOOT_DROPS, items),
        pool.choice(STREAM_FOMOR_GEAR, colors),
    )
    pool.reset_all()
    take2 = (
        pool.gate(STREAM_BOSS_CRITIC, 0.30),
        pool.choice(STREAM_LOOT_DROPS, items),
        pool.choice(STREAM_FOMOR_GEAR, colors),
    )
    assert take1 == take2
