"""Tests for per-entity persistent memory."""
from __future__ import annotations

import pytest

from server.entity_memory import (
    DEFAULT_HALF_LIFE_SECONDS,
    SALIENCE_FORGOTTEN,
    EntityMemoryStore,
    Memory,
    MemoryKind,
    MemoryRegistry,
    decay_salience,
)


def test_remember_basic():
    s = EntityMemoryStore(entity_id="curilla")
    m = s.remember(
        kind=MemoryKind.HELPED, other_entity_id="alice",
        salience=80, now_seconds=0.0,
        details="returned the lost amulet",
    )
    assert m.kind == MemoryKind.HELPED
    assert m.other_entity_id == "alice"
    assert s.memories == (m,)


def test_salience_out_of_range_rejected():
    with pytest.raises(ValueError):
        Memory(
            memory_id="m_bad", kind=MemoryKind.HELPED,
            other_entity_id="alice", initial_salience=200,
            created_at_seconds=0.0,
        )


def test_decay_salience_basic_half_life():
    """At one half-life elapsed, salience halves."""
    m = Memory(
        memory_id="m1", kind=MemoryKind.WITNESSED,
        other_entity_id="alice",
        initial_salience=80, created_at_seconds=0.0,
    )
    s = decay_salience(
        m, now_seconds=DEFAULT_HALF_LIFE_SECONDS,
        half_life_seconds=DEFAULT_HALF_LIFE_SECONDS,
    )
    assert 38 <= s <= 42       # ~40, allowing for rounding


def test_traumatic_memories_decay_slower():
    """KILLED memories decay 8x slower than WITNESSED."""
    killed = Memory(
        memory_id="k1", kind=MemoryKind.KILLED,
        other_entity_id="boss", initial_salience=100,
        created_at_seconds=0.0,
    )
    witnessed = Memory(
        memory_id="w1", kind=MemoryKind.WITNESSED,
        other_entity_id="boss", initial_salience=100,
        created_at_seconds=0.0,
    )
    one_week = DEFAULT_HALF_LIFE_SECONDS
    k_decayed = decay_salience(killed, now_seconds=one_week)
    w_decayed = decay_salience(witnessed, now_seconds=one_week)
    assert k_decayed > w_decayed


def test_decay_to_zero_long_after():
    m = Memory(
        memory_id="m1", kind=MemoryKind.WITNESSED,
        other_entity_id="alice", initial_salience=50,
        created_at_seconds=0.0,
    )
    # 100x half-life — pretty much gone
    s = decay_salience(
        m, now_seconds=100 * DEFAULT_HALF_LIFE_SECONDS,
    )
    assert s == 0


def test_about_filters_by_other_entity():
    s = EntityMemoryStore(entity_id="curilla")
    s.remember(
        kind=MemoryKind.HELPED, other_entity_id="alice",
        salience=80,
    )
    s.remember(
        kind=MemoryKind.HURT, other_entity_id="bob",
        salience=70,
    )
    s.remember(
        kind=MemoryKind.GIFTED, other_entity_id="alice",
        salience=60,
    )
    about_alice = s.about(other_entity_id="alice")
    assert len(about_alice) == 2
    for m in about_alice:
        assert m.other_entity_id == "alice"


def test_about_ranks_by_salience():
    s = EntityMemoryStore(entity_id="curilla")
    s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="alice",
        salience=20, now_seconds=0.0,
    )
    s.remember(
        kind=MemoryKind.SAVED, other_entity_id="alice",
        salience=90, now_seconds=0.0,
    )
    ranked = s.about(other_entity_id="alice", now_seconds=0.0)
    assert ranked[0].kind == MemoryKind.SAVED


def test_about_top_n_caps_results():
    s = EntityMemoryStore(entity_id="curilla")
    for i in range(10):
        s.remember(
            kind=MemoryKind.HELPED, other_entity_id="alice",
            salience=50 + i,
        )
    top3 = s.about(other_entity_id="alice", top_n=3)
    assert len(top3) == 3


def test_by_kind_filters():
    s = EntityMemoryStore(entity_id="curilla")
    s.remember(kind=MemoryKind.HELPED, other_entity_id="alice")
    s.remember(kind=MemoryKind.HURT, other_entity_id="bob")
    s.remember(kind=MemoryKind.HELPED, other_entity_id="charlie")
    helped = s.by_kind(MemoryKind.HELPED)
    assert len(helped) == 2


def test_since_filters_by_age():
    s = EntityMemoryStore(entity_id="curilla")
    s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="alice",
        now_seconds=0.0,
    )
    s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="bob",
        now_seconds=100.0,
    )
    recent = s.since(now_seconds=120.0, max_age_seconds=50.0)
    ids = {m.other_entity_id for m in recent}
    assert ids == {"bob"}


