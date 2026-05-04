"""Tests for the voiced cutscene player."""
from __future__ import annotations

from server.voiced_cutscene import (
    AdvanceMode,
    CutsceneLine,
    LineEmotion,
    PlaybackStatus,
    VoicedCutscenePlayer,
)


def _intro_lines():
    return (
        CutsceneLine(
            line_index=0, speaker_id="ferdinand",
            text="Adventurer, the kingdom calls.",
            voice_clip_id="ferdinand_intro_01",
        ),
        CutsceneLine(
            line_index=1, speaker_id="alice",
            text="I'll heed the call.",
            emotion=LineEmotion.URGENT,
        ),
        CutsceneLine(
            line_index=2, speaker_id="ferdinand",
            text="May the goddess guide you.",
        ),
    )


def test_register_cutscene():
    p = VoicedCutscenePlayer()
    cs = p.register_cutscene(
        cutscene_id="bastok_intro",
        title="Bastok Intro",
        lines=_intro_lines(),
    )
    assert cs is not None
    assert len(cs.lines) == 3


def test_register_no_lines_rejected():
    p = VoicedCutscenePlayer()
    assert p.register_cutscene(
        cutscene_id="x", title="empty", lines=(),
    ) is None


def test_register_non_contiguous_rejected():
    p = VoicedCutscenePlayer()
    bad = (
        CutsceneLine(
            line_index=0, speaker_id="a", text="x",
        ),
        CutsceneLine(
            line_index=2, speaker_id="b", text="y",
        ),
    )
    assert p.register_cutscene(
        cutscene_id="x", title="bad", lines=bad,
    ) is None


def test_double_register_rejected():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    assert p.register_cutscene(
        cutscene_id="x", title="t2",
        lines=_intro_lines(),
    ) is None


def test_start_cutscene_unknown():
    p = VoicedCutscenePlayer()
    assert p.start(
        player_id="alice", cutscene_id="ghost",
    ) is None


def test_start_initializes_state():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    st = p.start(
        player_id="alice", cutscene_id="x",
        mode=AdvanceMode.MANUAL,
    )
    assert st.status == PlaybackStatus.PLAYING
    assert st.line_index == 0
    assert st.mode == AdvanceMode.MANUAL


def test_current_line_first():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    line = p.current_line(player_id="alice")
    assert line.text.startswith("Adventurer")


def test_advance_progresses_line_index():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    st = p.advance(player_id="alice")
    assert st.line_index == 1


def test_advance_past_end_marks_complete():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    p.advance(player_id="alice")
    p.advance(player_id="alice")
    st = p.advance(player_id="alice")
    assert st.status == PlaybackStatus.COMPLETE


def test_advance_after_complete_returns_none():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    for _ in range(5):
        p.advance(player_id="alice")
    res = p.advance(player_id="alice")
    assert res is None


def test_skip_short_circuits():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    st = p.skip(player_id="alice")
    assert st.status == PlaybackStatus.SKIPPED


def test_skip_already_skipped_returns_none():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    p.skip(player_id="alice")
    assert p.skip(player_id="alice") is None


def test_pause_then_resume():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    assert p.pause(player_id="alice")
    assert p.state_for("alice").status == PlaybackStatus.PAUSED
    assert p.resume(player_id="alice")
    assert p.state_for("alice").status == PlaybackStatus.PLAYING


def test_pause_when_not_playing_returns_false():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    p.pause(player_id="alice")
    # Already paused
    assert not p.pause(player_id="alice")


def test_advance_when_paused_rejected():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    p.pause(player_id="alice")
    assert p.advance(player_id="alice") is None


def test_rewind_one_line():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    p.advance(player_id="alice")
    assert p.rewind_one_line(player_id="alice")
    assert p.state_for("alice").line_index == 0


def test_rewind_at_start_rejected():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="x", title="t", lines=_intro_lines(),
    )
    p.start(player_id="alice", cutscene_id="x")
    assert not p.rewind_one_line(player_id="alice")


def test_state_unknown_player():
    p = VoicedCutscenePlayer()
    assert p.state_for("ghost") is None


def test_total_cutscenes_count():
    p = VoicedCutscenePlayer()
    p.register_cutscene(
        cutscene_id="a", title="A", lines=_intro_lines(),
    )
    p.register_cutscene(
        cutscene_id="b", title="B", lines=_intro_lines(),
    )
    assert p.total_cutscenes() == 2
