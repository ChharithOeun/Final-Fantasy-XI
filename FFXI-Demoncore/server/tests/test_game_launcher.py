"""Tests for game_launcher."""
from __future__ import annotations

import pytest

from server.game_launcher import (
    CINEMATIC_INTRO_DURATION_MS,
    CharacterCard,
    FIRST_PLAY_SEQUENCE_NAME,
    GameLauncherSystem,
    LauncherPose,
    LauncherState,
    MAX_CHARACTERS_PER_ACCOUNT,
    SPLASH_DURATION_MS,
    Transition,
    TransitionKind,
)


def _sys() -> GameLauncherSystem:
    return GameLauncherSystem()


def _card(
    char_id="c1",
    name="Aragorn",
    race="hume",
    job="WAR",
    level=75,
    zone="bastok_markets",
    last_ms=1000,
    hero="hero/bastok.exr",
):
    return CharacterCard(
        char_id=char_id,
        char_name=name,
        race=race,
        main_job=job,
        level=level,
        last_played_zone=zone,
        last_played_ms=last_ms,
        hero_shot_uri=hero,
    )


# ---- enum coverage ----

def test_launcher_state_count():
    assert len(list(LauncherState)) == 15


def test_launcher_state_has_splash():
    assert LauncherState.SPLASH in list(LauncherState)


def test_launcher_state_has_cinematic_intro():
    assert LauncherState.CINEMATIC_INTRO in list(LauncherState)


def test_launcher_state_has_disconnected():
    assert LauncherState.DISCONNECTED in list(LauncherState)


def test_transition_kind_user():
    assert TransitionKind.USER.value == "user"


def test_transition_kind_auto():
    assert TransitionKind.AUTO.value == "auto"


# ---- register ----

def test_register_account():
    s = _sys()
    s.register_state("acct1")
    assert s.has_account("acct1")
    assert s.account_count() == 1


def test_register_empty_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.register_state("")


def test_register_duplicate_raises():
    s = _sys()
    s.register_state("acct1")
    with pytest.raises(ValueError):
        s.register_state("acct1")


def test_register_bad_region_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.register_state("acct1", region="xx")


def test_register_starts_at_splash():
    s = _sys()
    s.register_state("acct1")
    assert s.current_state("acct1") == LauncherState.SPLASH


def test_current_state_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.current_state("ghost")


def test_region_japanese():
    s = _sys()
    s.register_state("acct1", region="ja")
    assert s.region_for("acct1") == "ja"


# ---- transition graph ----

def test_valid_transitions_from_splash():
    s = _sys()
    out = s.valid_transitions_from(LauncherState.SPLASH)
    assert len(out) >= 1
    assert all(
        isinstance(t_, Transition) for t_ in out
    )


def test_valid_transitions_includes_splash_to_title():
    s = _sys()
    out = s.valid_transitions_from(LauncherState.SPLASH)
    targets = {t_.to_state for t_ in out}
    assert LauncherState.TITLE_SCREEN in targets


def test_transitions_total_nonzero():
    s = _sys()
    assert s.transitions_total() > 0


# ---- transition_to ----

def test_transition_to_self_ok():
    s = _sys()
    s.register_state("a")
    assert s.transition_to("a", LauncherState.SPLASH) == "ok"


def test_transition_invalid_denied():
    s = _sys()
    s.register_state("a")
    # SPLASH -> IN_GAME is not in the graph.
    assert s.transition_to("a", LauncherState.IN_GAME) == "denied"


def test_transition_title_to_patch_ok():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    assert s.current_state("a") == LauncherState.TITLE_SCREEN
    assert (
        s.transition_to(
            "a", LauncherState.PATCH_CHECK, now_ms=100,
        )
        == "ok"
    )


def test_transition_unknown_account_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.transition_to("ghost", LauncherState.LOGIN)


