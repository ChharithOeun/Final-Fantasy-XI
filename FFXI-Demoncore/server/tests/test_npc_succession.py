"""Tests for NPC succession registry."""
from __future__ import annotations

from server.npc_succession import (
    DEFAULT_INHERIT,
    HeirCandidate,
    InheritKind,
    NPCSuccessionRegistry,
    SuccessionPlan,
)


def _smith_plan() -> SuccessionPlan:
    return SuccessionPlan(
        role_id="bastok_master_smith",
        role_label="Bastok Master Smith",
        incumbent_npc_id="cooper",
        faction_id="bastok",
        heir_order=(
            HeirCandidate(
                npc_id="anvil_apprentice",
                faction_id="bastok",
                relationship_to_predecessor="apprentice",
            ),
            HeirCandidate(
                npc_id="hammer_son",
                faction_id="bastok",
                relationship_to_predecessor="son",
            ),
        ),
    )


def test_register_and_role_holder():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    assert reg.role_holder("bastok_master_smith") == "cooper"
    assert reg.total_roles() == 1


def test_history_starts_with_incumbent():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    history = reg.history("bastok_master_smith")
    assert history == ("cooper",)


def test_declare_dead_unknown_npc_returns_false():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    assert not reg.declare_dead(npc_id="ghost")


def test_declare_dead_known_npc():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    assert reg.declare_dead(npc_id="cooper", now_seconds=0.0)
    # Role no longer has a live holder
    assert reg.role_holder("bastok_master_smith") is None


def test_recover_heir_promotes_apprentice():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    reg.declare_dead(npc_id="cooper")
    res = reg.recover_heir(role_id="bastok_master_smith")
    assert res.accepted
    assert res.new_holder_id == "anvil_apprentice"
    assert reg.role_holder(
        "bastok_master_smith",
    ) == "anvil_apprentice"


def test_recover_heir_unknown_role():
    reg = NPCSuccessionRegistry()
    res = reg.recover_heir(role_id="ghost")
    assert not res.accepted


def test_recover_heir_incumbent_still_alive():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    res = reg.recover_heir(role_id="bastok_master_smith")
    assert not res.accepted
    assert "alive" in res.reason


def test_recover_heir_skips_dead_heir():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    # Apprentice ALSO dies before incumbent
    reg.declare_dead(npc_id="anvil_apprentice")
    reg.declare_dead(npc_id="cooper")
    res = reg.recover_heir(role_id="bastok_master_smith")
    assert res.accepted
    assert res.new_holder_id == "hammer_son"


def test_recover_heir_skips_wrong_faction():
    plan = SuccessionPlan(
        role_id="role_x", role_label="X",
        incumbent_npc_id="incumbent",
        faction_id="bastok",
        heir_order=(
            HeirCandidate(
                npc_id="foreigner",
                faction_id="windurst",
            ),
            HeirCandidate(
                npc_id="local",
                faction_id="bastok",
            ),
        ),
    )
    reg = NPCSuccessionRegistry()
    reg.register_plan(plan)
    reg.declare_dead(npc_id="incumbent")
    res = reg.recover_heir(role_id="role_x")
    assert res.accepted
    assert res.new_holder_id == "local"


def test_no_eligible_heirs_returns_failure():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    reg.declare_dead(npc_id="cooper")
    reg.declare_dead(npc_id="anvil_apprentice")
    reg.declare_dead(npc_id="hammer_son")
    res = reg.recover_heir(role_id="bastok_master_smith")
    assert not res.accepted
    assert "no eligible" in res.reason


def test_inherits_default_set():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    reg.declare_dead(npc_id="cooper")
    res = reg.recover_heir(role_id="bastok_master_smith")
    assert res.inherited == DEFAULT_INHERIT


def test_custom_inherits_subset():
    plan = SuccessionPlan(
        role_id="role_x", role_label="X",
        incumbent_npc_id="incumbent",
        faction_id="bastok",
        heir_order=(
            HeirCandidate(
                npc_id="heir_1", faction_id="bastok",
            ),
        ),
        inherits=frozenset({InheritKind.SHOP_INVENTORY}),
    )
    reg = NPCSuccessionRegistry()
    reg.register_plan(plan)
    reg.declare_dead(npc_id="incumbent")
    res = reg.recover_heir(role_id="role_x")
    assert res.inherited == frozenset({
        InheritKind.SHOP_INVENTORY,
    })


def test_history_grows_with_succession():
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    reg.declare_dead(npc_id="cooper")
    reg.recover_heir(role_id="bastok_master_smith")
    reg.declare_dead(npc_id="anvil_apprentice")
    reg.recover_heir(role_id="bastok_master_smith")
    history = reg.history("bastok_master_smith")
    assert history == (
        "cooper", "anvil_apprentice", "hammer_son",
    )


def test_full_lifecycle_dynasty_collapse():
    """Cooper dies, apprentice rises. Then apprentice dies,
    son rises. Then son dies — no eligible heir remains."""
    reg = NPCSuccessionRegistry()
    reg.register_plan(_smith_plan())
    # Death 1
    reg.declare_dead(npc_id="cooper")
    a = reg.recover_heir(role_id="bastok_master_smith")
    assert a.new_holder_id == "anvil_apprentice"
    # Death 2
    reg.declare_dead(npc_id="anvil_apprentice")
    b = reg.recover_heir(role_id="bastok_master_smith")
    assert b.new_holder_id == "hammer_son"
    # Death 3 — no heirs left
    reg.declare_dead(npc_id="hammer_son")
    c = reg.recover_heir(role_id="bastok_master_smith")
    assert not c.accepted
    # Role becomes vacant
    assert reg.role_holder(
        "bastok_master_smith",
    ) is None
