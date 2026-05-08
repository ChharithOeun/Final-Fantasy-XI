"""Tests for guild_legacy."""
from __future__ import annotations

from server.guild_legacy import (
    GuildLegacySystem, DisbandCause,
)


def _seal(s, **overrides):
    args = dict(
        ls_id="ls_alpha", name="Stoneforge",
        pearl_color="emerald", founded_day=10,
        sealed_day=900, founder_id="bob",
        final_leader_id="cara",
        member_count_at_seal=42,
        notable_honors=["First Tiamat",
                        "Cleared Sky"],
        cause=DisbandCause.VOLUNTARY,
    )
    args.update(overrides)
    return s.seal(**args)


def test_seal_happy():
    s = GuildLegacySystem()
    assert _seal(s) is not None


def test_seal_blank_ls():
    s = GuildLegacySystem()
    assert _seal(s, ls_id="") is None


def test_seal_blank_name():
    s = GuildLegacySystem()
    assert _seal(s, name="") is None


def test_seal_blank_pearl():
    s = GuildLegacySystem()
    assert _seal(s, pearl_color="") is None


def test_seal_negative_founded():
    s = GuildLegacySystem()
    assert _seal(s, founded_day=-1) is None


def test_seal_sealed_before_founded():
    s = GuildLegacySystem()
    assert _seal(s, founded_day=100, sealed_day=50) is None


def test_seal_negative_members():
    s = GuildLegacySystem()
    assert _seal(s, member_count_at_seal=-1) is None


def test_seal_dup_ls_blocked():
    s = GuildLegacySystem()
    _seal(s)
    assert _seal(s) is None


def test_name_is_sealed_after_seal():
    s = GuildLegacySystem()
    _seal(s, name="Stoneforge")
    assert s.name_is_sealed(name="Stoneforge") is True
    # Case-insensitive
    assert s.name_is_sealed(name="STONEFORGE") is True


def test_name_unsealed():
    s = GuildLegacySystem()
    assert s.name_is_sealed(name="Phoenix") is False


def test_legacy_for_ls():
    s = GuildLegacySystem()
    lid = _seal(s, ls_id="ls_alpha")
    rec = s.legacy_for_ls(ls_id="ls_alpha")
    assert rec is not None
    assert rec.legacy_id == lid


def test_legacy_for_ls_unknown():
    s = GuildLegacySystem()
    assert s.legacy_for_ls(ls_id="ghost") is None


def test_legacy_unknown():
    s = GuildLegacySystem()
    assert s.legacy(legacy_id="ghost") is None


def test_honor_score():
    s = GuildLegacySystem()
    lid = _seal(s, notable_honors=["a", "b", "c"])
    rec = s.legacy(legacy_id=lid)
    assert rec.honor_score == 3


def test_top_legacies_orders_by_honor():
    s = GuildLegacySystem()
    _seal(s, ls_id="ls_a", name="Alpha",
          notable_honors=["x"])
    _seal(s, ls_id="ls_b", name="Beta",
          notable_honors=["x", "y", "z"])
    _seal(s, ls_id="ls_c", name="Gamma",
          notable_honors=["x", "y"])
    out = s.top_legacies(limit=10)
    names = [r.name for r in out]
    assert names == ["Beta", "Gamma", "Alpha"]


def test_top_legacies_zero_limit():
    s = GuildLegacySystem()
    _seal(s)
    assert s.top_legacies(limit=0) == []


def test_all_legacies():
    s = GuildLegacySystem()
    _seal(s, ls_id="ls_a", name="Alpha")
    _seal(s, ls_id="ls_b", name="Beta")
    assert len(s.all_legacies()) == 2


def test_outlawed_cause_preserved():
    s = GuildLegacySystem()
    lid = _seal(
        s, cause=DisbandCause.OUTLAWED_DISSOLVED,
    )
    assert s.legacy(legacy_id=lid).cause == (
        DisbandCause.OUTLAWED_DISSOLVED
    )


def test_enum_count():
    assert len(list(DisbandCause)) == 4
