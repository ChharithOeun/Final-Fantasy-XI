"""Tests for bardic_renown."""
from __future__ import annotations

from server.bardic_renown import (
    BardicSongbook,
    RenownTier,
    SongTier,
)


def test_compose_happy():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="Of Vorrak's Fall", composer_id="ulmia",
        composed_at=100,
        subject_player_ids=["alice", "bob"],
        source_entry_id="hist_42",
        song_tier=SongTier.LEGENDARY,
    )
    assert bid == "ballad_1"
    assert sb.total_ballads() == 1


def test_blank_title_blocked():
    sb = BardicSongbook()
    out = sb.compose_ballad(
        title="", composer_id="ulmia",
        composed_at=10,
        subject_player_ids=["alice"],
    )
    assert out == ""


def test_blank_composer_blocked():
    sb = BardicSongbook()
    out = sb.compose_ballad(
        title="X", composer_id="",
        composed_at=10,
        subject_player_ids=["alice"],
    )
    assert out == ""


def test_no_subjects_blocked():
    sb = BardicSongbook()
    out = sb.compose_ballad(
        title="X", composer_id="ulmia",
        composed_at=10, subject_player_ids=[],
    )
    assert out == ""


def test_perform_to_subject_buffs():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="X", composer_id="ulmia",
        composed_at=10,
        subject_player_ids=["alice"],
    )
    assert sb.perform(
        ballad_id=bid, listening_player_id="alice",
        performed_at=20,
    ) is True


def test_perform_to_non_subject_no_buff():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="X", composer_id="ulmia",
        composed_at=10,
        subject_player_ids=["alice"],
    )
    assert sb.perform(
        ballad_id=bid, listening_player_id="bob",
        performed_at=20,
    ) is False


def test_perform_unknown_ballad():
    sb = BardicSongbook()
    out = sb.perform(
        ballad_id="ballad_999",
        listening_player_id="alice", performed_at=10,
    )
    assert out is False


def test_perform_blank_listener():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="X", composer_id="ulmia", composed_at=10,
        subject_player_ids=["alice"],
    )
    out = sb.perform(
        ballad_id=bid, listening_player_id="",
        performed_at=20,
    )
    assert out is False


def test_ballads_about_index():
    sb = BardicSongbook()
    sb.compose_ballad(
        title="A", composer_id="u",
        composed_at=1, subject_player_ids=["alice"],
    )
    sb.compose_ballad(
        title="B", composer_id="u",
        composed_at=2, subject_player_ids=["alice", "bob"],
    )
    sb.compose_ballad(
        title="C", composer_id="u",
        composed_at=3, subject_player_ids=["carol"],
    )
    alice = sb.ballads_about(player_id="alice")
    assert len(alice) == 2
    bob = sb.ballads_about(player_id="bob")
    assert len(bob) == 1


def test_ballads_by_index():
    sb = BardicSongbook()
    sb.compose_ballad(
        title="A", composer_id="ulmia",
        composed_at=1, subject_player_ids=["alice"],
    )
    sb.compose_ballad(
        title="B", composer_id="joachim",
        composed_at=2, subject_player_ids=["alice"],
    )
    sb.compose_ballad(
        title="C", composer_id="ulmia",
        composed_at=3, subject_player_ids=["bob"],
    )
    ulmia = sb.ballads_by(composer_id="ulmia")
    assert len(ulmia) == 2


def test_renown_unsung():
    sb = BardicSongbook()
    assert sb.renown_of(player_id="ghost") == RenownTier.UNSUNG


def test_renown_noted():
    sb = BardicSongbook()
    for i in range(2):
        sb.compose_ballad(
            title=f"t{i}", composer_id="u",
            composed_at=i, subject_player_ids=["alice"],
        )
    assert sb.renown_of(player_id="alice") == RenownTier.NOTED


def test_renown_celebrated():
    sb = BardicSongbook()
    for i in range(7):
        sb.compose_ballad(
            title=f"t{i}", composer_id="u",
            composed_at=i, subject_player_ids=["alice"],
        )
    assert sb.renown_of(player_id="alice") == RenownTier.CELEBRATED


def test_renown_legend():
    sb = BardicSongbook()
    for i in range(12):
        sb.compose_ballad(
            title=f"t{i}", composer_id="u",
            composed_at=i, subject_player_ids=["alice"],
            song_tier=SongTier.RARE,
        )
    assert sb.renown_of(player_id="alice") == RenownTier.LEGEND


def test_renown_immortal_needs_mythic_and_count():
    sb = BardicSongbook()
    # 25 songs, one mythic
    for i in range(24):
        sb.compose_ballad(
            title=f"t{i}", composer_id="u",
            composed_at=i, subject_player_ids=["alice"],
            song_tier=SongTier.RARE,
        )
    sb.compose_ballad(
        title="t-mythic", composer_id="u",
        composed_at=99, subject_player_ids=["alice"],
        song_tier=SongTier.MYTHIC,
    )
    assert sb.renown_of(player_id="alice") == RenownTier.IMMORTAL


def test_renown_20_without_mythic_is_legend_only():
    sb = BardicSongbook()
    for i in range(22):
        sb.compose_ballad(
            title=f"t{i}", composer_id="u",
            composed_at=i, subject_player_ids=["alice"],
            song_tier=SongTier.EPIC,
        )
    # 22 ballads but no mythic — caps at LEGEND
    assert sb.renown_of(player_id="alice") == RenownTier.LEGEND


def test_get_returns_ballad():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="X", composer_id="u", composed_at=10,
        subject_player_ids=["alice"],
        song_tier=SongTier.EPIC,
    )
    b = sb.get(ballad_id=bid)
    assert b is not None
    assert b.title == "X"
    assert b.song_tier == SongTier.EPIC


def test_blank_subjects_filtered():
    sb = BardicSongbook()
    bid = sb.compose_ballad(
        title="X", composer_id="u", composed_at=10,
        subject_player_ids=["alice", "", "bob"],
    )
    b = sb.get(ballad_id=bid)
    assert b is not None
    assert b.subject_player_ids == ("alice", "bob")
