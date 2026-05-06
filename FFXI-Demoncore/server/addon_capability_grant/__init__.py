"""Addon capability grant — fine-grained per-addon permissions.

lua_addon_loader has 3 broad PermissionTiers (READ_ONLY,
HOTBAR, SEND_INPUT). That's the install-time gate. This
module is the runtime gate: a per-addon set of specific
capabilities the player (or NPC owner) explicitly granted.

The reason this matters more once mobs use the addon
ecosystem: a player's gearswap addon should NEVER be
triggered by a hostile mob's event, and a hostile NPC's
"see player buffs" addon should NEVER read inventory.

A capability is a string token like:
    READ_BUFFS        observe a target's buff list
    READ_INVENTORY    observe an entity's pack contents
    SWAP_GEAR         change an entity's equipped set
    QUEUE_COMMAND     enqueue an action on the action_queue
    SEND_CHAT         post a message into chat channels
    READ_PARTY        observe party roster

A grant binds (addon_id, capability) → set of allowed
entity_ids. So gearswap can SWAP_GEAR on alice (the
player who installed it) but cannot SWAP_GEAR on bob.
A hostile mob's behavior addon can READ_BUFFS on alice
(it's a public combat observation) but cannot READ_INVENTORY.

Public surface
--------------
    Capability enum
    GrantKey = (addon_id, capability)
    AddonCapabilityGrant
        .grant(addon_id, capability, entity_id) -> bool
        .revoke(addon_id, capability, entity_id) -> bool
        .can(addon_id, capability, entity_id) -> bool
        .grants_for(addon_id, capability) -> list[str]
        .revoke_all_for(entity_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum


class Capability(str, enum.Enum):
    READ_BUFFS = "read_buffs"
    READ_INVENTORY = "read_inventory"
    READ_PARTY = "read_party"
    READ_CHAT = "read_chat"
    SWAP_GEAR = "swap_gear"
    QUEUE_COMMAND = "queue_command"
    SEND_CHAT = "send_chat"
    BIND_HOTBAR = "bind_hotbar"


@dataclasses.dataclass
class AddonCapabilityGrant:
    # (addon_id, capability) → set of entity_ids
    _grants: dict[tuple[str, Capability], set[str]] = \
        dataclasses.field(default_factory=dict)

    def grant(
        self, *, addon_id: str, capability: Capability,
        entity_id: str,
    ) -> bool:
        if not addon_id or not entity_id:
            return False
        key = (addon_id, capability)
        s = self._grants.setdefault(key, set())
        if entity_id in s:
            return False
        s.add(entity_id)
        return True

    def revoke(
        self, *, addon_id: str, capability: Capability,
        entity_id: str,
    ) -> bool:
        key = (addon_id, capability)
        s = self._grants.get(key)
        if s is None or entity_id not in s:
            return False
        s.discard(entity_id)
        if not s:
            del self._grants[key]
        return True

    def can(
        self, *, addon_id: str, capability: Capability,
        entity_id: str,
    ) -> bool:
        key = (addon_id, capability)
        s = self._grants.get(key)
        if s is None:
            return False
        return entity_id in s

    def grants_for(
        self, *, addon_id: str, capability: Capability,
    ) -> list[str]:
        key = (addon_id, capability)
        s = self._grants.get(key, set())
        return sorted(s)

    def revoke_all_for(self, *, entity_id: str) -> int:
        """Remove this entity from every grant.

        Returns the count of (addon, capability) pairs the
        entity was removed from. Used when an entity is
        deleted or banned — sweep all addons clean.
        """
        count = 0
        empty_keys: list[tuple[str, Capability]] = []
        for key, s in self._grants.items():
            if entity_id in s:
                s.discard(entity_id)
                count += 1
                if not s:
                    empty_keys.append(key)
        for k in empty_keys:
            del self._grants[k]
        return count

    def total_grants(self) -> int:
        return sum(len(v) for v in self._grants.values())


__all__ = [
    "Capability", "AddonCapabilityGrant",
]
