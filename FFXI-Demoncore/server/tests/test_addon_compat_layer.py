"""Tests for addon_compat_layer."""
from __future__ import annotations

from server.addon_compat_layer import (
    AddonCompatLayer, ApiCall, Platform, default_compat_layer,
)


def test_register_native_happy():
    l = AddonCompatLayer()
    out = l.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
        canonical=ApiCall.CHAT_EMIT,
    )
    assert out is True


def test_register_blank_name_blocked():
    l = AddonCompatLayer()
    out = l.register_native(
        platform=Platform.WINDOWER,
        native_name="", canonical=ApiCall.CHAT_EMIT,
    )
    assert out is False


def test_register_canonical_platform_blocked():
    """Canonical names are intrinsic — no registration needed."""
    l = AddonCompatLayer()
    out = l.register_native(
        platform=Platform.CANONICAL,
        native_name="anything", canonical=ApiCall.CHAT_EMIT,
    )
    assert out is False


def test_register_duplicate_blocked():
    l = AddonCompatLayer()
    l.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
        canonical=ApiCall.CHAT_EMIT,
    )
    out = l.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
        canonical=ApiCall.CHAT_EMIT,
    )
    assert out is False


def test_resolve_windower_native():
    l = default_compat_layer()
    out = l.resolve(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
    )
    assert out == ApiCall.CHAT_EMIT


def test_resolve_ashita_native():
    l = default_compat_layer()
    out = l.resolve(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.AddChatMessage",
    )
    assert out == ApiCall.CHAT_EMIT


def test_resolve_canonical_direct():
    """Canonical layer parses ApiCall name strings directly."""
    l = AddonCompatLayer()
    out = l.resolve(
        platform=Platform.CANONICAL,
        native_name="chat_emit",
    )
    assert out == ApiCall.CHAT_EMIT


def test_resolve_canonical_unknown_returns_none():
    l = AddonCompatLayer()
    out = l.resolve(
        platform=Platform.CANONICAL,
        native_name="ghost_call",
    )
    assert out is None


def test_resolve_unknown_native():
    l = default_compat_layer()
    out = l.resolve(
        platform=Platform.WINDOWER,
        native_name="windower.does_not_exist",
    )
    assert out is None


def test_canonical_signatures_present():
    l = AddonCompatLayer()
    sigs = l.canonical_signatures()
    assert ApiCall.CHAT_EMIT in sigs
    assert sigs[ApiCall.CHAT_EMIT].args == ("color_id", "message")


def test_canonical_signatures_returns_copy():
    l = AddonCompatLayer()
    sigs1 = l.canonical_signatures()
    sigs2 = l.canonical_signatures()
    assert sigs1 is not sigs2


def test_platforms_supporting_chat_emit():
    l = default_compat_layer()
    out = l.platforms_supporting(canonical=ApiCall.CHAT_EMIT)
    # Both Windower and Ashita registered it; canonical always supports
    assert Platform.WINDOWER in out
    assert Platform.ASHITA in out
    assert Platform.CANONICAL in out


def test_platforms_supporting_unmapped():
    l = AddonCompatLayer()
    out = l.platforms_supporting(canonical=ApiCall.CHAT_EMIT)
    # only canonical, no native mappings yet
    assert out == [Platform.CANONICAL]


def test_default_layer_covers_all_eight_canonical():
    l = default_compat_layer()
    for call in ApiCall:
        out = l.platforms_supporting(canonical=call)
        # both windower + ashita should have a native binding
        assert Platform.WINDOWER in out
        assert Platform.ASHITA in out


def test_default_layer_resolution_count():
    l = default_compat_layer()
    # 8 calls × 2 platforms = 16 native bindings
    assert l.total_resolutions() == 16


def test_eight_api_calls():
    assert len(list(ApiCall)) == 8


def test_three_platforms():
    assert len(list(Platform)) == 3


def test_round_trip_windower_to_ashita():
    """Canonical resolution unifies both ecosystems."""
    l = default_compat_layer()
    # A Windower addon's chat call resolves to canonical CHAT_EMIT;
    # an Ashita addon's chat call resolves to the SAME canonical;
    # therefore both addons can share a runtime that only knows
    # canonical names.
    w = l.resolve(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
    )
    a = l.resolve(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.AddChatMessage",
    )
    assert w == a
    assert w == ApiCall.CHAT_EMIT


def test_signatures_have_args_and_return():
    l = AddonCompatLayer()
    sigs = l.canonical_signatures()
    for call, sig in sigs.items():
        assert isinstance(sig.args, tuple)
        assert sig.return_kind in (
            "void", "table", "string", "int", "bool",
        )
