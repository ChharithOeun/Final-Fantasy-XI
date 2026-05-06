"""Tests for lua_addon_loader."""
from __future__ import annotations

from server.lua_addon_loader import (
    AddonManifest, EnableState, LuaAddonLoader, PermissionTier,
)


def _manifest(addon_id="dpsmeter", hooks=("on_damage",), signature=""):
    return AddonManifest(
        addon_id=addon_id, name="DPSMeter",
        version="1.0", author="alice",
        permission=PermissionTier.READ_ONLY,
        hooks=hooks, signature_hash=signature,
    )


def test_register_happy():
    l = LuaAddonLoader()
    assert l.register_addon(manifest=_manifest()) is True


def test_register_blank_id_blocked():
    l = LuaAddonLoader()
    out = l.register_addon(manifest=_manifest(addon_id=""))
    assert out is False


def test_register_no_hooks_blocked():
    l = LuaAddonLoader()
    out = l.register_addon(manifest=_manifest(hooks=()))
    assert out is False


def test_register_duplicate_blocked():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    out = l.register_addon(manifest=_manifest())
    assert out is False


def test_is_verified_unsigned():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(signature=""))
    assert l.is_verified(addon_id="dpsmeter") is False


def test_is_verified_signed():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(signature="abc123"))
    assert l.is_verified(addon_id="dpsmeter") is True


def test_is_verified_unknown():
    l = LuaAddonLoader()
    assert l.is_verified(addon_id="ghost") is False


def test_install_happy():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    out = l.install_for_player(
        player_id="alice", addon_id="dpsmeter",
    )
    assert out is True
    assert l.is_enabled(
        player_id="alice", addon_id="dpsmeter",
    ) is True


def test_install_unknown_addon():
    l = LuaAddonLoader()
    out = l.install_for_player(
        player_id="alice", addon_id="ghost",
    )
    assert out is False


def test_install_blank_player():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    out = l.install_for_player(
        player_id="", addon_id="dpsmeter",
    )
    assert out is False


def test_install_duplicate_blocked():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    l.install_for_player(
        player_id="alice", addon_id="dpsmeter",
    )
    out = l.install_for_player(
        player_id="alice", addon_id="dpsmeter",
    )
    assert out is False


def test_uninstall_happy():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    l.install_for_player(player_id="alice", addon_id="dpsmeter")
    out = l.uninstall_for_player(
        player_id="alice", addon_id="dpsmeter",
    )
    assert out is True
    assert l.is_enabled(
        player_id="alice", addon_id="dpsmeter",
    ) is False


def test_uninstall_unknown():
    l = LuaAddonLoader()
    out = l.uninstall_for_player(
        player_id="alice", addon_id="ghost",
    )
    assert out is False


def test_disable_then_reenable():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest())
    l.install_for_player(player_id="alice", addon_id="dpsmeter")
    l.disable(player_id="alice", addon_id="dpsmeter")
    assert l.is_enabled(
        player_id="alice", addon_id="dpsmeter",
    ) is False
    l.enable(player_id="alice", addon_id="dpsmeter")
    assert l.is_enabled(
        player_id="alice", addon_id="dpsmeter",
    ) is True


def test_disable_unknown():
    l = LuaAddonLoader()
    out = l.disable(player_id="alice", addon_id="ghost")
    assert out is False


def test_enable_unknown():
    l = LuaAddonLoader()
    out = l.enable(player_id="alice", addon_id="ghost")
    assert out is False


def test_hooks_for_player_filters_by_hook():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(
        addon_id="dps", hooks=("on_damage",),
    ))
    l.register_addon(manifest=_manifest(
        addon_id="ts", hooks=("on_target_change",),
    ))
    l.install_for_player(player_id="alice", addon_id="dps")
    l.install_for_player(player_id="alice", addon_id="ts")
    out = l.hooks_for_player(
        player_id="alice", hook_name="on_damage",
    )
    assert out == ["dps"]


def test_hooks_for_player_filters_by_enabled():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(hooks=("on_damage",)))
    l.install_for_player(player_id="alice", addon_id="dpsmeter")
    l.disable(player_id="alice", addon_id="dpsmeter")
    out = l.hooks_for_player(
        player_id="alice", hook_name="on_damage",
    )
    assert out == []


def test_hooks_for_player_other_player_unaffected():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(hooks=("on_damage",)))
    l.install_for_player(player_id="alice", addon_id="dpsmeter")
    out = l.hooks_for_player(
        player_id="bob", hook_name="on_damage",
    )
    assert out == []


def test_installed_for_player_lists():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(addon_id="a"))
    l.register_addon(manifest=_manifest(
        addon_id="b", hooks=("on_target_change",),
    ))
    l.install_for_player(player_id="alice", addon_id="a")
    l.install_for_player(player_id="alice", addon_id="b")
    out = l.installed_for_player(player_id="alice")
    assert sorted(out) == ["a", "b"]


def test_three_permission_tiers():
    assert len(list(PermissionTier)) == 3


def test_three_enable_states():
    assert len(list(EnableState)) == 3


def test_total_addons_registered():
    l = LuaAddonLoader()
    l.register_addon(manifest=_manifest(addon_id="a"))
    l.register_addon(manifest=_manifest(
        addon_id="b", hooks=("on_target_change",),
    ))
    assert l.total_addons_registered() == 2