def test_capacity_drops_oldest():
    s = EntityMemoryStore(entity_id="alice", capacity=3)
    for i in range(5):
        s.remember(
            kind=MemoryKind.WITNESSED, other_entity_id=f"e{i}",
            now_seconds=float(i),
        )
    assert len(s.memories) == 3
    # Oldest two (e0, e1) should be gone
    ids = {m.other_entity_id for m in s.memories}
    assert "e0" not in ids
    assert "e1" not in ids
    assert "e4" in ids


def test_compact_drops_zero_salience():
    s = EntityMemoryStore(entity_id="alice")
    s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="bob",
        salience=10, now_seconds=0.0,
    )
    s.remember(
        kind=MemoryKind.KILLED, other_entity_id="boss",
        salience=100, now_seconds=0.0,
    )
    # ~5 half-lives of game time. WITNESSED (1x HL): 10 * 0.5^5 ≈ 0
    # but KILLED (8x HL): 100 * 0.5^(5/8) ≈ 65 — still strong
    dropped = s.compact(now_seconds=5 * DEFAULT_HALF_LIFE_SECONDS)
    assert dropped >= 1
    survivors = {m.kind for m in s.memories}
    # KILLED has 8x half-life so survives the compaction
    assert MemoryKind.KILLED in survivors


def test_salience_at_returns_decayed_value():
    s = EntityMemoryStore(entity_id="alice")
    m = s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="bob",
        salience=80, now_seconds=0.0,
    )
    val = s.salience_at(memory_id=m.memory_id, now_seconds=0.0)
    assert val == 80
    val_later = s.salience_at(
        memory_id=m.memory_id,
        now_seconds=DEFAULT_HALF_LIFE_SECONDS,
    )
    assert 38 <= val_later <= 42


def test_salience_at_unknown_returns_none():
    s = EntityMemoryStore(entity_id="alice")
    assert s.salience_at(memory_id="ghost", now_seconds=0.0) is None


def test_total_with_counts_memories():
    s = EntityMemoryStore(entity_id="alice")
    s.remember(kind=MemoryKind.HELPED, other_entity_id="bob")
    s.remember(kind=MemoryKind.HURT, other_entity_id="bob")
    s.remember(kind=MemoryKind.HELPED, other_entity_id="charlie")
    assert s.total_with("bob") == 2
    assert s.total_with("dave") == 0


def test_registry_creates_store_lazily():
    reg = MemoryRegistry()
    s = reg.store_for("curilla")
    assert s.entity_id == "curilla"
    assert reg.total_entities() == 1
    # Same store on second call
    s2 = reg.store_for("curilla")
    assert s is s2


def test_registry_remember_passthrough():
    reg = MemoryRegistry()
    m = reg.remember(
        entity_id="curilla", kind=MemoryKind.HELPED,
        other_entity_id="alice", salience=70, now_seconds=0.0,
        details="returned amulet",
    )
    assert m.kind == MemoryKind.HELPED
    assert reg.store_for("curilla").total_with("alice") == 1


def test_full_lifecycle_npc_remembers_player_journey():
    """Curilla goes from neutral, gets saved by alice, is then
    abandoned during a fight, finally pardons alice."""
    reg = MemoryRegistry()
    reg.remember(
        entity_id="curilla", kind=MemoryKind.SAVED,
        other_entity_id="alice", salience=95, now_seconds=0.0,
    )
    reg.remember(
        entity_id="curilla", kind=MemoryKind.ABANDONED,
        other_entity_id="alice", salience=70,
        now_seconds=86400.0,
    )
    reg.remember(
        entity_id="curilla", kind=MemoryKind.PARDONED,
        other_entity_id="alice", salience=80,
        now_seconds=86400.0 * 7,
    )
    s = reg.store_for("curilla")
    about = s.about(
        other_entity_id="alice",
        now_seconds=86400.0 * 7,
    )
    # All three present, SAVED still tops because traumatic decay is slow
    assert len(about) == 3
    assert about[0].kind in (MemoryKind.SAVED, MemoryKind.PARDONED)


def test_full_lifecycle_traumatic_memory_overrides_recent_trivia():
    """A KILLED memory from long ago still beats a fresh
    WITNESSED memory in salience."""
    s = EntityMemoryStore(entity_id="boss")
    s.remember(
        kind=MemoryKind.KILLED, other_entity_id="alice",
        salience=100, now_seconds=0.0,
    )
    s.remember(
        kind=MemoryKind.WITNESSED, other_entity_id="alice",
        salience=70,
        now_seconds=DEFAULT_HALF_LIFE_SECONDS * 2,
    )
    ranked = s.about(
        other_entity_id="alice",
        now_seconds=DEFAULT_HALF_LIFE_SECONDS * 2,
    )
    assert ranked[0].kind == MemoryKind.KILLED
