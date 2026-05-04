"""Tests for the beastman language barrier."""
from __future__ import annotations

from server.beastman_language_barrier import (
    BeastmanLanguageBarrier,
    LanguageKind,
)


def test_declare_native():
    b = BeastmanLanguageBarrier()
    assert b.declare_native(
        player_id="alice",
        language=LanguageKind.VANADIELIAN,
    )


def test_declare_native_by_race_hume():
    b = BeastmanLanguageBarrier()
    assert b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    assert b.can_understand(
        listener_id="alice",
        language=LanguageKind.VANADIELIAN,
    )


def test_declare_native_by_race_orc():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="brokenfang", race="orc",
    )
    assert b.can_understand(
        listener_id="brokenfang",
        language=LanguageKind.ORCISH,
    )


def test_declare_native_by_race_unknown_rejected():
    b = BeastmanLanguageBarrier()
    assert not b.declare_native_by_race(
        player_id="alice", race="dragon",
    )


def test_unconfigured_listener_understands_vanadielian():
    b = BeastmanLanguageBarrier()
    assert b.can_understand(
        listener_id="alice",
        language=LanguageKind.VANADIELIAN,
    )


def test_unconfigured_listener_blocks_yagudic():
    b = BeastmanLanguageBarrier()
    assert not b.can_understand(
        listener_id="alice",
        language=LanguageKind.YAGUDIC,
    )


def test_vanadielian_universally_understood():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="brokenfang", race="orc",
    )
    assert b.can_understand(
        listener_id="brokenfang",
        language=LanguageKind.VANADIELIAN,
    )


def test_translator_quest_unlocks_language():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    assert b.translator_quest_complete(
        player_id="alice",
        language=LanguageKind.YAGUDIC,
    )
    assert b.can_understand(
        listener_id="alice",
        language=LanguageKind.YAGUDIC,
    )


def test_translator_quest_native_rejected():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    assert not b.translator_quest_complete(
        player_id="alice",
        language=LanguageKind.VANADIELIAN,
    )


def test_translator_quest_double_rejected():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    b.translator_quest_complete(
        player_id="alice",
        language=LanguageKind.YAGUDIC,
    )
    assert not b.translator_quest_complete(
        player_id="alice",
        language=LanguageKind.YAGUDIC,
    )


def test_translator_unknown_player_rejected():
    b = BeastmanLanguageBarrier()
    assert not b.translator_quest_complete(
        player_id="ghost",
        language=LanguageKind.YAGUDIC,
    )


def test_translate_native_speech_native_flag():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    res = b.translate(
        listener_id="alice", speaker_id="bob",
        speech="Hail, friend.",
        speech_language=LanguageKind.VANADIELIAN,
    )
    assert res.rendered_text == "Hail, friend."
    assert res.is_native


def test_translate_understood_via_quest():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    b.translator_quest_complete(
        player_id="alice",
        language=LanguageKind.YAGUDIC,
    )
    res = b.translate(
        listener_id="alice", speaker_id="bishop",
        speech="The relics await your hands.",
        speech_language=LanguageKind.YAGUDIC,
    )
    assert res.is_translated
    assert not res.is_native
    assert res.rendered_text == (
        "The relics await your hands."
    )


def test_translate_blocked_renders_gibberish():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    res = b.translate(
        listener_id="alice", speaker_id="orc_grunt",
        speech="grumblesomething threatening here",
        speech_language=LanguageKind.ORCISH,
    )
    assert not res.is_translated
    assert "grrah" in res.rendered_text


def test_translate_empty_speech_empty_render():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="alice", race="hume",
    )
    res = b.translate(
        listener_id="alice", speaker_id="x",
        speech="",
        speech_language=LanguageKind.YAGUDIC,
    )
    assert res.rendered_text == ""


def test_translate_unconfigured_listener_blocks():
    b = BeastmanLanguageBarrier()
    res = b.translate(
        listener_id="alice", speaker_id="bob",
        speech="hi there",
        speech_language=LanguageKind.YAGUDIC,
    )
    assert not res.is_translated


def test_orc_understands_orcish_natively():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="brokenfang", race="orc",
    )
    res = b.translate(
        listener_id="brokenfang", speaker_id="warlord",
        speech="To the iron cradle!",
        speech_language=LanguageKind.ORCISH,
    )
    assert res.is_native


def test_orc_doesnt_understand_yagudic_without_quest():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="brokenfang", race="orc",
    )
    res = b.translate(
        listener_id="brokenfang", speaker_id="bishop",
        speech="The relics await",
        speech_language=LanguageKind.YAGUDIC,
    )
    assert not res.is_translated


def test_total_listeners_count():
    b = BeastmanLanguageBarrier()
    b.declare_native_by_race(
        player_id="a", race="hume",
    )
    b.declare_native_by_race(
        player_id="b", race="orc",
    )
    assert b.total_listeners() == 2
