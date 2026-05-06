"""Tests for hunger_thirst."""
from __future__ import annotations

from server.hunger_thirst import HungerThirstEngine, NeedTier


def test_register_happy():
    e = HungerThirstEngine()
    assert e.register(player_id="alice") is True
    assert e.hunger_for(player_id="alice") == 100
    assert e.thirst_for(player_id="alice") == 100


def test_blank_player_blocked():
    e = HungerThirstEngine()
    assert e.register(player_id="") is False


def test_double_register_blocked():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    assert e.register(player_id="alice") is False


def test_tick_drains():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=10)
    assert e.hunger_for(player_id="alice") == 90
    assert e.thirst_for(player_id="alice") == 80


def test_combat_doubles_thirst():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=10, in_combat=True)
    # 2 * 2 = 4 per sec; 10 sec = 40
    assert e.thirst_for(player_id="alice") == 60


def test_decay_floors_at_zero():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=200)
    assert e.hunger_for(player_id="alice") == 0
    assert e.thirst_for(player_id="alice") == 0


def test_eat_restores():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=50)
    e.eat(player_id="alice", restore=20)
    assert e.hunger_for(player_id="alice") == 70


def test_eat_caps_at_100():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.eat(player_id="alice", restore=50)
    assert e.hunger_for(player_id="alice") == 100


def test_drink_restores():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=20)
    e.drink(player_id="alice", restore=30)
    assert e.thirst_for(player_id="alice") == 90


def test_drink_caps_at_100():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.drink(player_id="alice", restore=999)
    assert e.thirst_for(player_id="alice") == 100


def test_negative_restore_no_op():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=10)
    e.eat(player_id="alice", restore=-5)
    assert e.hunger_for(player_id="alice") == 90


def test_tier_sated():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    assert e.tier_for(player_id="alice") == NeedTier.SATED


def test_tier_peckish_at_50():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=50)
    # hunger=50, thirst=0 → DEHYDRATED dominates
    # use only-hunger view:
    e.drink(player_id="alice", restore=100)
    assert e.tier_for(player_id="alice") == NeedTier.PECKISH


def test_tier_starving():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=95)
    e.drink(player_id="alice", restore=100)
    # hunger=5, → STARVING
    assert e.tier_for(player_id="alice") == NeedTier.STARVING


def test_tier_dehydrated():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    # thirst goes to 0 fast; reset hunger to keep test focused
    e.tick(player_id="alice", dt_seconds=50)
    e.eat(player_id="alice", restore=100)
    # at thirst=0
    assert e.tier_for(player_id="alice") == NeedTier.DEHYDRATED


def test_thirst_tier_priority_when_worse():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=15)  # hunger=85, thirst=70
    # both sated
    assert e.tier_for(player_id="alice") == NeedTier.SATED


def test_hunger_tier_when_worse_than_thirst():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    e.tick(player_id="alice", dt_seconds=80)  # hunger=20, thirst=0
    # both bad — DEHYDRATED is rank 3; HUNGRY is rank 2; thirst returns
    assert e.tier_for(player_id="alice") == NeedTier.DEHYDRATED


def test_unknown_player_sated():
    e = HungerThirstEngine()
    assert e.tier_for(player_id="ghost") == NeedTier.SATED


def test_seven_need_tiers():
    assert len(list(NeedTier)) == 7


def test_tick_returns_current_tier():
    e = HungerThirstEngine()
    e.register(player_id="alice")
    out = e.tick(player_id="alice", dt_seconds=1)
    assert out == NeedTier.SATED
