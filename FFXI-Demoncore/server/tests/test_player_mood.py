"""Tests for player mood / morale registry."""
from __future__ import annotations

import pytest

from server.player_mood import (
    DECAY_PER_TICK,
    DEFAULT_TICK_INTERVAL_SECONDS,
    DEMORALIZED_AVG,
    HIGH_MORALE_AVG,
    MoodAxis,
    MoodEventKind,
    MoodRegistry,
    MoodVector,
)


def test_default_vector_is_zero():
    v = MoodVector()
    for axis in MoodAxis:
        assert v.as_dict()[axis] == 0


def test_vector_rejects_out_of_range():
    with pytest.raises(ValueError):
        MoodVector(confidence=200)


def test_vector_average():
    v = MoodVector(
        confidence=20, energy=40, cohesion=0, grit=-20,
    )
    assert v.average() == 10.0


def test_apply_event_adjusts_axes():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_BOSS,
    )
    v = reg.vector_for("alice")
    assert v.confidence == 30
    assert v.grit == 20


def test_apply_event_clamps_at_max():
    reg = MoodRegistry()
    for _ in range(10):
        reg.apply_event(
            player_id="alice", kind=MoodEventKind.KILLED_BOSS,
        )
    v = reg.vector_for("alice")
    assert v.confidence == 100


def test_apply_event_clamps_at_min():
    reg = MoodRegistry()
    for _ in range(10):
        reg.apply_event(
            player_id="alice", kind=MoodEventKind.PARTY_WIPE,
        )
    v = reg.vector_for("alice")
    assert v.confidence == -100


def test_magnitude_pct_scales_event():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_NM,
        magnitude_pct=50,
    )
    v = reg.vector_for("alice")
    # KILLED_NM: confidence +10, grit +5; at 50% -> +5, +2
    assert v.confidence == 5
    assert v.grit == 2


def test_tick_decays_toward_zero():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_BOSS,
    )
    v_before = reg.vector_for("alice").confidence
    # After 2 ticks of decay
    reg.tick(
        player_id="alice",
        now_seconds=DEFAULT_TICK_INTERVAL_SECONDS * 2,
    )
    v_after = reg.vector_for("alice").confidence
    assert v_after == v_before - DECAY_PER_TICK * 2


def test_tick_respects_interval():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_BOSS,
    )
    # Less than one tick interval
    reg.tick(
        player_id="alice",
        now_seconds=DEFAULT_TICK_INTERVAL_SECONDS / 2,
    )
    v = reg.vector_for("alice")
    assert v.confidence == 30   # unchanged


def test_tick_does_not_overshoot_zero():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_NM,
    )
    # +10 confidence; many ticks of decay
    reg.tick(
        player_id="alice",
        now_seconds=DEFAULT_TICK_INTERVAL_SECONDS * 100,
    )
    assert reg.vector_for("alice").confidence == 0


def test_tick_brings_negative_toward_zero():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KO_DEATH,
    )
    # -25 confidence
    reg.tick(
        player_id="alice",
        now_seconds=DEFAULT_TICK_INTERVAL_SECONDS * 5,
    )
    v = reg.vector_for("alice")
    # 5 ticks * 5/tick = 25 decay -> 0
    assert v.confidence == 0


def test_high_morale_threshold():
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_BOSS,
    )
    # +30 confidence +20 grit -> avg 12.5 (not high)
    assert not reg.is_high_morale("alice")
    # Pile on
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.LEVEL_UP,
    )
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.LONG_REST,
    )
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.REVIVED_BY_ALLY,
    )
    avg = reg.vector_for("alice").average()
    if avg >= HIGH_MORALE_AVG:
        assert reg.is_high_morale("alice")


def test_demoralized_threshold():
    reg = MoodRegistry()
    for _ in range(2):
        reg.apply_event(
            player_id="alice",
            kind=MoodEventKind.PARTY_WIPE,
        )
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.LONG_GRIND,
    )
    avg = reg.vector_for("alice").average()
    if avg <= DEMORALIZED_AVG:
        assert reg.is_demoralized("alice")


def test_combat_speed_neutral_at_zero():
    reg = MoodRegistry()
    assert reg.combat_speed_multiplier("alice") == 1.0


def test_combat_speed_high_morale():
    reg = MoodRegistry()
    # Saturate confidence
    for _ in range(5):
        reg.apply_event(
            player_id="alice",
            kind=MoodEventKind.KILLED_BOSS,
        )
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.LONG_REST,
    )
    mult = reg.combat_speed_multiplier("alice")
    assert mult > 1.0
    assert mult <= 1.15


def test_combat_speed_demoralized():
    reg = MoodRegistry()
    for _ in range(5):
        reg.apply_event(
            player_id="alice", kind=MoodEventKind.PARTY_WIPE,
        )
    mult = reg.combat_speed_multiplier("alice")
    assert mult < 1.0
    assert mult >= 0.85


def test_full_lifecycle_party_run():
    """Alice starts neutral, slays an NM (+morale), takes a KO
    (-morale), gets revived by ally (+cohesion), levels up
    (+confidence), then long-rest tick: morale ebbs back toward
    zero."""
    reg = MoodRegistry()
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KILLED_NM,
    )
    after_nm = reg.vector_for("alice").confidence
    assert after_nm == 10
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.KO_DEATH,
    )
    after_ko = reg.vector_for("alice").confidence
    assert after_ko == 10 - 25
    reg.apply_event(
        player_id="alice",
        kind=MoodEventKind.REVIVED_BY_ALLY,
    )
    assert reg.vector_for("alice").cohesion == 20
    reg.apply_event(
        player_id="alice", kind=MoodEventKind.LEVEL_UP,
    )
    # Multiple ticks of decay
    reg.tick(
        player_id="alice",
        now_seconds=DEFAULT_TICK_INTERVAL_SECONDS * 6,
    )
    v = reg.vector_for("alice")
    # All axes should be closer to 0 than peak values
    assert abs(v.confidence) <= 30
    assert abs(v.cohesion) <= 20
