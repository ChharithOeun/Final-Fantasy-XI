"""Tests for addon_event_bus."""
from __future__ import annotations

from server.addon_event_bus import AddonEventBus, EventEnvelope


def _env(hook="on_damage", source="goblin", ts=10, **payload):
    return EventEnvelope(
        hook_name=hook, source_id=source,
        payload=payload, fired_at=ts,
    )


def test_subscribe_happy():
    b = AddonEventBus()
    ok = b.subscribe(
        subscriber_id="dpsmeter:alice", hook_name="on_damage",
    )
    assert ok is True


def test_subscribe_blank_subscriber_blocked():
    b = AddonEventBus()
    out = b.subscribe(
        subscriber_id="", hook_name="on_damage",
    )
    assert out is False


def test_subscribe_blank_hook_blocked():
    b = AddonEventBus()
    out = b.subscribe(
        subscriber_id="x", hook_name="",
    )
    assert out is False


def test_subscribe_duplicate_blocked():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    out = b.subscribe(subscriber_id="x", hook_name="on_damage")
    assert out is False


def test_subscribe_same_sub_different_hooks():
    b = AddonEventBus()
    assert b.subscribe(subscriber_id="x", hook_name="a") is True
    assert b.subscribe(subscriber_id="x", hook_name="b") is True


def test_unsubscribe_happy():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    out = b.unsubscribe(subscriber_id="x", hook_name="on_damage")
    assert out is True


def test_unsubscribe_unknown_hook():
    b = AddonEventBus()
    out = b.unsubscribe(subscriber_id="x", hook_name="ghost")
    assert out is False


def test_unsubscribe_unknown_subscriber():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    out = b.unsubscribe(subscriber_id="y", hook_name="on_damage")
    assert out is False


def test_unsubscribe_all():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="a")
    b.subscribe(subscriber_id="x", hook_name="b")
    b.subscribe(subscriber_id="x", hook_name="c")
    out = b.unsubscribe_all(subscriber_id="x")
    assert out == 3


def test_unsubscribe_all_unknown():
    b = AddonEventBus()
    out = b.unsubscribe_all(subscriber_id="ghost")
    assert out == 0


def test_publish_delivers_to_all_subs():
    b = AddonEventBus()
    b.subscribe(subscriber_id="dpsmeter:alice", hook_name="on_damage")
    b.subscribe(subscriber_id="dpsmeter:bob", hook_name="on_damage")
    b.subscribe(
        subscriber_id="gearswap:maat", hook_name="on_damage",
    )
    out = b.publish(envelope=_env(hook="on_damage"))
    assert out == 3


def test_publish_no_subscribers():
    b = AddonEventBus()
    out = b.publish(envelope=_env(hook="ghost_hook"))
    assert out == 0


def test_publish_isolated_hooks():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="a")
    b.subscribe(subscriber_id="y", hook_name="b")
    # publish only triggers "a" subscribers
    out = b.publish(envelope=_env(hook="a"))
    assert out == 1


def test_subscribers_for():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    b.subscribe(subscriber_id="y", hook_name="on_damage")
    out = b.subscribers_for(hook_name="on_damage")
    assert sorted(out) == ["x", "y"]


def test_subscribers_for_unknown_empty():
    b = AddonEventBus()
    assert b.subscribers_for(hook_name="ghost") == []


def test_subscriptions_for():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="a")
    b.subscribe(subscriber_id="x", hook_name="b")
    out = b.subscriptions_for(subscriber_id="x")
    assert sorted(out) == ["a", "b"]


def test_subscriptions_for_unknown_empty():
    b = AddonEventBus()
    assert b.subscriptions_for(subscriber_id="ghost") == []


def test_npc_and_player_share_bus():
    """The whole point: mob addons + player addons on same bus."""
    b = AddonEventBus()
    b.subscribe(
        subscriber_id="player:alice:gearswap",
        hook_name="on_engaged",
    )
    b.subscribe(
        subscriber_id="boss:maat:gearswap",
        hook_name="on_engaged",
    )
    out = b.publish(envelope=_env(hook="on_engaged"))
    assert out == 2


def test_delivery_count_tracks_publishes():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    b.publish(envelope=_env(hook="on_damage"))
    b.publish(envelope=_env(hook="on_damage"))
    assert b.delivery_count(hook_name="on_damage") == 2


def test_total_subscriptions():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="a")
    b.subscribe(subscriber_id="x", hook_name="b")
    b.subscribe(subscriber_id="y", hook_name="a")
    assert b.total_subscriptions() == 3


def test_unsubscribe_then_publish_misses_them():
    b = AddonEventBus()
    b.subscribe(subscriber_id="x", hook_name="on_damage")
    b.subscribe(subscriber_id="y", hook_name="on_damage")
    b.unsubscribe(subscriber_id="x", hook_name="on_damage")
    out = b.publish(envelope=_env(hook="on_damage"))
    assert out == 1
