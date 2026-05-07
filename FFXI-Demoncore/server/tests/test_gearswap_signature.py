"""Tests for gearswap_signature."""
from __future__ import annotations

from server.gearswap_signature import (
    AccentColor, GearswapSignature, Glyph,
)


def test_set_signature_initial():
    s = GearswapSignature()
    out = s.set_signature(
        author_id="chharith", motto="speed kills",
        glyph=Glyph.SWORD, accent_color=AccentColor.CRIMSON,
        now=1000,
    )
    assert out is True


def test_set_signature_blank_author_blocked():
    s = GearswapSignature()
    assert s.set_signature(
        author_id="", motto="x",
        glyph=Glyph.SWORD, accent_color=AccentColor.CRIMSON,
        now=1000,
    ) is False


def test_set_signature_blank_motto_allowed():
    """Empty motto is fine — author chose minimalism."""
    s = GearswapSignature()
    out = s.set_signature(
        author_id="chharith", motto="",
        glyph=Glyph.NONE, accent_color=AccentColor.SLATE,
        now=1000,
    )
    assert out is True


def test_set_signature_motto_strips_whitespace():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="   trimmed   ",
        glyph=Glyph.NONE, accent_color=AccentColor.SLATE,
        now=1000,
    )
    sig = s.get_signature(author_id="chharith")
    assert sig.motto == "trimmed"


def test_set_signature_motto_too_long_blocked():
    s = GearswapSignature()
    out = s.set_signature(
        author_id="chharith", motto="x" * 61,
        glyph=Glyph.NONE, accent_color=AccentColor.SLATE,
        now=1000,
    )
    assert out is False


def test_set_signature_at_motto_max_allowed():
    s = GearswapSignature()
    out = s.set_signature(
        author_id="chharith", motto="x" * 60,
        glyph=Glyph.NONE, accent_color=AccentColor.SLATE,
        now=1000,
    )
    assert out is True


def test_can_edit_when_no_signature():
    s = GearswapSignature()
    assert s.can_edit(
        author_id="chharith", now=1000,
    ) is True


def test_can_edit_blocked_within_cooldown():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="m",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    assert s.can_edit(
        author_id="chharith", now=1000 + 3600,
    ) is False


def test_can_edit_after_cooldown():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="m",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    assert s.can_edit(
        author_id="chharith", now=1000 + 86400,
    ) is True


def test_set_signature_blocked_within_cooldown():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="first",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    out = s.set_signature(
        author_id="chharith", motto="second",
        glyph=Glyph.MOON, accent_color=AccentColor.SAPPHIRE,
        now=1000 + 60,
    )
    assert out is False
    sig = s.get_signature(author_id="chharith")
    assert sig.motto == "first"


def test_set_signature_after_cooldown_changes():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="first",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    s.set_signature(
        author_id="chharith", motto="second",
        glyph=Glyph.MOON, accent_color=AccentColor.SAPPHIRE,
        now=1000 + 86400 + 1,
    )
    sig = s.get_signature(author_id="chharith")
    assert sig.motto == "second"
    assert sig.glyph == Glyph.MOON


def test_seconds_until_can_edit_no_sig_zero():
    s = GearswapSignature()
    assert s.seconds_until_can_edit(
        author_id="chharith", now=1000,
    ) == 0


def test_seconds_until_can_edit_after_cooldown_zero():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="m",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    assert s.seconds_until_can_edit(
        author_id="chharith", now=1000 + 86400,
    ) == 0


def test_seconds_until_can_edit_within_cooldown():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="m",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    out = s.seconds_until_can_edit(
        author_id="chharith", now=1000 + 3600,
    )
    assert out == 86400 - 3600


def test_get_signature_unknown_none():
    s = GearswapSignature()
    assert s.get_signature(author_id="ghost") is None


def test_get_signature_returns_full_record():
    s = GearswapSignature()
    s.set_signature(
        author_id="chharith", motto="speed kills",
        glyph=Glyph.SWORD, accent_color=AccentColor.CRIMSON,
        now=1000,
    )
    sig = s.get_signature(author_id="chharith")
    assert sig.author_id == "chharith"
    assert sig.glyph == Glyph.SWORD
    assert sig.accent_color == AccentColor.CRIMSON
    assert sig.last_edited_at == 1000


def test_total_signatures():
    s = GearswapSignature()
    s.set_signature(
        author_id="a", motto="m1",
        glyph=Glyph.STAR, accent_color=AccentColor.AMBER,
        now=1000,
    )
    s.set_signature(
        author_id="b", motto="m2",
        glyph=Glyph.MOON, accent_color=AccentColor.SAPPHIRE,
        now=1000,
    )
    assert s.total_signatures() == 2


def test_sixteen_glyphs():
    assert GearswapSignature.glyph_count() == 16


def test_ten_accent_colors():
    assert GearswapSignature.color_count() == 10
