"""Tests for addon_capability_grant."""
from __future__ import annotations

from server.addon_capability_grant import (
    AddonCapabilityGrant, Capability,
)


def test_grant_happy():
    g = AddonCapabilityGrant()
    ok = g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert ok is True
    assert g.can(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is True


def test_grant_blank_addon_blocked():
    g = AddonCapabilityGrant()
    out = g.grant(
        addon_id="", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert out is False


def test_grant_blank_entity_blocked():
    g = AddonCapabilityGrant()
    out = g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="",
    )
    assert out is False


def test_grant_duplicate_blocked():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    out = g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert out is False


def test_can_default_false():
    g = AddonCapabilityGrant()
    assert g.can(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is False


def test_revoke_happy():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    out = g.revoke(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert out is True
    assert g.can(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is False


def test_revoke_unknown_grant():
    g = AddonCapabilityGrant()
    out = g.revoke(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert out is False


def test_separate_entities_isolated():
    """Gearswap on alice does NOT mean gearswap on bob."""
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert g.can(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="bob",
    ) is False


def test_separate_capabilities_isolated():
    """SWAP_GEAR doesn't imply READ_INVENTORY."""
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert g.can(
        addon_id="gearswap",
        capability=Capability.READ_INVENTORY,
        entity_id="alice",
    ) is False


def test_separate_addons_isolated():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="gearswap", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert g.can(
        addon_id="other_addon", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is False


def test_npc_grant_separate_from_player():
    """Mob's behavior addon can READ_BUFFS on alice, but
    player's gearswap addon's grants are independent."""
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="boss_ai_observe",
        capability=Capability.READ_BUFFS,
        entity_id="alice",
    )
    # Player's gearswap on alice should NOT inherit
    assert g.can(
        addon_id="gearswap",
        capability=Capability.READ_BUFFS,
        entity_id="alice",
    ) is False


def test_grants_for_lists():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="boss_ai_observe",
        capability=Capability.READ_BUFFS,
        entity_id="alice",
    )
    g.grant(
        addon_id="boss_ai_observe",
        capability=Capability.READ_BUFFS,
        entity_id="bob",
    )
    out = g.grants_for(
        addon_id="boss_ai_observe",
        capability=Capability.READ_BUFFS,
    )
    assert out == ["alice", "bob"]


def test_grants_for_unknown_empty():
    g = AddonCapabilityGrant()
    out = g.grants_for(
        addon_id="x", capability=Capability.READ_BUFFS,
    )
    assert out == []


def test_revoke_all_for_entity():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="a", capability=Capability.READ_BUFFS,
        entity_id="alice",
    )
    g.grant(
        addon_id="b", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    g.grant(
        addon_id="a", capability=Capability.READ_BUFFS,
        entity_id="bob",
    )
    out = g.revoke_all_for(entity_id="alice")
    assert out == 2
    # bob's grants survive
    assert g.can(
        addon_id="a", capability=Capability.READ_BUFFS,
        entity_id="bob",
    ) is True


def test_revoke_all_for_unknown_entity():
    g = AddonCapabilityGrant()
    out = g.revoke_all_for(entity_id="ghost")
    assert out == 0


def test_revoke_emptying_set_cleans_key():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="x", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    g.revoke(
        addon_id="x", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    # Re-granting works
    out = g.grant(
        addon_id="x", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert out is True


def test_eight_capabilities():
    assert len(list(Capability)) == 8


def test_total_grants():
    g = AddonCapabilityGrant()
    g.grant(
        addon_id="a", capability=Capability.READ_BUFFS,
        entity_id="alice",
    )
    g.grant(
        addon_id="a", capability=Capability.READ_BUFFS,
        entity_id="bob",
    )
    g.grant(
        addon_id="b", capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    assert g.total_grants() == 3


def test_canonical_safety_pattern():
    """The motivating example from the design notes:
    a player's gearswap can SWAP_GEAR on alice;
    a hostile mob's behavior addon can only READ_BUFFS
    on alice (no SWAP_GEAR, no READ_INVENTORY)."""
    g = AddonCapabilityGrant()
    # Player installs gearswap on themselves.
    g.grant(
        addon_id="gearswap",
        capability=Capability.SWAP_GEAR,
        entity_id="alice",
    )
    g.grant(
        addon_id="gearswap",
        capability=Capability.READ_INVENTORY,
        entity_id="alice",
    )
    # Hostile NM AI gets a public combat observation grant.
    g.grant(
        addon_id="boss_ai_observer",
        capability=Capability.READ_BUFFS,
        entity_id="alice",
    )
    # Player's gear is theirs:
    assert g.can(
        addon_id="gearswap",
        capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is True
    # The boss CANNOT swap the player's gear:
    assert g.can(
        addon_id="boss_ai_observer",
        capability=Capability.SWAP_GEAR,
        entity_id="alice",
    ) is False
    # The boss CANNOT read the player's inventory:
    assert g.can(
        addon_id="boss_ai_observer",
        capability=Capability.READ_INVENTORY,
        entity_id="alice",
    ) is False
    # But CAN watch their public buffs:
    assert g.can(
        addon_id="boss_ai_observer",
        capability=Capability.READ_BUFFS,
        entity_id="alice",
    ) is True