def test_full_happy_path_returning_player():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.set_first_play_complete("a")
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    assert s.current_state("a") == LauncherState.TITLE_SCREEN
    assert (
        s.transition_to("a", LauncherState.PATCH_CHECK) == "ok"
    )
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    assert s.current_state("a") == LauncherState.LOGIN
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    assert s.current_state("a") == LauncherState.SERVER_SELECTION
    s.select_server("a", "us_east")
    s.transition_to("a", LauncherState.CHARACTER_SELECT)
    s.register_character_card("a", _card())
    s.select_character("a", "c1")
    s.transition_to("a", LauncherState.WORLD_LOAD)
    s.set_predicate("a", "world_loaded")
    s.advance_automatic("a", now_ms=10000)
    assert s.current_state("a") == LauncherState.IN_GAME


# ---- automatic transitions ----

def test_splash_auto_advances_after_duration():
    s = _sys()
    s.register_state("a", now_ms=0)
    fired = s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    assert fired is True
    assert s.current_state("a") == LauncherState.TITLE_SCREEN


def test_splash_no_auto_before_duration():
    s = _sys()
    s.register_state("a", now_ms=0)
    fired = s.advance_automatic("a", now_ms=100)
    assert fired is False
    assert s.current_state("a") == LauncherState.SPLASH


def test_patch_check_clean_advances_to_login():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    assert s.current_state("a") == LauncherState.LOGIN


def test_patch_check_pending_advances_to_patching():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_pending")
    s.advance_automatic("a", now_ms=2000)
    assert s.current_state("a") == LauncherState.PATCHING


def test_patching_download_finished_to_login():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_pending")
    s.advance_automatic("a", now_ms=2000)
    assert s.current_state("a") == LauncherState.PATCHING
    s.set_predicate("a", "download_finished")
    s.advance_automatic("a", now_ms=3000)
    assert s.current_state("a") == LauncherState.LOGIN


def test_cinematic_intro_auto_advances():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    s.transition_to("a", LauncherState.CHARACTER_SELECT)
    s.register_character_card("a", _card())
    s.select_character("a", "c1")
    s.transition_to("a", LauncherState.WORLD_LOAD)
    s.set_predicate("a", "world_loaded")
    s.advance_automatic("a", now_ms=10000)
    assert s.current_state("a") == LauncherState.CINEMATIC_INTRO
    fired = s.advance_automatic(
        "a", now_ms=10000 + CINEMATIC_INTRO_DURATION_MS,
    )
    assert fired
    assert s.current_state("a") == LauncherState.IN_GAME


def test_socket_drop_to_disconnected():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.set_first_play_complete("a")
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    s.transition_to("a", LauncherState.CHARACTER_SELECT)
    s.register_character_card("a", _card())
    s.select_character("a", "c1")
    s.transition_to("a", LauncherState.WORLD_LOAD)
    s.set_predicate("a", "world_loaded")
    s.advance_automatic("a", now_ms=4000)
    assert s.current_state("a") == LauncherState.IN_GAME
    s.set_predicate("a", "socket_dropped")
    s.advance_automatic("a", now_ms=5000)
    assert s.current_state("a") == LauncherState.DISCONNECTED


# ---- characters ----

def test_register_character_card():
    s = _sys()
    s.register_state("a")
    s.register_character_card("a", _card())
    assert len(s.character_cards("a")) == 1


def test_register_duplicate_card_raises():
    s = _sys()
    s.register_state("a")
    s.register_character_card("a", _card())
    with pytest.raises(ValueError):
        s.register_character_card("a", _card())


def test_card_slots_free():
    s = _sys()
    s.register_state("a")
    assert s.card_slots_free("a") == MAX_CHARACTERS_PER_ACCOUNT
    s.register_character_card("a", _card())
    assert (
        s.card_slots_free("a")
        == MAX_CHARACTERS_PER_ACCOUNT - 1
    )


