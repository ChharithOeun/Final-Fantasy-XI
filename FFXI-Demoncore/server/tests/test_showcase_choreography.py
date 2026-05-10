"""Tests for showcase_choreography."""
from __future__ import annotations

import pytest

from server.showcase_choreography import (
    BUILTIN_BASTOK_MARKETS_DEMO,
    Beat,
    BeatTrigger,
    ChoreographySequence,
    ShowcaseChoreography,
)


def _beat(
    beat_id: str = "x",
    idx: int = 0,
    trigger: BeatTrigger = BeatTrigger.PLAYER_ENTERS_VOLUME,
    volume: str = "vol",
    handoff: str = "WIDE",
    fallback: str = "",
    duration: float = 5.0,
) -> Beat:
    return Beat(
        beat_id=beat_id,
        sequence_index=idx,
        trigger=trigger,
        zone_id="bastok_markets",
        location_volume_id=volume,
        camera_handoff=handoff,
        dialogue_line_ids=(),
        expected_duration_s=duration,
        mob_spawns=(),
        music_cue_id="",
        fallback_if_skipped=fallback,
    )


def _seq(name: str = "test_seq", beats: int = 2) -> ChoreographySequence:
    return ChoreographySequence(
        seq_name=name,
        title=name,
        beats=tuple(
            _beat(f"b{i}", i, fallback=f"b{i+1}" if i + 1 < beats else "")
            for i in range(beats)
        ),
    )


# ---- Builtin sequence ----

def test_builtin_demo_has_at_least_8_beats():
    assert len(BUILTIN_BASTOK_MARKETS_DEMO.beats) >= 8


def test_builtin_demo_in_bastok_markets():
    for b in BUILTIN_BASTOK_MARKETS_DEMO.beats:
        assert b.zone_id == "bastok_markets"


def test_builtin_demo_includes_required_beats():
    ids = {b.beat_id for b in BUILTIN_BASTOK_MARKETS_DEMO.beats}
    for needed in (
        "spawn_in_mines",
        "emerge_to_markets",
        "cid_forging",
        "volker_quest_handoff",
        "crowd_ambient_walk",
        "bandit_raid_trigger",
        "iron_eater_shadow_skillchain",
        "iron_eater_intro",
    ):
        assert needed in ids, f"missing beat: {needed}"


def test_builtin_demo_indexes_monotonic():
    indices = [
        b.sequence_index for b in BUILTIN_BASTOK_MARKETS_DEMO.beats
    ]
    assert indices == sorted(indices)


def test_builtin_demo_iron_eater_intro_is_terminal():
    last = BUILTIN_BASTOK_MARKETS_DEMO.beats[-1]
    assert last.beat_id == "iron_eater_intro"
    assert last.fallback_if_skipped == ""


def test_builtin_demo_skillchain_uses_skillchain_trigger():
    ids = {
        b.beat_id: b.trigger
        for b in BUILTIN_BASTOK_MARKETS_DEMO.beats
    }
    assert (
        ids["iron_eater_shadow_skillchain"]
        == BeatTrigger.SKILLCHAIN_COMPLETED
    )


def test_builtin_demo_iron_eater_uses_phase_trigger():
    ids = {
        b.beat_id: b.trigger
        for b in BUILTIN_BASTOK_MARKETS_DEMO.beats
    }
    assert ids["iron_eater_intro"] == BeatTrigger.MOB_PHASE_X


def test_with_bastok_demo_loads_sequence():
    sc = ShowcaseChoreography.with_bastok_demo()
    assert "bastok_markets_demo" in [
        s.seq_name for s in sc._sequences.values()
    ]


# ---- Registration ----

def test_register_sequence_returns_sequence():
    sc = ShowcaseChoreography()
    out = sc.register_sequence(_seq("a"))
    assert out.seq_name == "a"


def test_register_sequence_duplicate_raises():
    sc = ShowcaseChoreography()
    sc.register_sequence(_seq("a"))
    with pytest.raises(ValueError):
        sc.register_sequence(_seq("a"))


def test_register_sequence_empty_name_raises():
    sc = ShowcaseChoreography()
    with pytest.raises(ValueError):
        sc.register_sequence(
            ChoreographySequence(
                seq_name="", title="x", beats=(_beat(),),
            ),
        )


def test_register_sequence_no_beats_raises():
    sc = ShowcaseChoreography()
    with pytest.raises(ValueError):
        sc.register_sequence(
            ChoreographySequence(
                seq_name="a", title="x", beats=(),
            ),
        )


def test_register_sequence_duplicate_beat_id_raises():
    sc = ShowcaseChoreography()
    bad = ChoreographySequence(
        seq_name="a", title="x",
        beats=(_beat("b1", 0), _beat("b1", 1)),
    )
    with pytest.raises(ValueError):
        sc.register_sequence(bad)


def test_register_sequence_non_monotonic_raises():
    sc = ShowcaseChoreography()
    bad = ChoreographySequence(
        seq_name="a", title="x",
        beats=(_beat("b1", 5), _beat("b2", 1)),
    )
    with pytest.raises(ValueError):
        sc.register_sequence(bad)


