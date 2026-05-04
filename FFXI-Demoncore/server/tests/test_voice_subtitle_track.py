"""Tests for the voice subtitle track."""
from __future__ import annotations

from server.voice_subtitle_track import (
    DEFAULT_FONT,
    FontFamily,
    MAX_BG_ALPHA,
    MAX_FONT,
    SubtitleLanguage,
    VoiceSubtitleTrack,
)


def test_prefs_default():
    t = VoiceSubtitleTrack()
    p = t.prefs_for(player_id="alice")
    assert p.enabled
    assert p.font_size == DEFAULT_FONT
    assert p.language == SubtitleLanguage.EN


def test_set_pref_font_clamps():
    t = VoiceSubtitleTrack()
    t.set_pref(player_id="alice", font_size=999)
    assert t.prefs_for(
        player_id="alice",
    ).font_size == MAX_FONT


def test_set_pref_alpha_clamps():
    t = VoiceSubtitleTrack()
    t.set_pref(
        player_id="alice", background_alpha=200,
    )
    assert t.prefs_for(
        player_id="alice",
    ).background_alpha == MAX_BG_ALPHA


def test_set_pref_language():
    t = VoiceSubtitleTrack()
    t.set_pref(
        player_id="alice", language=SubtitleLanguage.JA,
    )
    assert t.prefs_for(
        player_id="alice",
    ).language == SubtitleLanguage.JA


def test_set_pref_color_empty_ignored():
    t = VoiceSubtitleTrack()
    p = t.prefs_for(player_id="alice")
    original = p.color
    t.set_pref(player_id="alice", color="")
    assert t.prefs_for(
        player_id="alice",
    ).color == original


def test_push_line_creates_subtitle():
    t = VoiceSubtitleTrack()
    line = t.push_line(
        player_id="alice", speaker_name="Cid",
        text="Stand together!",
        hold_seconds=3.0,
    )
    assert line is not None


def test_push_line_disabled_returns_none():
    t = VoiceSubtitleTrack()
    t.set_pref(player_id="alice", enabled=False)
    line = t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=3.0,
    )
    assert line is None


def test_push_line_empty_text_rejected():
    t = VoiceSubtitleTrack()
    line = t.push_line(
        player_id="alice", speaker_name="x",
        text="", hold_seconds=3.0,
    )
    assert line is None


def test_push_line_zero_hold_rejected():
    t = VoiceSubtitleTrack()
    line = t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=0.0,
    )
    assert line is None


def test_show_in_active_world_off_blocks_world_lines():
    t = VoiceSubtitleTrack()
    t.set_pref(
        player_id="alice", show_in_active_world=False,
    )
    line = t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=3.0,
        from_cutscene=False,
    )
    assert line is None
    # but cutscene line still works
    line2 = t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=3.0,
        from_cutscene=True,
    )
    assert line2 is not None


def test_current_subtitles_returns_recent():
    t = VoiceSubtitleTrack()
    for i in range(5):
        t.push_line(
            player_id="alice", speaker_name="x",
            text=f"line {i}", hold_seconds=10.0,
        )
    subs = t.current_subtitles(
        player_id="alice", max_lines=3,
    )
    assert len(subs) == 3
    assert subs[-1].text == "line 4"


def test_current_subtitles_zero_max_returns_empty():
    t = VoiceSubtitleTrack()
    t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=3.0,
    )
    assert t.current_subtitles(
        player_id="alice", max_lines=0,
    ) == ()


def test_tick_expires_old_lines():
    t = VoiceSubtitleTrack()
    t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=2.0,
        now_seconds=0.0,
    )
    expired = t.tick(
        player_id="alice", now_seconds=10.0,
    )
    assert len(expired) == 1
    assert t.total_active_lines(
        player_id="alice",
    ) == 0


def test_tick_keeps_fresh_lines():
    t = VoiceSubtitleTrack()
    t.push_line(
        player_id="alice", speaker_name="x",
        text="hi", hold_seconds=10.0,
        now_seconds=0.0,
    )
    expired = t.tick(
        player_id="alice", now_seconds=1.0,
    )
    assert expired == ()


def test_tick_unknown_player():
    t = VoiceSubtitleTrack()
    assert t.tick(
        player_id="ghost", now_seconds=10.0,
    ) == ()


def test_per_player_isolation():
    t = VoiceSubtitleTrack()
    t.push_line(
        player_id="alice", speaker_name="x",
        text="alice line", hold_seconds=10.0,
    )
    t.push_line(
        player_id="bob", speaker_name="x",
        text="bob line", hold_seconds=10.0,
    )
    a = t.current_subtitles(player_id="alice")
    b = t.current_subtitles(player_id="bob")
    assert a[0].text == "alice line"
    assert b[0].text == "bob line"


def test_set_pref_font_family():
    t = VoiceSubtitleTrack()
    t.set_pref(
        player_id="alice",
        font_family=FontFamily.DYSLEXIC,
    )
    assert t.prefs_for(
        player_id="alice",
    ).font_family == FontFamily.DYSLEXIC


def test_show_speaker_name_toggle():
    t = VoiceSubtitleTrack()
    t.set_pref(
        player_id="alice", show_speaker_name=False,
    )
    assert not t.prefs_for(
        player_id="alice",
    ).show_speaker_name
