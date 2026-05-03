"""Tests for status slot manager + displacement rules."""
from __future__ import annotations

from server.status_slot_manager import (
    ApplyOutcome,
    Effect,
    SlotCategory,
    StatusSlotManager,
)


def _bio(target: str = "boss", tier: int = 1, **kwargs) -> Effect:
    base = dict(
        target_id=target,
        category=SlotCategory.BIO_FAMILY,
        effect_id=f"bio_{tier}",
        tier=tier, duration_seconds=120,
        caster_id="alice",
        applied_at_seconds=0.0,
    )
    base.update(kwargs)
    return Effect(**base)


def test_first_apply_lands():
    mgr = StatusSlotManager()
    res = mgr.apply(effect=_bio())
    assert res.outcome == ApplyOutcome.APPLIED


def test_apply_zero_duration_rejected():
    mgr = StatusSlotManager()
    res = mgr.apply(
        effect=_bio(duration_seconds=0),
    )
    assert res.outcome == ApplyOutcome.REJECTED


def test_apply_negative_tier_rejected():
    mgr = StatusSlotManager()
    res = mgr.apply(effect=_bio(tier=-1))
    assert res.outcome == ApplyOutcome.REJECTED


def test_higher_tier_displaces_lower():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(tier=1))
    res = mgr.apply(effect=_bio(tier=3))
    assert res.outcome == ApplyOutcome.DISPLACED
    assert res.displaced_effect.tier == 1
    assert res.effect.tier == 3
    # Slot now has tier 3
    slot = mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    )
    assert slot.tier == 3


def test_same_tier_refreshes():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(
        tier=2, duration_seconds=100,
        applied_at_seconds=0.0,
    ))
    res = mgr.apply(effect=_bio(
        tier=2, duration_seconds=180,
        applied_at_seconds=50.0,
        caster_id="bob",
    ))
    assert res.outcome == ApplyOutcome.REFRESHED
    slot = mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    )
    assert slot.duration_seconds == 180
    assert slot.caster_id == "bob"


def test_lower_tier_rejected():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(tier=3))
    res = mgr.apply(effect=_bio(tier=1))
    assert res.outcome == ApplyOutcome.REJECTED


def test_different_category_does_not_displace():
    """Bio and Dia are distinct categories; both can co-exist."""
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio())
    dia = Effect(
        target_id="boss",
        category=SlotCategory.DIA_FAMILY,
        effect_id="dia_3", tier=3,
        duration_seconds=120,
    )
    res = mgr.apply(effect=dia)
    assert res.outcome == ApplyOutcome.APPLIED
    # Both slots present
    active = mgr.active_slots("boss")
    cats = {e.category for e in active}
    assert cats == {
        SlotCategory.BIO_FAMILY, SlotCategory.DIA_FAMILY,
    }


def test_different_targets_isolated():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(target="boss_a", tier=1))
    mgr.apply(effect=_bio(target="boss_b", tier=3))
    a = mgr.get_slot(
        target_id="boss_a", category=SlotCategory.BIO_FAMILY,
    )
    b = mgr.get_slot(
        target_id="boss_b", category=SlotCategory.BIO_FAMILY,
    )
    assert a.tier == 1
    assert b.tier == 3


def test_clear_slot():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio())
    assert mgr.clear_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    )
    assert mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    ) is None


def test_clear_unknown_slot_returns_false():
    mgr = StatusSlotManager()
    assert not mgr.clear_slot(
        target_id="ghost", category=SlotCategory.BIO_FAMILY,
    )


def test_tick_drops_expired():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(
        duration_seconds=60, applied_at_seconds=0.0,
    ))
    # Tick past expiry
    dropped = mgr.tick(target_id="boss", now_seconds=100.0)
    assert len(dropped) == 1
    assert mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    ) is None


def test_tick_keeps_active_effects():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(
        duration_seconds=60, applied_at_seconds=0.0,
    ))
    dropped = mgr.tick(target_id="boss", now_seconds=30.0)
    assert dropped == ()
    assert mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    ) is not None


def test_active_slots_lists_all():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(target="alice"))
    haste = Effect(
        target_id="alice",
        category=SlotCategory.HASTE,
        effect_id="haste_ii", tier=2,
        duration_seconds=180,
    )
    mgr.apply(effect=haste)
    actives = mgr.active_slots("alice")
    assert len(actives) == 2


def test_total_active_count():
    mgr = StatusSlotManager()
    mgr.apply(effect=_bio(target="a"))
    mgr.apply(effect=_bio(target="b"))
    assert mgr.total_active() == 2


def test_full_lifecycle_bio_displacement_cycle():
    """Bio I -> Bio II (displace) -> Bio II again (refresh) ->
    Bio I (rejected) -> tick past expiry (cleared)."""
    mgr = StatusSlotManager()
    r1 = mgr.apply(effect=_bio(tier=1, applied_at_seconds=0.0))
    assert r1.outcome == ApplyOutcome.APPLIED
    r2 = mgr.apply(effect=_bio(tier=2, applied_at_seconds=10.0))
    assert r2.outcome == ApplyOutcome.DISPLACED
    r3 = mgr.apply(effect=_bio(
        tier=2, duration_seconds=200, applied_at_seconds=50.0,
    ))
    assert r3.outcome == ApplyOutcome.REFRESHED
    assert mgr.get_slot(
        target_id="boss", category=SlotCategory.BIO_FAMILY,
    ).duration_seconds == 200
    r4 = mgr.apply(effect=_bio(tier=1))
    assert r4.outcome == ApplyOutcome.REJECTED
    # Tick past
    dropped = mgr.tick(target_id="boss", now_seconds=300.0)
    assert len(dropped) == 1