def test_register_beat_appends():
    sc = ShowcaseChoreography()
    sc.register_sequence(_seq("a", beats=2))
    sc.register_beat(
        "a",
        _beat(beat_id="extra", idx=2),
    )
    assert len(sc.lookup_sequence("a").beats) == 3


def test_register_beat_unknown_seq_raises():
    sc = ShowcaseChoreography()
    with pytest.raises(KeyError):
        sc.register_beat("nope", _beat())


def test_register_beat_duplicate_id_raises():
    sc = ShowcaseChoreography()
    sc.register_sequence(_seq("a", beats=2))
    with pytest.raises(ValueError):
        sc.register_beat(
            "a", _beat(beat_id="b0", idx=2),
        )


def test_register_beat_lower_index_raises():
    sc = ShowcaseChoreography()
    sc.register_sequence(_seq("a", beats=2))
    with pytest.raises(ValueError):
        sc.register_beat(
            "a", _beat(beat_id="late", idx=0),
        )


# ---- Lookups ----

def test_lookup_sequence_unknown_raises():
    sc = ShowcaseChoreography()
    with pytest.raises(KeyError):
        sc.lookup_sequence("nope")


def test_sequence_for_demo_returns_beats():
    sc = ShowcaseChoreography.with_bastok_demo()
    beats = sc.sequence_for_demo("bastok_markets_demo")
    assert len(beats) >= 8


def test_beat_at_index_finds_beat():
    sc = ShowcaseChoreography.with_bastok_demo()
    b = sc.beat_at_index("bastok_markets_demo", 0)
    assert b.beat_id == "spawn_in_mines"


def test_beat_at_index_unknown_raises():
    sc = ShowcaseChoreography.with_bastok_demo()
    with pytest.raises(KeyError):
        sc.beat_at_index("bastok_markets_demo", 99)


# ---- Advance ----

def test_advance_returns_next():
    sc = ShowcaseChoreography.with_bastok_demo()
    nxt = sc.advance("bastok_markets_demo", "spawn_in_mines")
    assert nxt is not None
    assert nxt.beat_id == "emerge_to_markets"


def test_advance_terminal_returns_none():
    sc = ShowcaseChoreography.with_bastok_demo()
    nxt = sc.advance(
        "bastok_markets_demo", "iron_eater_intro",
    )
    assert nxt is None


def test_advance_unknown_beat_raises():
    sc = ShowcaseChoreography.with_bastok_demo()
    with pytest.raises(KeyError):
        sc.advance("bastok_markets_demo", "no_such_beat")


# ---- Fallback ----

def test_fallback_for_existing_beat():
    sc = ShowcaseChoreography.with_bastok_demo()
    fb = sc.fallback_for(
        "bastok_markets_demo", "spawn_in_mines",
    )
    assert fb is not None
    assert fb.beat_id == "emerge_to_markets"


def test_fallback_for_terminal_beat():
    sc = ShowcaseChoreography.with_bastok_demo()
    fb = sc.fallback_for(
        "bastok_markets_demo", "iron_eater_intro",
    )
    assert fb is None


# ---- Aggregations ----

def test_total_duration_s():
    sc = ShowcaseChoreography.with_bastok_demo()
    total = sc.total_duration_s("bastok_markets_demo")
    # Eight beats sum well over a minute, around 130s.
    assert total > 60.0


def test_all_dialogue_line_ids_collected():
    sc = ShowcaseChoreography.with_bastok_demo()
    lines = sc.all_dialogue_line_ids("bastok_markets_demo")
    assert "vline_volker_handoff_001" in lines
    assert "vline_cid_forging_001" in lines


def test_all_mob_spawns_collected():
    sc = ShowcaseChoreography.with_bastok_demo()
    spawns = sc.all_mob_spawns("bastok_markets_demo")
    assert "mob_iron_eater_boss" in spawns
    assert "mob_bandit_a" in spawns


def test_all_music_cues_collected():
    sc = ShowcaseChoreography.with_bastok_demo()
    cues = sc.all_music_cues("bastok_markets_demo")
    assert "cue_iron_eater_theme" in cues


# ---- Validation ----

def test_validate_sequence_passes_builtin():
    sc = ShowcaseChoreography.with_bastok_demo()
    sc.validate_sequence("bastok_markets_demo")


def test_validate_sequence_unknown_fallback_raises():
    sc = ShowcaseChoreography()
    bad_beat = _beat("b0", 0, fallback="ghost_beat")
    sc.register_sequence(
        ChoreographySequence(
            seq_name="bad", title="bad", beats=(bad_beat,),
        ),
    )
    with pytest.raises(ValueError):
        sc.validate_sequence("bad")


def test_validate_sequence_unknown_sequence_raises():
    sc = ShowcaseChoreography()
    with pytest.raises(KeyError):
        sc.validate_sequence("nope")
