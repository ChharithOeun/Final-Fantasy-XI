"""Tests for the memorial registry."""
from __future__ import annotations

from server.memorial_registry import (
    DeathCause,
    MemorialRegistry,
    RESPECT_HONOR_REWARD,
)


def test_inscribe_basic():
    reg = MemorialRegistry()
    res = reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
        cause=DeathCause.NM_ENCOUNTER,
        age_in_game_days=120,
        epitaph="Stood her ground.",
        inscribed_at_seconds=100.0,
    )
    assert res.accepted
    assert res.entry.name == "Alice"
    assert reg.total_inscribed() == 1


def test_inscribe_empty_name_rejected():
    reg = MemorialRegistry()
    assert not reg.inscribe(
        name="   ", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    ).accepted


def test_inscribe_invalid_level_rejected():
    reg = MemorialRegistry()
    assert not reg.inscribe(
        name="Bob", nation="bastok",
        level_at_death=0, main_job_id="WAR",
    ).accepted


def test_double_inscribe_rejected():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    res2 = reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=80, main_job_id="WHM",
    )
    assert not res2.accepted


def test_lookup_returns_entry():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    e = reg.lookup("Alice")
    assert e is not None
    assert e.name == "Alice"


def test_lookup_unknown_returns_none():
    reg = MemorialRegistry()
    assert reg.lookup("ghost") is None


def test_for_nation_filters():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    reg.inscribe(
        name="Bob", nation="san_doria",
        level_at_death=80, main_job_id="WHM",
    )
    bastok = reg.for_nation("bastok")
    assert len(bastok) == 1
    assert bastok[0].name == "Alice"


def test_name_taken_check():
    reg = MemorialRegistry()
    assert not reg.name_taken("Alice")
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    assert reg.name_taken("Alice")


def test_pay_respects_unknown_rejected():
    reg = MemorialRegistry()
    res = reg.pay_respects(
        visitor_id="visitor", name="ghost",
    )
    assert not res.accepted


def test_pay_respects_first_time_grants_honor():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    res = reg.pay_respects(
        visitor_id="visitor", name="Alice",
    )
    assert res.accepted
    assert res.honor_gained == RESPECT_HONOR_REWARD


def test_pay_respects_twice_rejected():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    reg.pay_respects(
        visitor_id="visitor", name="Alice",
    )
    second = reg.pay_respects(
        visitor_id="visitor", name="Alice",
    )
    assert not second.accepted


def test_different_visitors_each_count():
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=75, main_job_id="WAR",
    )
    for v in ("v1", "v2", "v3"):
        res = reg.pay_respects(visitor_id=v, name="Alice")
        assert res.accepted
    assert reg.respects_count_for("Alice") == 3


def test_full_lifecycle_alice_remembered():
    """Alice falls in a Boss raid; gets inscribed; multiple
    visitors pay respects; name is locked."""
    reg = MemorialRegistry()
    reg.inscribe(
        name="Alice", nation="bastok",
        level_at_death=99, main_job_id="WAR",
        cause=DeathCause.BOSS_RAID,
        age_in_game_days=300,
        epitaph="She held the line for the party.",
        inscribed_at_seconds=1000.0,
    )
    assert reg.name_taken("Alice")
    # Multiple visitors
    for v in ("bob", "charlie", "dave"):
        res = reg.pay_respects(visitor_id=v, name="Alice")
        assert res.accepted
    # Bob can't pay twice
    again = reg.pay_respects(visitor_id="bob", name="Alice")
    assert not again.accepted
    # Total respects
    assert reg.respects_count_for("Alice") == 3
    # The entry is preserved
    e = reg.lookup("Alice")
    assert e.cause == DeathCause.BOSS_RAID
    assert "line" in e.epitaph
