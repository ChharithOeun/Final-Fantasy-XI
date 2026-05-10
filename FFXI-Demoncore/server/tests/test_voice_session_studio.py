"""Tests for voice_session_studio."""
from __future__ import annotations

import pytest

from server.voice_session_studio import (
    DirectorMark, SessionKind, SessionState, SessionStudio,
    STUDIOS, StudioKind,
)


def _book() -> tuple[SessionStudio, str]:
    s = SessionStudio()
    sess = s.book_session(
        "burbank_voiceworks", "curilla", "Jane Smith", 4.0,
    )
    return s, sess.session_id


def test_six_studios_present():
    assert len(STUDIOS) == 6


def test_list_studios_returns_all():
    s = SessionStudio()
    out = s.list_studios()
    assert len(out) == 6


def test_studio_kinds_diverse():
    kinds = {st.kind for st in STUDIOS.values()}
    assert StudioKind.IN_PERSON in kinds
    assert StudioKind.REMOTE in kinds


def test_book_session_basic():
    s = SessionStudio()
    sess = s.book_session(
        "burbank_voiceworks", "curilla", "Jane", 3.5,
    )
    assert sess.state == SessionState.BOOKED
    assert sess.studio_name == "burbank_voiceworks"
    assert sess.role_id == "curilla"


def test_book_unknown_studio_raises():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.book_session("nope", "curilla", "Jane", 1.0)


def test_book_zero_hours_raises():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.book_session(
            "burbank_voiceworks", "curilla", "Jane", 0.0,
        )


def test_book_blank_role_raises():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.book_session(
            "burbank_voiceworks", "", "Jane", 1.0,
        )


def test_book_blank_va_raises():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.book_session(
            "burbank_voiceworks", "curilla", "", 1.0,
        )


def test_book_adr_on_jamulus_rejected():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.book_session(
            "jamulus_remote", "curilla", "Jane", 1.0,
            kind=SessionKind.ADR,
        )


def test_book_adr_on_burbank_ok():
    s = SessionStudio()
    out = s.book_session(
        "burbank_voiceworks", "curilla", "Jane", 1.0,
        kind=SessionKind.ADR,
    )
    assert out.kind == SessionKind.ADR


def test_log_take_advances_to_recording():
    s, sid = _book()
    s.log_take(
        sid, "L1", 1, 2.5, DirectorMark.PICK,
    )
    summary = s.session_summary(sid)
    assert summary["state"] == "recording"


def test_log_take_records_take():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 2.5, DirectorMark.PICK)
    s.log_take(sid, "L1", 2, 2.6, DirectorMark.ALT)
    summary = s.session_summary(sid)
    assert summary["takes_total"] == 2
    assert summary["takes_pick"] == 1


def test_log_take_zero_take_number_raises():
    s, sid = _book()
    with pytest.raises(ValueError):
        s.log_take(sid, "L1", 0, 1.0, DirectorMark.PICK)


def test_log_take_negative_duration_raises():
    s, sid = _book()
    with pytest.raises(ValueError):
        s.log_take(sid, "L1", 1, -0.5, DirectorMark.PICK)


def test_wrap_and_deliver_path():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 1.5, DirectorMark.PICK)
    s.wrap(sid)
    s.deliver(sid, "s3://demoncore/curilla/sess_00001.wav")
    summary = s.session_summary(sid)
    assert summary["state"] == "delivered"
    assert summary["delivered_uri"].startswith("s3://")


def test_deliver_requires_wrap():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 1.5, DirectorMark.PICK)
    with pytest.raises(RuntimeError):
        s.deliver(sid, "s3://x.wav")


def test_deliver_requires_uri():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 1.5, DirectorMark.PICK)
    s.wrap(sid)
    with pytest.raises(ValueError):
        s.deliver(sid, "")


def test_log_take_after_wrap_raises():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 1.5, DirectorMark.PICK)
    s.wrap(sid)
    with pytest.raises(RuntimeError):
        s.log_take(sid, "L2", 1, 1.0, DirectorMark.PICK)


def test_session_summary_lines_recorded():
    s, sid = _book()
    s.log_take(sid, "L1", 1, 1.5, DirectorMark.PICK)
    s.log_take(sid, "L1", 2, 1.5, DirectorMark.ALT)
    s.log_take(sid, "L2", 1, 1.5, DirectorMark.PICK)
    summary = s.session_summary(sid)
    assert summary["lines_recorded"] == 2


def test_projected_cost_matches_studio_rate():
    s = SessionStudio()
    sess = s.book_session(
        "burbank_voiceworks", "curilla", "Jane", 4.0,
    )
    expected = STUDIOS["burbank_voiceworks"].hourly_rate_usd
    assert sess.projected_cost_usd == expected * 4.0


def test_unknown_session_raises():
    s = SessionStudio()
    with pytest.raises(KeyError):
        s.session_summary("sess_99999")


def test_best_studio_for_la_within_budget():
    s = SessionStudio()
    out = s.best_studio_for("la", budget_usd_max=400.0)
    assert out.name == "burbank_voiceworks"


def test_best_studio_for_tokyo_within_budget():
    s = SessionStudio()
    out = s.best_studio_for("tokyo", budget_usd_max=300.0)
    assert out.name == "aoi_tokyo"


def test_best_studio_for_unknown_loc_uses_cheapest():
    s = SessionStudio()
    out = s.best_studio_for("rural_iceland", 50.0)
    # home_booth or jamulus_remote both = 0 hourly
    assert out.hourly_rate_usd <= 50.0


def test_best_studio_for_zero_budget_picks_free():
    s = SessionStudio()
    out = s.best_studio_for("nowhere", 0.0)
    assert out.hourly_rate_usd == 0.0


def test_best_studio_for_negative_budget_raises():
    s = SessionStudio()
    with pytest.raises(ValueError):
        s.best_studio_for("la", -1.0)


def test_best_studio_for_la_under_budget_falls_back():
    s = SessionStudio()
    # LA studio is 300/hr; budget 50 forces a remote.
    out = s.best_studio_for("la", 50.0)
    assert out.kind == StudioKind.REMOTE


def test_session_kind_normal_default():
    s, sid = _book()
    assert (
        s.session_summary(sid)["kind"] == "normal"
    )


def test_session_summary_keys():
    s, sid = _book()
    summary = s.session_summary(sid)
    for key in (
        "session_id", "studio", "role_id", "va_name",
        "kind", "state", "takes_total", "takes_pick",
        "lines_recorded", "projected_cost_usd",
        "delivered_uri",
    ):
        assert key in summary
