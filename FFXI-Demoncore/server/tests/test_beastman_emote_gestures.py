"""Tests for the beastman emote gestures."""
from __future__ import annotations

from server.beastman_emote_gestures import (
    BeastmanEmoteGestures,
    EmoteScope,
)
from server.beastman_playable_races import BeastmanRace


def test_register():
    e = BeastmanEmoteGestures()
    res = e.register_emote(
        emote_id="cheer",
        scope=EmoteScope.UNIVERSAL,
    )
    assert res is not None


def test_register_duplicate():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="cheer",
        scope=EmoteScope.UNIVERSAL,
    )
    res = e.register_emote(
        emote_id="cheer",
        scope=EmoteScope.YAGUDO,
    )
    assert res is None


def test_register_empty_id():
    e = BeastmanEmoteGestures()
    res = e.register_emote(
        emote_id="",
        scope=EmoteScope.UNIVERSAL,
    )
    assert res is None


def test_register_payload_without_zone_rejected():
    e = BeastmanEmoteGestures()
    res = e.register_emote(
        emote_id="ritual",
        scope=EmoteScope.YAGUDO,
        ritual_payload="cue",
    )
    assert res is None


def test_perform_universal():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="cheer",
        scope=EmoteScope.UNIVERSAL,
    )
    res = e.perform(
        player_id="kraw",
        race=BeastmanRace.YAGUDO,
        emote_id="cheer",
        zone_id="anywhere",
    )
    assert res.accepted


def test_perform_race_locked_match():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="wing_flare",
        scope=EmoteScope.YAGUDO,
    )
    res = e.perform(
        player_id="kraw",
        race=BeastmanRace.YAGUDO,
        emote_id="wing_flare",
        zone_id="anywhere",
    )
    assert res.accepted


def test_perform_race_locked_mismatch():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="wing_flare",
        scope=EmoteScope.YAGUDO,
    )
    res = e.perform(
        player_id="garesh",
        race=BeastmanRace.ORC,
        emote_id="wing_flare",
        zone_id="anywhere",
    )
    assert not res.accepted


def test_perform_unknown_emote():
    e = BeastmanEmoteGestures()
    res = e.perform(
        player_id="kraw",
        race=BeastmanRace.YAGUDO,
        emote_id="ghost",
        zone_id="anywhere",
    )
    assert not res.accepted


def test_ritual_triggers_in_correct_zone():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="stone_bow",
        scope=EmoteScope.QUADAV,
        ritual_zone_id="palborough_altar",
        ritual_payload="quest_cue_a",
    )
    res = e.perform(
        player_id="zlot",
        race=BeastmanRace.QUADAV,
        emote_id="stone_bow",
        zone_id="palborough_altar",
    )
    assert res.accepted
    assert res.triggered_ritual
    assert res.ritual_payload == "quest_cue_a"


def test_ritual_doesnt_trigger_elsewhere():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="stone_bow",
        scope=EmoteScope.QUADAV,
        ritual_zone_id="palborough_altar",
        ritual_payload="quest_cue_a",
    )
    res = e.perform(
        player_id="zlot",
        race=BeastmanRace.QUADAV,
        emote_id="stone_bow",
        zone_id="elsewhere",
    )
    assert res.accepted
    assert not res.triggered_ritual
    assert res.ritual_payload == ""


def test_available_for_includes_universal():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="cheer",
        scope=EmoteScope.UNIVERSAL,
    )
    e.register_emote(
        emote_id="wing_flare",
        scope=EmoteScope.YAGUDO,
    )
    e.register_emote(
        emote_id="roar_of_kin",
        scope=EmoteScope.ORC,
    )
    av = e.available_for(race=BeastmanRace.YAGUDO)
    ids = {x.emote_id for x in av}
    assert "cheer" in ids
    assert "wing_flare" in ids
    assert "roar_of_kin" not in ids


def test_available_for_orc():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="wing_flare",
        scope=EmoteScope.YAGUDO,
    )
    e.register_emote(
        emote_id="roar_of_kin",
        scope=EmoteScope.ORC,
    )
    av = e.available_for(race=BeastmanRace.ORC)
    ids = {x.emote_id for x in av}
    assert ids == {"roar_of_kin"}


def test_available_for_lamia():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="coil_dance",
        scope=EmoteScope.LAMIA,
    )
    av = e.available_for(race=BeastmanRace.LAMIA)
    assert len(av) == 1
    assert av[0].emote_id == "coil_dance"


def test_available_for_quadav():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="stone_bow",
        scope=EmoteScope.QUADAV,
    )
    av = e.available_for(race=BeastmanRace.QUADAV)
    assert len(av) == 1


def test_total_emotes():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="a", scope=EmoteScope.UNIVERSAL,
    )
    e.register_emote(
        emote_id="b", scope=EmoteScope.YAGUDO,
    )
    assert e.total_emotes() == 2


def test_universal_available_to_all_races():
    e = BeastmanEmoteGestures()
    e.register_emote(
        emote_id="cheer", scope=EmoteScope.UNIVERSAL,
    )
    for race in (
        BeastmanRace.YAGUDO,
        BeastmanRace.QUADAV,
        BeastmanRace.LAMIA,
        BeastmanRace.ORC,
    ):
        res = e.perform(
            player_id="x",
            race=race,
            emote_id="cheer",
            zone_id="z",
        )
        assert res.accepted
