"""Tests for voice_audition_pipeline."""
from __future__ import annotations

import pytest

from server.voice_audition_pipeline import (
    AudioFormat, AuditionPacket, AuditionPipeline,
    AuditionState, Decision, RecordingSpec,
)


def _good_spec() -> RecordingSpec:
    return RecordingSpec(
        sample_rate_hz=48_000, bit_depth=24,
        fmt=AudioFormat.WAV,
        room_tone_seconds=4.0,
        broadcast_loudness_lufs=-20.0,
    )


def _packet(role_id: str = "curilla") -> AuditionPacket:
    return AuditionPacket(
        role_id=role_id,
        sample_lines=(
            "Halt, by order of Her Majesty.",
            "We move at sundown.",
            "Hold the line!",
        ),
        wild_line="A captain's word is iron.",
        performance_notes="Stern, paternal, no warmth.",
    )


def _open_basic() -> tuple[AuditionPipeline, AuditionPacket]:
    p = AuditionPipeline()
    pk = _packet()
    p.open_audition("curilla", pk)
    return p, pk


def test_packet_requires_3_to_5_sample_lines():
    with pytest.raises(ValueError):
        AuditionPacket(
            role_id="x", sample_lines=("a", "b"),
            wild_line="w", performance_notes="",
        )


def test_packet_requires_wild_line():
    with pytest.raises(ValueError):
        AuditionPacket(
            role_id="x",
            sample_lines=("a", "b", "c"),
            wild_line="", performance_notes="",
        )


def test_open_audition_records_packet():
    p, _ = _open_basic()
    assert p.has_open_audition("curilla")


def test_open_audition_role_mismatch_raises():
    p = AuditionPipeline()
    pk = _packet("curilla")
    with pytest.raises(ValueError):
        p.open_audition("trion", pk)


def test_open_audition_double_open_raises():
    p, pk = _open_basic()
    with pytest.raises(ValueError):
        p.open_audition("curilla", pk)


def test_submit_with_good_spec():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane Smith", _good_spec())
    assert sub.state == AuditionState.SUBMITTED
    assert sub.role_id == "curilla"
    assert sub.va_name == "Jane Smith"


def test_submit_unknown_role_raises():
    p = AuditionPipeline()
    with pytest.raises(ValueError):
        p.submit("nope", "X", _good_spec())


def test_submit_blank_va_raises():
    p, _ = _open_basic()
    with pytest.raises(ValueError):
        p.submit("curilla", "", _good_spec())


def test_submit_low_sample_rate_raises():
    p, _ = _open_basic()
    bad = RecordingSpec(
        sample_rate_hz=44_100, bit_depth=24,
        fmt=AudioFormat.WAV,
        room_tone_seconds=4.0,
        broadcast_loudness_lufs=-20.0,
    )
    with pytest.raises(ValueError):
        p.submit("curilla", "Jane", bad)


def test_submit_low_bit_depth_raises():
    p, _ = _open_basic()
    bad = RecordingSpec(
        sample_rate_hz=48_000, bit_depth=16,
        fmt=AudioFormat.WAV,
        room_tone_seconds=4.0,
        broadcast_loudness_lufs=-20.0,
    )
    with pytest.raises(ValueError):
        p.submit("curilla", "Jane", bad)


def test_submit_loudness_too_loud_raises():
    p, _ = _open_basic()
    bad = RecordingSpec(
        sample_rate_hz=48_000, bit_depth=24,
        fmt=AudioFormat.WAV,
        room_tone_seconds=4.0,
        broadcast_loudness_lufs=-10.0,
    )
    with pytest.raises(ValueError):
        p.submit("curilla", "Jane", bad)


def test_submit_loudness_too_quiet_raises():
    p, _ = _open_basic()
    bad = RecordingSpec(
        sample_rate_hz=48_000, bit_depth=24,
        fmt=AudioFormat.WAV,
        room_tone_seconds=4.0,
        broadcast_loudness_lufs=-30.0,
    )
    with pytest.raises(ValueError):
        p.submit("curilla", "Jane", bad)


