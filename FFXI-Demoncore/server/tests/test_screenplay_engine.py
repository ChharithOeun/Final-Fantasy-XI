"""Tests for screenplay_engine."""
from __future__ import annotations

import pytest

from server.screenplay_engine import (
    Element,
    ElementKind,
    RevisionColor,
    Scene,
    Sequence,
    Slugline,
    SluglineKind,
    a_page_label,
    assign_line_numbers,
    build_scene,
    build_sequence,
    bump_revision,
    estimate_runtime_minutes,
    from_fountain,
    page_count,
    parse_slugline,
    to_fountain,
    validate_sequence,
)


# ---- Slugline parsing ----

def test_parse_slugline_int_day():
    s = parse_slugline("INT. BASTOK MARKETS - DAY")
    assert s.kind == SluglineKind.INT
    assert s.location == "BASTOK MARKETS"
    assert s.time_of_day == "DAY"


def test_parse_slugline_ext_night():
    s = parse_slugline("EXT. RONFAURE FOREST - NIGHT")
    assert s.kind == SluglineKind.EXT
    assert s.time_of_day == "NIGHT"


def test_parse_slugline_int_ext():
    s = parse_slugline("INT/EXT. AIRSHIP DECK - DUSK")
    assert s.kind == SluglineKind.INT_EXT
    assert s.location == "AIRSHIP DECK"


def test_parse_slugline_uppercases_location():
    s = parse_slugline("INT. lower jeuno - day")
    assert s.location == "LOWER JEUNO"


def test_parse_slugline_rejects_empty():
    with pytest.raises(ValueError):
        parse_slugline("")


def test_parse_slugline_rejects_malformed():
    with pytest.raises(ValueError):
        parse_slugline("BASTOK MARKETS DAY")


def test_slugline_render_round_trip():
    s = parse_slugline("INT. BASTOK MARKETS - DAY")
    assert s.render() == "INT. BASTOK MARKETS - DAY"


# ---- Element / scene validation ----

def test_dialogue_after_character_ok():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(kind=ElementKind.CHARACTER, text="CURILLA"),
        Element(
            kind=ElementKind.DIALOGUE,
            text="Hold the line.",
            character="CURILLA",
        ),
    )
    scene = build_scene("s1", sl, els)
    assert len(scene.elements) == 2


def test_dialogue_without_character_fails():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(
            kind=ElementKind.DIALOGUE,
            text="Hold the line.",
            character="CURILLA",
        ),
    )
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


def test_parenthetical_between_character_and_dialogue_ok():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(kind=ElementKind.CHARACTER, text="CURILLA"),
        Element(kind=ElementKind.PARENTHETICAL, text="weary"),
        Element(
            kind=ElementKind.DIALOGUE,
            text="Hold.",
            character="CURILLA",
        ),
    )
    build_scene("s1", sl, els)  # should not raise


def test_parenthetical_after_action_fails():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(kind=ElementKind.ACTION, text="A door slams."),
        Element(kind=ElementKind.PARENTHETICAL, text="off"),
    )
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


def test_lowercase_character_cue_rejected():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(kind=ElementKind.CHARACTER, text="curilla"),
    )
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


def test_empty_character_rejected():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (Element(kind=ElementKind.CHARACTER, text=""),)
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


def test_dual_dialogue_requires_both_speakers():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(
            kind=ElementKind.DUAL_DIALOGUE,
            text="hi",
            dual_pair=("CURILLA", ""),
        ),
    )
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


def test_dialogue_missing_character_field_fails():
    sl = parse_slugline("INT. CASTLE - DAY")
    els = (
        Element(kind=ElementKind.CHARACTER, text="CURILLA"),
        Element(kind=ElementKind.DIALOGUE, text="hi", character=""),
    )
    with pytest.raises(ValueError):
        build_scene("s1", sl, els)


# ---- Sequence build ----

def test_build_sequence_holds_scenes():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene(
        "s1", sl,
        (Element(kind=ElementKind.ACTION, text="A scene happens."),),
    )
    seq = build_sequence("seq_pilot", (sc,))
    assert seq.scenes[0].scene_id == "s1"
    assert seq.sequence_id == "seq_pilot"


def test_build_sequence_requires_scenes():
    with pytest.raises(ValueError):
        build_sequence("seq", ())


def test_build_sequence_requires_id():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    with pytest.raises(ValueError):
        build_sequence("", (sc,))


# ---- Runtime / page-count ----

def test_runtime_action_ten_words_is_quarter_minute():
    sl = parse_slugline("INT. A - DAY")
    text = " ".join(["word"] * 36)  # 36 words = 1 page action
    sc = build_scene(
        "s1", sl,
        (Element(kind=ElementKind.ACTION, text=text),),
    )
    seq = build_sequence("seq", (sc,))
    # 1 page action + 1 slugline-eighth = 1.125
    assert estimate_runtime_minutes(seq) == pytest.approx(1.125, abs=0.01)