def test_max_characters_enforced():
    s = _sys()
    s.register_state("a")
    for i in range(MAX_CHARACTERS_PER_ACCOUNT):
        s.register_character_card("a", _card(char_id=f"c{i}"))
    with pytest.raises(ValueError):
        s.register_character_card("a", _card(char_id="extra"))


def test_bad_level_raises():
    s = _sys()
    s.register_state("a")
    with pytest.raises(ValueError):
        s.register_character_card("a", _card(level=0))


def test_last_played_picks_most_recent():
    s = _sys()
    s.register_state("a")
    s.register_character_card(
        "a", _card(char_id="c1", last_ms=1000),
    )
    s.register_character_card(
        "a", _card(char_id="c2", last_ms=2000),
    )
    s.register_character_card(
        "a", _card(char_id="c3", last_ms=1500),
    )
    assert s.last_played_card_id("a") == "c2"


def test_last_played_empty_account():
    s = _sys()
    s.register_state("a")
    assert s.last_played_card_id("a") == ""


def test_select_character_requires_state():
    s = _sys()
    s.register_state("a")
    s.register_character_card("a", _card())
    with pytest.raises(ValueError):
        s.select_character("a", "c1")


def test_select_character_unknown_raises():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    s.transition_to("a", LauncherState.CHARACTER_SELECT)
    with pytest.raises(KeyError):
        s.select_character("a", "ghost")


def test_select_character_sets_last_played():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    s.transition_to("a", LauncherState.CHARACTER_SELECT)
    s.register_character_card("a", _card(char_id="c1"))
    s.register_character_card(
        "a", _card(char_id="c2", last_ms=500),
    )
    s.select_character("a", "c2")
    assert s.last_played_card_id("a") == "c2"
    assert s.selected_character("a") == "c2"


# ---- server ----

def test_select_server_requires_state():
    s = _sys()
    s.register_state("a")
    with pytest.raises(ValueError):
        s.select_server("a", "us_east")


def test_select_server_unknown_raises():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    with pytest.raises(ValueError):
        s.select_server("a", "mars_one")


# ---- first play ----

def test_first_play_default_true():
    s = _sys()
    s.register_state("a")
    assert s.is_first_play("a") is True


def test_first_play_complete_flag():
    s = _sys()
    s.register_state("a")
    s.set_first_play_complete("a")
    assert s.is_first_play("a") is False


def test_first_play_sequence_name_constant():
    s = _sys()
    assert s.first_play_sequence_name() == FIRST_PLAY_SEQUENCE_NAME
    assert FIRST_PLAY_SEQUENCE_NAME == "first_play_intro"


# ---- pose ----

def test_launcher_pose_initial():
    s = _sys()
    s.register_state("a", region="ja", now_ms=10)
    pose = s.launcher_pose("a")
    assert isinstance(pose, LauncherPose)
    assert pose.state == LauncherState.SPLASH
    assert pose.region == "ja"
    assert pose.is_first_play is True
    assert pose.state_entered_ms == 10


def test_launcher_pose_after_state_change():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    pose = s.launcher_pose("a")
    assert pose.state == LauncherState.TITLE_SCREEN


def test_pose_carries_selected_server():
    s = _sys()
    s.register_state("a", now_ms=0)
    s.advance_automatic("a", now_ms=SPLASH_DURATION_MS)
    s.transition_to("a", LauncherState.PATCH_CHECK)
    s.set_predicate("a", "patches_clean")
    s.advance_automatic("a", now_ms=2000)
    s.transition_to("a", LauncherState.DISCORD_OAUTH_FLOW)
    s.set_predicate("a", "oauth_complete")
    s.advance_automatic("a", now_ms=3000)
    s.select_server("a", "jp_tokyo")
    pose = s.launcher_pose("a")
    assert pose.selected_server == "jp_tokyo"


def test_splash_duration_constant():
    assert SPLASH_DURATION_MS > 0


def test_cinematic_intro_duration_constant():
    assert CINEMATIC_INTRO_DURATION_MS > 0
