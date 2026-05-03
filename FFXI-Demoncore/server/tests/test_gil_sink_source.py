"""Tests for the gil flow tracker."""
from __future__ import annotations

import pytest

from server.gil_sink_source import (
    CRISIS_INFLATION,
    DEFLATION_THRESHOLD,
    GAME_DAY_SECONDS,
    GilEconomyState,
    GilFlowTracker,
    GilSinkKind,
    GilSourceKind,
    INFLATION_THRESHOLD,
)


def test_record_source_zero_or_negative_rejected():
    t = GilFlowTracker()
    with pytest.raises(ValueError):
        t.record_source(
            kind=GilSourceKind.MOB_DROP, amount=0,
            now_seconds=0.0,
        )
    with pytest.raises(ValueError):
        t.record_source(
            kind=GilSourceKind.MOB_DROP, amount=-100,
            now_seconds=0.0,
        )


def test_record_sink_zero_or_negative_rejected():
    t = GilFlowTracker()
    with pytest.raises(ValueError):
        t.record_sink(
            kind=GilSinkKind.NPC_VENDOR_BUY, amount=-50,
            now_seconds=0.0,
        )


def test_total_source_and_sink():
    t = GilFlowTracker()
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=1000,
        now_seconds=0.0,
    )
    t.record_source(
        kind=GilSourceKind.NM_DROP, amount=2000,
        now_seconds=0.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=500,
        now_seconds=0.0,
    )
    assert t.total_source_gil(now_seconds=0.0) == 3000
    assert t.total_sink_gil(now_seconds=0.0) == 500


def test_net_flow_per_day_window_full_day():
    """Source = 100k, sink = 30k over 1 day -> net 70k/day."""
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=100_000,
        now_seconds=100.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=30_000,
        now_seconds=200.0,
    )
    net = t.net_flow_per_day(now_seconds=GAME_DAY_SECONDS)
    assert net == 70_000


def test_state_healthy_within_band():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=50_000,
        now_seconds=0.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=40_000,
        now_seconds=0.0,
    )
    assert t.state_at(
        now_seconds=GAME_DAY_SECONDS,
    ) == GilEconomyState.HEALTHY


def test_state_inflating_above_threshold():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.NM_DROP,
        amount=INFLATION_THRESHOLD + 50_000,
        now_seconds=0.0,
    )
    state = t.state_at(now_seconds=GAME_DAY_SECONDS)
    assert state == GilEconomyState.INFLATING


def test_state_crisis_inflation():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.NM_DROP,
        amount=CRISIS_INFLATION + 100,
        now_seconds=0.0,
    )
    state = t.state_at(now_seconds=GAME_DAY_SECONDS)
    assert state == GilEconomyState.CRISIS_INFLATION


def test_state_deflating_below_threshold():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    # Sinks > sources by 250k
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=50_000,
        now_seconds=0.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY,
        amount=50_000 + abs(DEFLATION_THRESHOLD) + 50_000,
        now_seconds=0.0,
    )
    state = t.state_at(now_seconds=GAME_DAY_SECONDS)
    assert state == GilEconomyState.DEFLATING


def test_state_crisis_deflation():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY,
        amount=2_000_000, now_seconds=0.0,
    )
    state = t.state_at(now_seconds=GAME_DAY_SECONDS)
    assert state == GilEconomyState.CRISIS_DEFLATION


def test_top_sources_ranks_by_amount():
    t = GilFlowTracker()
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=10_000,
        now_seconds=0.0,
    )
    t.record_source(
        kind=GilSourceKind.NM_DROP, amount=50_000,
        now_seconds=0.0,
    )
    t.record_source(
        kind=GilSourceKind.QUEST_REWARD, amount=20_000,
        now_seconds=0.0,
    )
    top = t.top_sources(now_seconds=0.0, top_n=2)
    kinds = [k for k, _ in top]
    assert kinds == [GilSourceKind.NM_DROP, GilSourceKind.QUEST_REWARD]


def test_top_sinks_aggregates_same_kind():
    t = GilFlowTracker()
    for _ in range(5):
        t.record_sink(
            kind=GilSinkKind.REPAIR, amount=1000,
            now_seconds=0.0,
        )
    t.record_sink(
        kind=GilSinkKind.AH_TAX, amount=2000,
        now_seconds=0.0,
    )
    top = t.top_sinks(now_seconds=0.0, top_n=2)
    assert top[0] == (GilSinkKind.REPAIR, 5000)
    assert top[1] == (GilSinkKind.AH_TAX, 2000)


def test_old_flows_drop_out_of_window():
    t = GilFlowTracker(window_seconds=100.0)
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=10_000,
        now_seconds=0.0,
    )
    # Long after — old flow should be trimmed when the next one
    # is recorded.
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=5_000,
        now_seconds=10_000.0,
    )
    assert t.total_source_gil(now_seconds=10_000.0) == 5_000


def test_report_packages_state():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.NM_DROP, amount=300_000,
        now_seconds=0.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=50_000,
        now_seconds=0.0,
    )
    report = t.report(now_seconds=GAME_DAY_SECONDS)
    assert report.total_source_gil == 300_000
    assert report.total_sink_gil == 50_000
    assert report.state == GilEconomyState.INFLATING


def test_report_recommended_multiplier_inflation():
    """Inflating state -> regulator should recommend reduced
    gil drops."""
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.NM_DROP, amount=300_000,
        now_seconds=0.0,
    )
    report = t.report(now_seconds=GAME_DAY_SECONDS)
    assert report.recommended_drop_rate_multiplier < 1.0


def test_report_recommended_multiplier_deflation():
    """Deflating state -> recommend bumping gil drops."""
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=300_000,
        now_seconds=0.0,
    )
    report = t.report(now_seconds=GAME_DAY_SECONDS)
    assert report.recommended_drop_rate_multiplier > 1.0


def test_report_recommended_multiplier_healthy_is_one():
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=20_000,
        now_seconds=0.0,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=15_000,
        now_seconds=0.0,
    )
    report = t.report(now_seconds=GAME_DAY_SECONDS)
    assert report.recommended_drop_rate_multiplier == 1.0


def test_full_lifecycle_inflation_then_correction():
    """Day 1 inflation, regulator recommends a cut. Day 2 sinks
    catch up, state returns healthy, multiplier returns to 1.0."""
    t = GilFlowTracker(window_seconds=GAME_DAY_SECONDS)
    # Day 1: NM gold rush
    for _ in range(50):
        t.record_source(
            kind=GilSourceKind.NM_DROP, amount=10_000,
            now_seconds=1000.0,
        )
    day_one = t.report(now_seconds=GAME_DAY_SECONDS - 100)
    assert day_one.state == GilEconomyState.INFLATING
    assert day_one.recommended_drop_rate_multiplier < 1.0
    # Day 2: balance restored
    later = 2 * GAME_DAY_SECONDS
    t.record_source(
        kind=GilSourceKind.MOB_DROP, amount=20_000,
        now_seconds=later - 100,
    )
    t.record_sink(
        kind=GilSinkKind.NPC_VENDOR_BUY, amount=15_000,
        now_seconds=later - 50,
    )
    day_two = t.report(now_seconds=later)
    assert day_two.state == GilEconomyState.HEALTHY
    assert day_two.recommended_drop_rate_multiplier == 1.0