def test_runtime_dialogue_is_heavier_per_word():
    sl = parse_slugline("INT. A - DAY")
    text = " ".join(["w"] * 25)  # 25 words = 1 page dialogue
    els = (
        Element(kind=ElementKind.CHARACTER, text="CURILLA"),
        Element(
            kind=ElementKind.DIALOGUE, text=text, character="CURILLA",
        ),
    )
    sc = build_scene("s1", sl, els)
    seq = build_sequence("seq", (sc,))
    assert estimate_runtime_minutes(seq) > 1.0


def test_runtime_zero_for_only_slugline():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("seq", (sc,))
    # one slugline = 1/8 page
    assert estimate_runtime_minutes(seq) == pytest.approx(0.125, abs=0.01)


def test_page_count_alias_matches_runtime():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("seq", (sc,))
    assert page_count(seq) == estimate_runtime_minutes(seq)


# ---- Revision bumps ----

def test_bump_revision_white_to_blue():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("seq", (sc,))
    bumped = bump_revision(seq)
    assert bumped.revision_color == RevisionColor.BLUE
    assert bumped.revision_number == 1


def test_bump_revision_explicit_target():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("seq", (sc,))
    bumped = bump_revision(seq, RevisionColor.PINK)
    assert bumped.revision_color == RevisionColor.PINK
    assert bumped.revision_number == 1


def test_bump_revision_advances_through_cycle():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("seq", (sc,))
    for _ in range(5):
        seq = bump_revision(seq)
    assert seq.revision_number == 5
    # WHITE → BLUE → PINK → YELLOW → GREEN → GOLDENROD
    assert seq.revision_color == RevisionColor.GOLDENROD


def test_a_page_label_first_revision():
    assert a_page_label(12, 1) == "12A"


def test_a_page_label_second_revision():
    assert a_page_label(12, 2) == "12B"


def test_a_page_label_double_letter():
    assert a_page_label(12, 27) == "12AA"


def test_a_page_label_rejects_zero_line():
    with pytest.raises(ValueError):
        a_page_label(0, 1)


def test_assign_line_numbers_indexes_one_based():
    sl = parse_slugline("INT. A - DAY")
    els = (
        Element(kind=ElementKind.ACTION, text="x"),
        Element(kind=ElementKind.ACTION, text="y"),
    )
    sc = build_scene("s1", sl, els)
    sc2 = assign_line_numbers(sc)
    assert sc2.elements[0].line_no == 1
    assert sc2.elements[1].line_no == 2


# ---- Fountain export / import ----

def test_to_fountain_emits_title():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("pilot", (sc,))
    out = to_fountain(seq)
    assert "Title: pilot" in out
    assert "INT. A - DAY" in out


def test_to_fountain_includes_revision_color():
    sl = parse_slugline("INT. A - DAY")
    sc = build_scene("s1", sl, ())
    seq = build_sequence("pilot", (sc,))
    seq = bump_revision(seq)  # blue
    out = to_fountain(seq)
    assert "blue" in out


def test_from_fountain_round_trip_basic():
    text = (
        "Title: pilot\n\n"
        "INT. CASTLE - DAY\n\n"
        "A door opens.\n\n"
        "CURILLA\n"
        "Hold the line.\n\n"
    )
    seq = from_fountain(text)
    assert seq.sequence_id == "pilot"
    assert len(seq.scenes) == 1
    assert seq.scenes[0].slugline.location == "CASTLE"


def test_from_fountain_picks_up_dialogue():
    text = (
        "INT. CASTLE - DAY\n\n"
        "CURILLA\nHold the line.\n\n"
    )
    seq = from_fountain(text)
    kinds = [e.kind for e in seq.scenes[0].elements]
    assert ElementKind.CHARACTER in kinds
    assert ElementKind.DIALOGUE in kinds


def test_from_fountain_picks_up_transition():
    text = "INT. A - DAY\n\nA scene.\n\n> CUT TO:\n"
    seq = from_fountain(text)
    kinds = [e.kind for e in seq.scenes[0].elements]
    assert ElementKind.TRANSITION in kinds


def test_from_fountain_picks_up_shot():
    text = "INT. A - DAY\n\n!ANGLE ON CURILLA\n"
    seq = from_fountain(text)
    kinds = [e.kind for e in seq.scenes[0].elements]
    assert ElementKind.SHOT in kinds


def test_from_fountain_rejects_no_scenes():
    with pytest.raises(ValueError):
        from_fountain("Title: pilot\n\nJust some random text\n")


def test_validate_sequence_walks_all_scenes():
    sl = parse_slugline("INT. A - DAY")
    good_sc = build_scene(
        "s1", sl,
        (Element(kind=ElementKind.ACTION, text="hi"),),
    )
    seq = build_sequence("seq", (good_sc,))
    validate_sequence(seq)  # should not raise
