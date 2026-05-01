"""Tests for the synergy cooldown tracker."""
from __future__ import annotations

import pytest

from server.automaton_synergy import CooldownTracker


def test_new_tracker_says_can_trigger_anything():
    cd = CooldownTracker()
    assert cd.can_trigger(
        master_id="alice", ability_id="death_spikes",
        now_tick=1000,
    )
    assert cd.next_available(
        master_id="alice", ability_id="death_spikes",
    ) is None


def test_trigger_records_lockout():
    cd = CooldownTracker()
    next_avail = cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert next_avail == 1900


def test_can_trigger_false_during_lockout():
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    # Mid-lockout
    assert not cd.can_trigger(
        master_id="alice", ability_id="death_spikes",
        now_tick=1500,
    )


def test_can_trigger_true_at_exact_expiry():
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert cd.can_trigger(
        master_id="alice", ability_id="death_spikes",
        now_tick=1900,
    )


def test_can_trigger_true_after_expiry():
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert cd.can_trigger(
        master_id="alice", ability_id="death_spikes",
        now_tick=2000,
    )


def test_remaining_seconds_decrements_with_time():
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert cd.remaining(
        master_id="alice", ability_id="death_spikes",
        now_tick=1000,
    ) == 900
    assert cd.remaining(
        master_id="alice", ability_id="death_spikes",
        now_tick=1500,
    ) == 400
    assert cd.remaining(
        master_id="alice", ability_id="death_spikes",
        now_tick=2000,
    ) == 0


def test_per_master_isolation():
    """Alice and Bob both fire the same ability — Alice on
    cooldown, Bob still free."""
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert not cd.can_trigger(
        master_id="alice", ability_id="death_spikes",
        now_tick=1500,
    )
    assert cd.can_trigger(
        master_id="bob", ability_id="death_spikes",
        now_tick=1500,
    )


def test_per_ability_isolation():
    """Alice fires Death Spikes — her Stoneskin cooldown shouldn't
    be affected."""
    cd = CooldownTracker()
    cd.trigger(
        master_id="alice", ability_id="death_spikes",
        cooldown_seconds=900, now_tick=1000,
    )
    assert cd.can_trigger(
        master_id="alice", ability_id="aoe_stoneskin",
        now_tick=1500,
    )


def test_negative_cooldown_raises():
    cd = CooldownTracker()
    with pytest.raises(ValueError):
        cd.trigger(
            master_id="alice", ability_id="x",
            cooldown_seconds=-1, now_tick=1000,
        )


def test_clear_all():
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="alice", ability_id="b",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="bob", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    n = cd.clear()
    assert n == 3
    assert cd.can_trigger(
        master_id="alice", ability_id="a", now_tick=10,
    )


def test_clear_only_master():
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="alice", ability_id="b",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="bob", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    n = cd.clear(master_id="alice")
    assert n == 2
    # Bob's cooldown survived.
    assert not cd.can_trigger(
        master_id="bob", ability_id="a", now_tick=10,
    )


def test_clear_only_ability():
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="bob", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="alice", ability_id="b",
               cooldown_seconds=100, now_tick=0)
    n = cd.clear(ability_id="a")
    assert n == 2
    assert not cd.can_trigger(
        master_id="alice", ability_id="b", now_tick=10,
    )


def test_clear_specific_entry():
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="alice", ability_id="b",
               cooldown_seconds=100, now_tick=0)
    n = cd.clear(master_id="alice", ability_id="a")
    assert n == 1
    assert cd.can_trigger(
        master_id="alice", ability_id="a", now_tick=10,
    )
    assert not cd.can_trigger(
        master_id="alice", ability_id="b", now_tick=10,
    )


def test_active_count():
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    cd.trigger(master_id="bob", ability_id="b",
               cooldown_seconds=200, now_tick=0)
    assert cd.active_count(now_tick=50) == 2
    assert cd.active_count(now_tick=150) == 1
    assert cd.active_count(now_tick=300) == 0


def test_re_trigger_resets_lockout():
    """Firing the same ability twice should restart the cooldown
    from the second firing's tick."""
    cd = CooldownTracker()
    cd.trigger(master_id="alice", ability_id="a",
               cooldown_seconds=100, now_tick=0)
    # Mid-cooldown is technically impossible (caller is supposed
    # to gate via can_trigger), but if it happens, the second
    # call must overwrite, not stack.
    next2 = cd.trigger(master_id="alice", ability_id="a",
                       cooldown_seconds=200, now_tick=50)
    assert next2 == 250
    assert cd.next_available(
        master_id="alice", ability_id="a",
    ) == 250
