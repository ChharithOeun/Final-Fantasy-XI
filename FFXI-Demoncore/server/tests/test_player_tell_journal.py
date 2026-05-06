"""Tests for player_tell_journal."""
from __future__ import annotations

from server.boss_ability_tells import TellKind
from server.player_tell_journal import (
    Confidence,
    DEFEATED_BONUS_OBSERVATIONS,
    HUNCH_THRESHOLD,
    LEARNED_THRESHOLD,
    PATTERNED_THRESHOLD,
    PlayerTellJournal,
)


def test_observe_happy():
    j = PlayerTellJournal()
    assert j.observe(
        player_id="alice", boss_id="vorrak",
        ability_id="spirit_surge", tell=TellKind.WEAPON_GLOW,
    ) is True


def test_blank_player_blocked():
    j = PlayerTellJournal()
    assert j.observe(
        player_id="", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    ) is False


def test_default_unknown():
    j = PlayerTellJournal()
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.UNKNOWN


def test_one_observation_seen_once():
    j = PlayerTellJournal()
    j.observe(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.SEEN_ONCE


def test_hunch_threshold():
    j = PlayerTellJournal()
    for _ in range(HUNCH_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.HUNCH


def test_patterned_threshold():
    j = PlayerTellJournal()
    for _ in range(PATTERNED_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.PATTERNED


def test_learned_threshold():
    j = PlayerTellJournal()
    for _ in range(LEARNED_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.LEARNED


def test_defeat_promotes_to_defeated():
    j = PlayerTellJournal()
    for _ in range(LEARNED_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    j.mark_defeat(player_id="alice", boss_id="vorrak")
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.DEFEATED


def test_defeat_bonus_lifts_confidence():
    j = PlayerTellJournal()
    # 4 observations = HUNCH normally
    for _ in range(4):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    j.mark_defeat(player_id="alice", boss_id="vorrak")
    # +5 from defeat = 9 = PATTERNED
    out = j.confidence(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.PATTERNED


def test_predictions_for_tell_ranks_by_count():
    j = PlayerTellJournal()
    # Apocalyptic Slam: 7 observations
    for _ in range(7):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="apocalyptic_slam",
            tell=TellKind.DUST_FALLING,
        )
    # Lesser Crash: 2 observations (false alarm)
    for _ in range(2):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="lesser_crash",
            tell=TellKind.DUST_FALLING,
        )
    out = j.predictions_for_tell(
        player_id="alice", boss_id="vorrak",
        tell=TellKind.DUST_FALLING,
    )
    assert len(out) == 2
    assert out[0].ability_id == "apocalyptic_slam"
    assert out[0].observations == 7
    assert out[1].ability_id == "lesser_crash"


def test_predictions_for_unknown_tell_empty():
    j = PlayerTellJournal()
    out = j.predictions_for_tell(
        player_id="alice", boss_id="vorrak",
        tell=TellKind.GUSTING_WIND,
    )
    assert out == ()


def test_per_player_isolation():
    j = PlayerTellJournal()
    for _ in range(LEARNED_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    out = j.confidence(
        player_id="bob", boss_id="vorrak",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.UNKNOWN


def test_per_boss_isolation():
    j = PlayerTellJournal()
    for _ in range(LEARNED_THRESHOLD):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.WEAPON_GLOW,
        )
    out = j.confidence(
        player_id="alice", boss_id="mirahna",
        ability_id="x", tell=TellKind.WEAPON_GLOW,
    )
    assert out == Confidence.UNKNOWN


def test_total_observations():
    j = PlayerTellJournal()
    for _ in range(5):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.DUST_FALLING,
        )
    for _ in range(3):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="y", tell=TellKind.GUSTING_WIND,
        )
    assert j.total_observations(player_id="alice") == 8


def test_known_bosses():
    j = PlayerTellJournal()
    j.observe(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.DUST_FALLING,
    )
    j.observe(
        player_id="alice", boss_id="mirahna",
        ability_id="y", tell=TellKind.WATER_RIPPLE,
    )
    out = j.known_bosses(player_id="alice")
    assert "vorrak" in out
    assert "mirahna" in out


def test_defeat_bonus_shows_in_predictions():
    j = PlayerTellJournal()
    j.observe(
        player_id="alice", boss_id="vorrak",
        ability_id="x", tell=TellKind.DUST_FALLING,
    )
    j.mark_defeat(player_id="alice", boss_id="vorrak")
    out = j.predictions_for_tell(
        player_id="alice", boss_id="vorrak",
        tell=TellKind.DUST_FALLING,
    )
    # 1 base obs + 5 defeat bonus = 6 observations
    assert out[0].observations == 1 + DEFEATED_BONUS_OBSERVATIONS


def test_multiple_observations_for_same_pair():
    j = PlayerTellJournal()
    for _ in range(3):
        j.observe(
            player_id="alice", boss_id="vorrak",
            ability_id="x", tell=TellKind.DUST_FALLING,
        )
    out = j.predictions_for_tell(
        player_id="alice", boss_id="vorrak",
        tell=TellKind.DUST_FALLING,
    )
    assert out[0].observations == 3
