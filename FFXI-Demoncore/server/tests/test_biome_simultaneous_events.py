"""Tests for biome simultaneous events."""
from __future__ import annotations

from server.biome_simultaneous_events import (
    BiomeSimultaneousEvents,
    DECAY_AFTER_SECONDS,
    EventBiome,
    EventFacet,
    EventKind,
)


def _seed_chain(b: BiomeSimultaneousEvents):
    return b.register_chain(
        chain_id="bastok_siege",
        primary_biome=EventBiome.SURFACE,
        primary_kind=EventKind.SIEGE,
        facets=[
            EventFacet(
                biome=EventBiome.DEEP,
                kind=EventKind.SUB_INCURSION,
            ),
            EventFacet(
                biome=EventBiome.SKY,
                kind=EventKind.AERIAL_RAID,
            ),
        ],
        duration_seconds=1800,
    )


def test_register_chain_happy():
    b = BiomeSimultaneousEvents()
    assert _seed_chain(b) is True


def test_register_blank_id():
    b = BiomeSimultaneousEvents()
    assert b.register_chain(
        chain_id="", primary_biome=EventBiome.SURFACE,
        primary_kind=EventKind.SIEGE,
        facets=[], duration_seconds=60,
    ) is False


def test_register_zero_duration():
    b = BiomeSimultaneousEvents()
    assert b.register_chain(
        chain_id="c1", primary_biome=EventBiome.SURFACE,
        primary_kind=EventKind.SIEGE,
        facets=[], duration_seconds=0,
    ) is False


def test_register_double_blocked():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    assert _seed_chain(b) is False


def test_start_happy():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    assert b.start(chain_id="bastok_siege", now_seconds=0) is True


def test_start_unknown():
    b = BiomeSimultaneousEvents()
    assert b.start(chain_id="ghost", now_seconds=0) is False


def test_start_double_blocked():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    assert b.start(chain_id="bastok_siege", now_seconds=10) is False


def test_is_active_after_start():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    assert b.is_active(chain_id="bastok_siege", now_seconds=100) is True


def test_is_active_after_duration():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    assert b.is_active(
        chain_id="bastok_siege", now_seconds=2000,
    ) is False


def test_contribute_happy():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    ok = b.contribute(
        chain_id="bastok_siege", player_id="p1",
        biome=EventBiome.SURFACE, points=50, now_seconds=10,
    )
    assert ok is True
    assert b.contributions(chain_id="bastok_siege")["p1"] == 50


def test_contribute_facet_biome_works():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    ok = b.contribute(
        chain_id="bastok_siege", player_id="p1",
        biome=EventBiome.DEEP, points=50, now_seconds=10,
    )
    assert ok is True


def test_contribute_unknown_biome_blocked():
    """If a chain doesn't include SKY, SKY contributions don't count."""
    b = BiomeSimultaneousEvents()
    b.register_chain(
        chain_id="surface_only",
        primary_biome=EventBiome.SURFACE,
        primary_kind=EventKind.SIEGE,
        facets=[],
        duration_seconds=600,
    )
    b.start(chain_id="surface_only", now_seconds=0)
    ok = b.contribute(
        chain_id="surface_only", player_id="p1",
        biome=EventBiome.SKY, points=50, now_seconds=10,
    )
    assert ok is False


def test_contribute_after_duration_blocked():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    ok = b.contribute(
        chain_id="bastok_siege", player_id="p1",
        biome=EventBiome.SURFACE, points=50, now_seconds=2000,
    )
    assert ok is False


def test_contribute_decay_late():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    # contribute well past decay window: 60 + 30 = 90 sec into event
    b.contribute(
        chain_id="bastok_siege", player_id="late",
        biome=EventBiome.SURFACE, points=100,
        now_seconds=DECAY_AFTER_SECONDS + 30,
    )
    early_b = BiomeSimultaneousEvents()
    _seed_chain(early_b)
    early_b.start(chain_id="bastok_siege", now_seconds=0)
    early_b.contribute(
        chain_id="bastok_siege", player_id="early",
        biome=EventBiome.SURFACE, points=100, now_seconds=10,
    )
    late_pts = b.contributions(chain_id="bastok_siege")["late"]
    early_pts = early_b.contributions(chain_id="bastok_siege")["early"]
    assert late_pts < early_pts


def test_contribute_not_started_blocked():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    ok = b.contribute(
        chain_id="bastok_siege", player_id="p1",
        biome=EventBiome.SURFACE, points=50, now_seconds=10,
    )
    assert ok is False


def test_end_blocks_further_contributions():
    b = BiomeSimultaneousEvents()
    _seed_chain(b)
    b.start(chain_id="bastok_siege", now_seconds=0)
    b.end(chain_id="bastok_siege", now_seconds=100)
    ok = b.contribute(
        chain_id="bastok_siege", player_id="p1",
        biome=EventBiome.SURFACE, points=10, now_seconds=110,
    )
    assert ok is False
    assert b.is_active(
        chain_id="bastok_siege", now_seconds=110,
    ) is False


def test_end_unknown():
    b = BiomeSimultaneousEvents()
    assert b.end(chain_id="ghost", now_seconds=0) is False


def test_contributions_unknown():
    b = BiomeSimultaneousEvents()
    assert b.contributions(chain_id="ghost") == {}