def test_submit_short_room_tone_raises():
    p, _ = _open_basic()
    bad = RecordingSpec(
        sample_rate_hz=48_000, bit_depth=24,
        fmt=AudioFormat.WAV,
        room_tone_seconds=1.0,
        broadcast_loudness_lufs=-20.0,
    )
    with pytest.raises(ValueError):
        p.submit("curilla", "Jane", bad)


def test_screen_pass_advances_to_screened():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(
        sub.submission_id, Decision.PASS, "screener_a",
    )
    assert (
        p.state_of(sub.submission_id)
        == AuditionState.SCREENED
    )


def test_screen_reject_terminal():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(
        sub.submission_id, Decision.REJECT, "screener_a",
    )
    assert (
        p.state_of(sub.submission_id)
        == AuditionState.REJECTED
    )


def test_screen_hold_keeps_state():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(
        sub.submission_id, Decision.HOLD, "screener_a",
    )
    assert (
        p.state_of(sub.submission_id)
        == AuditionState.SUBMITTED
    )


def test_screen_requires_screener():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    with pytest.raises(ValueError):
        p.screen(sub.submission_id, Decision.PASS, "")


def test_screen_only_from_submitted():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    with pytest.raises(RuntimeError):
        p.screen(sub.submission_id, Decision.PASS, "s")


def test_callback_only_from_screened():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    with pytest.raises(RuntimeError):
        p.callback(sub.submission_id, "notes")


def test_callback_records_notes():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    out = p.callback(sub.submission_id, "needs more weight")
    assert out.director_notes == "needs more weight"
    assert out.state == AuditionState.CALLBACK


def test_book_requires_callback_first():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    with pytest.raises(RuntimeError):
        p.book(sub.submission_id, "C-1")


def test_book_requires_contract_id():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    p.callback(sub.submission_id, "good")
    with pytest.raises(ValueError):
        p.book(sub.submission_id, "")


def test_book_full_path():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    p.callback(sub.submission_id, "perfect")
    out = p.book(sub.submission_id, "C-2026-007")
    assert out.state == AuditionState.BOOKED
    assert out.contract_id == "C-2026-007"


def test_reject_anytime_before_terminal():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    p.reject(sub.submission_id, "tone mismatch")
    assert (
        p.state_of(sub.submission_id)
        == AuditionState.REJECTED
    )


def test_reject_after_book_raises():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.screen(sub.submission_id, Decision.PASS, "s")
    p.callback(sub.submission_id, "x")
    p.book(sub.submission_id, "C-1")
    with pytest.raises(RuntimeError):
        p.reject(sub.submission_id, "oops")


def test_submissions_for_role():
    p, _ = _open_basic()
    p.submit("curilla", "Jane", _good_spec())
    p.submit("curilla", "Eve", _good_spec())
    assert len(p.submissions_for("curilla")) == 2


def test_unknown_submission_raises():
    p = AuditionPipeline()
    with pytest.raises(KeyError):
        p.state_of("sub_999")


def test_flag_does_not_change_state():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    p.flag(sub.submission_id, "peer_va", "tonal_concern")
    state = p.state_of(sub.submission_id)
    assert state == AuditionState.SUBMITTED


def test_flag_records_text():
    p, _ = _open_basic()
    sub = p.submit("curilla", "Jane", _good_spec())
    out = p.flag(
        sub.submission_id, "peer_va", "tonal_concern",
    )
    assert out.flags == ["peer_va:tonal_concern"]


def test_submission_ids_are_unique():
    p, _ = _open_basic()
    a = p.submit("curilla", "Jane", _good_spec())
    b = p.submit("curilla", "Eve", _good_spec())
    assert a.submission_id != b.submission_id
