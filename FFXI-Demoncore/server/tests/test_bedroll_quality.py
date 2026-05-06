"""Tests for bedroll_quality."""
from __future__ import annotations

from server.bedroll_quality import BedrollRegistry, BedrollTier


def test_craft_happy():
    r = BedrollRegistry()
    ok = r.craft(
        bedroll_id="b1", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    assert ok is True
    assert r.uses_remaining(bedroll_id="b1") == 10


def test_blank_id_blocked():
    r = BedrollRegistry()
    out = r.craft(
        bedroll_id="", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    assert out is False


def test_blank_owner_blocked():
    r = BedrollRegistry()
    out = r.craft(
        bedroll_id="b", owner_id="",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    assert out is False


def test_duplicate_blocked():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    out = r.craft(
        bedroll_id="b", owner_id="bob",
        tier=BedrollTier.FUR, crafted_at=20,
    )
    assert out is False


def test_quality_temperate_baseline():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    # WOOL prefers temperate → 55 + 10
    out = r.effective_quality(bedroll_id="b", climate="temperate")
    assert out == 65


def test_quality_climate_match_bonus():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.FUR, crafted_at=10,
    )
    # FUR + arctic → 80 + 10
    out = r.effective_quality(bedroll_id="b", climate="arctic")
    assert out == 90


def test_quality_climate_poor_penalty():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.FUR, crafted_at=10,
    )
    # FUR + desert → 80 - 20
    out = r.effective_quality(bedroll_id="b", climate="desert")
    assert out == 60


def test_quality_climate_neutral():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    # STRAW + rainforest (neither preferred nor poor) → 30
    out = r.effective_quality(bedroll_id="b", climate="rainforest")
    assert out == 30


def test_quality_caps_at_100():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.FUR, crafted_at=10,
    )
    # FUR is 80, +10 = 90 (within cap, just sanity check)
    out = r.effective_quality(bedroll_id="b", climate="ARCTIC")
    assert out == 90  # case-insensitive


def test_quality_floor_at_zero():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    # STRAW base 30, arctic -20 = 10 (still positive)
    out = r.effective_quality(bedroll_id="b", climate="arctic")
    assert out == 10


def test_quality_unknown_bedroll_zero():
    r = BedrollRegistry()
    assert r.effective_quality(
        bedroll_id="ghost", climate="temperate",
    ) == 0


def test_use_decrements_uses():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    ok = r.use(bedroll_id="b")
    assert ok is True
    assert r.uses_remaining(bedroll_id="b") == 2


def test_use_exhausts_after_max():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    for _ in range(3):
        r.use(bedroll_id="b")
    out = r.use(bedroll_id="b")
    assert out is False


def test_use_unknown():
    r = BedrollRegistry()
    out = r.use(bedroll_id="ghost")
    assert out is False


def test_exhausted_bedroll_zero_quality():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.FUR, crafted_at=10,
    )
    for _ in range(20):
        r.use(bedroll_id="b")
    out = r.effective_quality(bedroll_id="b", climate="arctic")
    assert out == 0


def test_repair_restores_uses():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    for _ in range(5):
        r.use(bedroll_id="b")
    out = r.repair(bedroll_id="b", units=3)
    assert out == 8


def test_repair_caps_at_max():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    r.use(bedroll_id="b")
    out = r.repair(bedroll_id="b", units=999)
    assert out == 10


def test_repair_zero_units_no_change():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.WOOL, crafted_at=10,
    )
    r.use(bedroll_id="b")
    out = r.repair(bedroll_id="b", units=0)
    assert out == 9


def test_repair_unknown():
    r = BedrollRegistry()
    out = r.repair(bedroll_id="ghost", units=5)
    assert out == 0


def test_profile_for():
    r = BedrollRegistry()
    p = r.profile_for(tier=BedrollTier.DOWN)
    assert p.base_quality_pct == 70
    assert "temperate" in p.preferred_climates


def test_total_bedrolls():
    r = BedrollRegistry()
    r.craft(
        bedroll_id="a", owner_id="alice",
        tier=BedrollTier.STRAW, crafted_at=10,
    )
    r.craft(
        bedroll_id="b", owner_id="alice",
        tier=BedrollTier.FUR, crafted_at=20,
    )
    assert r.total_bedrolls() == 2


def test_four_tiers():
    assert len(list(BedrollTier)) == 4
