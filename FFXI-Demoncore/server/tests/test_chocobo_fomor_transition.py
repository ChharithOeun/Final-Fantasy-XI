"""Tests for chocobo fomor transition."""
from __future__ import annotations

from server.chocobo_colors import ChocoboColor
from server.chocobo_fomor_transition import (
    ChocoboFomorTransition,
    DeathOutcome,
)


def test_yellow_dies_into_fomor():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.YELLOW,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.accepted
    assert res.outcome == DeathOutcome.FOMOR
    assert res.fomor_variant_id == "fomor_yellow"


def test_red_fomor_variant():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.RED,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_red"


def test_white_fomor_variant():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.WHITE,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_white"


def test_grey_fomor_variant():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.GREY,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_grey"


def test_rainbow_dies_into_rex_egg():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="rainbow_c1",
        color=ChocoboColor.RAINBOW,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.accepted
    assert res.outcome == DeathOutcome.RAINBOW_EGG_REX
    assert res.rex_egg_id == "rainbow_c1_rainbow_rex_egg"
    assert res.fomor_variant_id == ""


def test_double_record_blocked():
    t = ChocoboFomorTransition()
    t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.YELLOW,
        owner_id="kraw",
        now_seconds=0,
    )
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.YELLOW,
        owner_id="kraw",
        now_seconds=10,
    )
    assert not res.accepted


def test_missing_chocobo_id_rejected():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="",
        color=ChocoboColor.YELLOW,
        owner_id="kraw",
        now_seconds=0,
    )
    assert not res.accepted


def test_missing_owner_rejected():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.YELLOW,
        owner_id="",
        now_seconds=0,
    )
    assert not res.accepted


def test_lookup_basic():
    t = ChocoboFomorTransition()
    t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.BLUE,
        owner_id="kraw",
        now_seconds=42,
    )
    rec = t.lookup(chocobo_id="c1")
    assert rec is not None
    assert rec.fomor_variant_id == "fomor_blue"
    assert rec.died_at == 42


def test_lookup_unknown():
    t = ChocoboFomorTransition()
    assert t.lookup(chocobo_id="ghost") is None


def test_total_records():
    t = ChocoboFomorTransition()
    for i in range(5):
        t.record_death(
            chocobo_id=f"c{i}",
            color=ChocoboColor.YELLOW,
            owner_id=f"p{i}",
            now_seconds=i,
        )
    assert t.total_records() == 5


def test_all_color_variants_have_fomor():
    t = ChocoboFomorTransition()
    non_rainbow = [
        c for c in ChocoboColor if c != ChocoboColor.RAINBOW
    ]
    for i, c in enumerate(non_rainbow):
        res = t.record_death(
            chocobo_id=f"c_{i}",
            color=c,
            owner_id="kraw",
            now_seconds=i,
        )
        assert res.accepted
        assert res.fomor_variant_id.startswith("fomor_")


def test_brown_fomor():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.BROWN,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_brown"


def test_green_fomor():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.GREEN,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_green"


def test_light_blue_fomor():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.LIGHT_BLUE,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_light_blue"


def test_light_purple_fomor():
    t = ChocoboFomorTransition()
    res = t.record_death(
        chocobo_id="c1",
        color=ChocoboColor.LIGHT_PURPLE,
        owner_id="kraw",
        now_seconds=0,
    )
    assert res.fomor_variant_id == "fomor_light_purple"
