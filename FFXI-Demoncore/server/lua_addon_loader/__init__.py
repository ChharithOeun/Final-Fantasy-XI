"""Lua addon loader — registry and lifecycle for player addons.

Demoncore is fully menu-driven with tons of LUA addons.
This module is the server-side companion: each addon
declares a manifest (id, name, version, author, hooks),
and the loader maintains a per-player enabled/disabled
set with persistence and conflict resolution.

The actual Lua VM lives client-side; this server module
catalogs what exists, gates per-player enables, and lets
the client query "what hooks are wired for player X?"
so it can dispatch events.

Permission tiers describe what the addon can do:
    READ_ONLY    can read game state, render UI
    HOTBAR       can additionally bind/unbind hotbar slots
    SEND_INPUT   can issue commands as if the player typed
                 them (highest trust)

A signed addon (signature_hash present) can be flagged
as VERIFIED. Unverified addons can still install but
the UI surfaces a "third-party, unverified" warning.

Public surface
--------------
    PermissionTier enum
    AddonManifest dataclass (frozen)
    EnableState enum
    LuaAddonLoader
        .register_addon(manifest) -> bool
        .install_for_player(player_id, addon_id) -> bool
        .uninstall_for_player(player_id, addon_id) -> bool
        .enable(player_id, addon_id) -> bool
        .disable(player_id, addon_id) -> bool
        .is_enabled(player_id, addon_id) -> bool
        .hooks_for_player(player_id, hook_name) -> list[str]
            (returns addon_ids whose enabled manifests
             register that hook)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PermissionTier(str, enum.Enum):
    READ_ONLY = "read_only"
    HOTBAR = "hotbar"
    SEND_INPUT = "send_input"


class EnableState(str, enum.Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclasses.dataclass(frozen=True)
class AddonManifest:
    addon_id: str
    name: str
    version: str
    author: str
    permission: PermissionTier
    hooks: tuple[str, ...]
    signature_hash: str = ""    # "" = unverified


@dataclasses.dataclass
class _PlayerAddonState:
    addon_id: str
    state: EnableState


@dataclasses.dataclass
class LuaAddonLoader:
    _addons: dict[str, AddonManifest] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, addon_id) -> state
    _player_state: dict[tuple[str, str], EnableState] = \
        dataclasses.field(default_factory=dict)

    def register_addon(
        self, *, manifest: AddonManifest,
    ) -> bool:
        if not manifest.addon_id or not manifest.name:
            return False
        if manifest.addon_id in self._addons:
            return False
        if not manifest.hooks:
            # an addon with no hooks is just a background
            # script — fine to allow, but at least one
            # hook makes the design intentional
            return False
        self._addons[manifest.addon_id] = manifest
        return True

    def is_verified(self, *, addon_id: str) -> bool:
        a = self._addons.get(addon_id)
        if a is None:
            return False
        return bool(a.signature_hash)

    def install_for_player(
        self, *, player_id: str, addon_id: str,
    ) -> bool:
        if not player_id or addon_id not in self._addons:
            return False
        key = (player_id, addon_id)
        if key in self._player_state:
            return False
        # default to ENABLED on install — players opt out
        # if they want to keep an addon installed but off
        self._player_state[key] = EnableState.ENABLED
        return True

    def uninstall_for_player(
        self, *, player_id: str, addon_id: str,
    ) -> bool:
        key = (player_id, addon_id)
        if key not in self._player_state:
            return False
        del self._player_state[key]
        return True

    def enable(
        self, *, player_id: str, addon_id: str,
    ) -> bool:
        key = (player_id, addon_id)
        if key not in self._player_state:
            return False
        self._player_state[key] = EnableState.ENABLED
        return True

    def disable(
        self, *, player_id: str, addon_id: str,
    ) -> bool:
        key = (player_id, addon_id)
        if key not in self._player_state:
            return False
        self._player_state[key] = EnableState.DISABLED
        return True

    def is_enabled(
        self, *, player_id: str, addon_id: str,
    ) -> bool:
        key = (player_id, addon_id)
        st = self._player_state.get(key)
        return st == EnableState.ENABLED

    def hooks_for_player(
        self, *, player_id: str, hook_name: str,
    ) -> list[str]:
        out: list[str] = []
        for (pid, aid), state in self._player_state.items():
            if pid != player_id:
                continue
            if state != EnableState.ENABLED:
                continue
            manifest = self._addons.get(aid)
            if manifest is None:
                continue
            if hook_name in manifest.hooks:
                out.append(aid)
        return out

    def installed_for_player(
        self, *, player_id: str,
    ) -> list[str]:
        return [
            aid for (pid, aid) in self._player_state
            if pid == player_id
        ]

    def total_addons_registered(self) -> int:
        return len(self._addons)


__all__ = [
    "PermissionTier", "EnableState", "AddonManifest",
    "LuaAddonLoader",
]
