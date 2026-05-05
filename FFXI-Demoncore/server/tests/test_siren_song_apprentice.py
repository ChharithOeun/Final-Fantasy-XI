"""Tests for siren song apprentice."""
from __future__ import annotations

from server.siren_song_apprentice import (
    ApprenticeSpell,
    SirenSongApprentice,
)


def test_learn_happy():
    s = SirenSongApprentice()
    r = s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    assert r.accepted is True


def test_learn_wrong_job():
    s = SirenSongApprentice()
    r = s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="WAR",
        faction_holding_court="tide_keepers",
        mermaid_rep=200,
    )
    assert r.accepted is False
    assert r.reason == "BRD required"


def test_learn_wrong_council():
    s = SirenSongApprentice()
    r = s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="deep_faithful",
        mermaid_rep=200,
    )
    assert r.accepted is False
    assert r.reason == "council not TIDE_KEEPERS"


def test_learn_low_rep():
    s = SirenSongApprentice()
    r = s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=50,
    )
    assert r.accepted is False
    assert r.reason == "mermaid rep too low"


def test_learn_blank_player():
    s = SirenSongApprentice()
    r = s.learn(
        player_id="",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    assert r.accepted is False


def test_learn_duplicate():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    r = s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    assert r.accepted is False


def test_cast_happy():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.HYMN_LULL,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    r = s.cast(
        player_id="p",
        spell=ApprenticeSpell.HYMN_LULL,
        target_kind="pve",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
        now_seconds=10,
    )
    assert r.accepted is True
    assert r.duration_seconds == 60


def test_cast_unknown_spell():
    s = SirenSongApprentice()
    r = s.cast(
        player_id="p",
        spell=ApprenticeSpell.HYMN_LULL,
        target_kind="pve",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "not learned"


def test_cast_pvp_forbidden():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=200,
    )
    r = s.cast(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        target_kind="pvp",
        faction_holding_court="tide_keepers",
        mermaid_rep=200,
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "pvp use forbidden"


def test_cast_council_revokes():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=200,
    )
    # council shifts to merchant_pearl after learning
    r = s.cast(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        target_kind="pve",
        faction_holding_court="merchant_pearl",
        mermaid_rep=200,
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "council revoked"


def test_cast_rep_drop_revokes():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=200,
    )
    r = s.cast(
        player_id="p",
        spell=ApprenticeSpell.WHISPER_BIND,
        target_kind="pve",
        faction_holding_court="tide_keepers",
        mermaid_rep=10,
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "rep below threshold"


def test_knows_default_false():
    s = SirenSongApprentice()
    assert s.knows(
        player_id="p", spell=ApprenticeSpell.WHISPER_BIND,
    ) is False


def test_knows_after_learn():
    s = SirenSongApprentice()
    s.learn(
        player_id="p",
        spell=ApprenticeSpell.CHORD_DRIFT,
        job="BRD",
        faction_holding_court="tide_keepers",
        mermaid_rep=100,
    )
    assert s.knows(
        player_id="p", spell=ApprenticeSpell.CHORD_DRIFT,
    ) is True
