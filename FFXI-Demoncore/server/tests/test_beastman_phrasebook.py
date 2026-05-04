"""Tests for the beastman phrasebook."""
from __future__ import annotations

from server.beastman_phrasebook import (
    BeastmanPhrasebook,
    Dialect,
)


def _seed(p):
    p.register_phrase(
        phrase_id="hello",
        translations={
            Dialect.YAGUDO_TONGUE: "Krak-krak!",
            Dialect.QUADAV_TONGUE: "Krrkr.",
            Dialect.LAMIA_TONGUE: "Sssalut.",
            Dialect.ORC_TONGUE: "Grogg.",
            Dialect.TRADE_PIDGIN: "Hello, friend.",
        },
    )


def test_register():
    p = BeastmanPhrasebook()
    _seed(p)
    assert p.total_phrases() == 1


def test_register_duplicate():
    p = BeastmanPhrasebook()
    _seed(p)
    res = p.register_phrase(
        phrase_id="hello",
        translations={Dialect.TRADE_PIDGIN: "x"},
    )
    assert res is None


def test_register_empty_phrase_id():
    p = BeastmanPhrasebook()
    res = p.register_phrase(
        phrase_id="",
        translations={Dialect.TRADE_PIDGIN: "x"},
    )
    assert res is None


def test_register_no_translations():
    p = BeastmanPhrasebook()
    res = p.register_phrase(
        phrase_id="x",
        translations={},
    )
    assert res is None


def test_register_missing_pidgin():
    p = BeastmanPhrasebook()
    res = p.register_phrase(
        phrase_id="x",
        translations={Dialect.YAGUDO_TONGUE: "krak"},
    )
    assert res is None


def test_register_empty_translation_string():
    p = BeastmanPhrasebook()
    res = p.register_phrase(
        phrase_id="x",
        translations={
            Dialect.TRADE_PIDGIN: "",
        },
    )
    assert res is None


def test_set_preferred():
    p = BeastmanPhrasebook()
    assert p.set_preferred(
        player_id="kraw",
        dialect=Dialect.YAGUDO_TONGUE,
    )


def test_set_preferred_empty_player_rejected():
    p = BeastmanPhrasebook()
    res = p.set_preferred(
        player_id="",
        dialect=Dialect.YAGUDO_TONGUE,
    )
    assert not res


def test_preferred_for_default():
    p = BeastmanPhrasebook()
    assert p.preferred_for(
        player_id="ghost",
    ) == Dialect.TRADE_PIDGIN


def test_preferred_for_set():
    p = BeastmanPhrasebook()
    p.set_preferred(
        player_id="kraw",
        dialect=Dialect.LAMIA_TONGUE,
    )
    assert p.preferred_for(
        player_id="kraw",
    ) == Dialect.LAMIA_TONGUE


def test_translate_default_pidgin():
    p = BeastmanPhrasebook()
    _seed(p)
    res = p.translate(
        phrase_id="hello", recipient_id="ghost",
    )
    assert res.accepted
    assert res.text == "Hello, friend."
    assert res.dialect_used == Dialect.TRADE_PIDGIN


def test_translate_yagudo_recipient():
    p = BeastmanPhrasebook()
    _seed(p)
    p.set_preferred(
        player_id="kraw",
        dialect=Dialect.YAGUDO_TONGUE,
    )
    res = p.translate(
        phrase_id="hello", recipient_id="kraw",
    )
    assert res.text == "Krak-krak!"
    assert res.dialect_used == Dialect.YAGUDO_TONGUE


def test_translate_orc_recipient():
    p = BeastmanPhrasebook()
    _seed(p)
    p.set_preferred(
        player_id="garesh",
        dialect=Dialect.ORC_TONGUE,
    )
    res = p.translate(
        phrase_id="hello", recipient_id="garesh",
    )
    assert res.text == "Grogg."


def test_translate_unknown_phrase():
    p = BeastmanPhrasebook()
    res = p.translate(
        phrase_id="ghost", recipient_id="kraw",
    )
    assert not res.accepted


def test_translate_falls_back_to_pidgin():
    p = BeastmanPhrasebook()
    p.register_phrase(
        phrase_id="rare",
        translations={
            Dialect.TRADE_PIDGIN: "Untranslated",
        },
    )
    p.set_preferred(
        player_id="kraw",
        dialect=Dialect.YAGUDO_TONGUE,
    )
    res = p.translate(
        phrase_id="rare", recipient_id="kraw",
    )
    assert res.text == "Untranslated"
    assert res.dialect_used == Dialect.TRADE_PIDGIN


def test_total_phrases():
    p = BeastmanPhrasebook()
    _seed(p)
    p.register_phrase(
        phrase_id="goodbye",
        translations={
            Dialect.TRADE_PIDGIN: "Bye.",
        },
    )
    assert p.total_phrases() == 2


def test_per_player_preferred_isolation():
    p = BeastmanPhrasebook()
    _seed(p)
    p.set_preferred(
        player_id="alice",
        dialect=Dialect.YAGUDO_TONGUE,
    )
    p.set_preferred(
        player_id="bob",
        dialect=Dialect.ORC_TONGUE,
    )
    a = p.translate(phrase_id="hello", recipient_id="alice")
    b = p.translate(phrase_id="hello", recipient_id="bob")
    assert a.text == "Krak-krak!"
    assert b.text == "Grogg."
