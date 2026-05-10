"""Tests for voice_swap_orchestrator."""
from __future__ import annotations

import datetime as dt

import pytest

from server.voice_swap_orchestrator import (
    LineProvisioning, QcReport, VoiceSwapOrchestrator,
)


def _orch_with_line() -> VoiceSwapOrchestrator:
    o = VoiceSwapOrchestrator()
    o.register_line(
        "L1", "curilla",
        "ai://curilla/L1.wav",
        expected_duration_s=2.0,
    )
    return o


def _now() -> dt.datetime:
    return dt.datetime(2026, 5, 9, 14, 0, 0)


def test_register_line_basic():
    o = _orch_with_line()
    assert o.state_of("L1") == LineProvisioning.AI_DEFAULT


def test_register_line_blank_id_raises():
    o = VoiceSwapOrchestrator()
    with pytest.raises(ValueError):
        o.register_line("", "curilla", "ai://x.wav")


def test_register_line_blank_uri_raises():
    o = VoiceSwapOrchestrator()
    with pytest.raises(ValueError):
        o.register_line("L1", "curilla", "")


def test_register_line_zero_duration_raises():
    o = VoiceSwapOrchestrator()
    with pytest.raises(ValueError):
        o.register_line(
            "L1", "curilla", "ai://x.wav",
            expected_duration_s=0.0,
        )


def test_register_line_duplicate_raises():
    o = _orch_with_line()
    with pytest.raises(ValueError):
        o.register_line("L1", "curilla", "ai://x.wav")


def test_active_uri_starts_as_ai():
    o = _orch_with_line()
    assert o.active_uri_for("L1") == "ai://curilla/L1.wav"


def test_deliver_human_take_advances_state():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav",
        _now(), "Jane Smith",
    )
    assert (
        o.state_of("L1")
        == LineProvisioning.HUMAN_RECORDING
    )


def test_deliver_human_take_blank_uri_raises():
    o = _orch_with_line()
    with pytest.raises(ValueError):
        o.deliver_human_take("L1", "", _now(), "Jane")


def test_deliver_human_take_blank_va_raises():
    o = _orch_with_line()
    with pytest.raises(ValueError):
        o.deliver_human_take(
            "L1", "human://good.wav", _now(), "",
        )


def test_qc_passes_for_good_audio():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    report = o.qc_check("L1")
    assert isinstance(report, QcReport)
    assert report.passed is True
    assert report.alignment_cer <= 0.05


def test_qc_fails_for_bad_audio():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://bad/L1.wav", _now(), "Jane",
    )
    report = o.qc_check("L1")
    assert report.passed is False
    assert len(report.issues) >= 1


def test_qc_advances_to_human_qc():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    assert o.state_of("L1") == LineProvisioning.HUMAN_QC


def test_qc_check_only_after_recording():
    o = _orch_with_line()
    with pytest.raises(RuntimeError):
        o.qc_check("L1")


def test_promote_to_live_after_pass():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    assert o.state_of("L1") == LineProvisioning.HUMAN_LIVE


def test_promote_to_live_active_uri_changes():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    assert o.active_uri_for("L1") == "human://good/L1.wav"


def test_promote_blocked_when_qc_failed():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://bad/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    with pytest.raises(RuntimeError):
        o.promote_to_live("L1")


def test_promote_requires_qc_state():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    with pytest.raises(RuntimeError):
        o.promote_to_live("L1")


def test_deprecate_after_live():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    o.deprecate("L1", "VA voiced wrong line")
    assert o.state_of("L1") == LineProvisioning.DEPRECATED


def test_deprecate_blocked_on_ai_default():
    o = _orch_with_line()
    with pytest.raises(RuntimeError):
        o.deprecate("L1", "x")


def test_rollback_to_ai_after_deprecate():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    o.deprecate("L1", "incident")
    o.rollback_to_ai("L1")
    assert o.state_of("L1") == LineProvisioning.AI_DEFAULT
    assert o.active_uri_for("L1") == "ai://curilla/L1.wav"


def test_rollback_requires_deprecated():
    o = _orch_with_line()
    with pytest.raises(RuntimeError):
        o.rollback_to_ai("L1")


def test_redeliver_after_rollback_works():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    o.deprecate("L1", "fix")
    o.rollback_to_ai("L1")
    o.deliver_human_take(
        "L1", "human://good/L1_v2.wav", _now(), "Jane",
    )
    assert (
        o.state_of("L1")
        == LineProvisioning.HUMAN_RECORDING
    )


def test_cannot_redeliver_when_live():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    with pytest.raises(RuntimeError):
        o.deliver_human_take(
            "L1", "human://good/L1_v2.wav", _now(), "Jane",
        )


def test_unknown_line_raises():
    o = VoiceSwapOrchestrator()
    with pytest.raises(KeyError):
        o.state_of("L1")


def test_percent_human_voiced_zero_when_none():
    o = _orch_with_line()
    assert o.percent_human_voiced("curilla") == 0.0


def test_percent_human_voiced_partial():
    o = _orch_with_line()
    o.register_line("L2", "curilla", "ai://L2.wav")
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    assert o.percent_human_voiced("curilla") == 50.0


def test_percent_human_voiced_unknown_role_zero():
    o = _orch_with_line()
    assert o.percent_human_voiced("nope") == 0.0


def test_provisioning_dashboard_shape():
    o = _orch_with_line()
    o.register_line("L2", "trion", "ai://L2.wav")
    dash = o.provisioning_dashboard()
    assert "curilla" in dash
    assert "trion" in dash
    assert dash["curilla"] == 0.0
    assert dash["trion"] == 0.0


def test_incident_log_records_deprecate_reason():
    o = _orch_with_line()
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    o.qc_check("L1")
    o.promote_to_live("L1")
    o.deprecate("L1", "out of sync")
    log = o.incident_log()
    assert len(log) == 1
    assert "out of sync" in log[0]


def test_qc_report_dataclass_frozen():
    import dataclasses as _d
    r = QcReport(True, 0.01, 0.04, -19.5, ())
    with pytest.raises(_d.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def test_custom_qc_fn_used():
    def always_fail(state, expected):
        return QcReport(
            False, 0.5, 0.5, -10.0, ("custom failure",),
        )
    o = VoiceSwapOrchestrator(qc_fn=always_fail)
    o.register_line(
        "L1", "curilla", "ai://x.wav",
        expected_duration_s=2.0,
    )
    o.deliver_human_take(
        "L1", "human://good/L1.wav", _now(), "Jane",
    )
    r = o.qc_check("L1")
    assert r.passed is False
    assert "custom failure" in r.issues[0]
