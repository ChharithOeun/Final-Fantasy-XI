"""Tests for voice_role_registry."""
from __future__ import annotations

import pytest

from server.voice_role_registry import (
    Archetype, BUILTIN_ROLES, Provisioning, ProvisionKind,
    RateCard, RoleSpec, VoiceRole, VoiceRoleRegistry,
)


def _spec() -> RoleSpec:
    return RoleSpec(
        pitch_hz_target=180.0, accent="test", vibe="test",
        age_range=(20, 30), gender="m",
        language_primary="en",
    )


def _role(role_id: str = "test_role") -> VoiceRole:
    return VoiceRole(
        role_id=role_id, character_name="Tester",
        archetype=Archetype.HERO,
        provisioned_by=Provisioning(
            ProvisionKind.AI_ENGINE, "higgs_v2", "",
        ),
        spec=_spec(),
        rate_card=RateCard(0.5, 0.1),
    )


def test_canon_has_at_least_30_roles():
    assert len(BUILTIN_ROLES) >= 30


def test_canon_role_ids_unique():
    ids = [r.role_id for r in BUILTIN_ROLES]
    assert len(set(ids)) == len(ids)


def test_with_canon_loads_all_roles():
    reg = VoiceRoleRegistry.with_canon()
    assert len(reg.all_roles()) == len(BUILTIN_ROLES)


def test_lookup_existing():
    reg = VoiceRoleRegistry.with_canon()
    role = reg.lookup("curilla")
    assert role.character_name == "Curilla"
    assert role.archetype == Archetype.HERO


def test_lookup_unknown_raises():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(KeyError):
        reg.lookup("nope")


def test_register_role_duplicate_rejects():
    reg = VoiceRoleRegistry()
    reg.register_role(_role("rid"))
    with pytest.raises(ValueError):
        reg.register_role(_role("rid"))


def test_register_returns_role():
    reg = VoiceRoleRegistry()
    out = reg.register_role(_role("rid"))
    assert out.role_id == "rid"


def test_provision_with_ai_changes_kind():
    reg = VoiceRoleRegistry.with_canon()
    out = reg.provision_with_ai("curilla", "higgs_v2")
    assert out.provisioned_by.kind == ProvisionKind.AI_ENGINE
    assert out.provisioned_by.ref == "higgs_v2"


def test_provision_with_ai_unknown_role_raises():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(KeyError):
        reg.provision_with_ai("nope", "higgs_v2")


def test_provision_with_ai_blank_engine_raises():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(ValueError):
        reg.provision_with_ai("curilla", "")


def test_provision_with_human_sets_kind():
    reg = VoiceRoleRegistry.with_canon()
    out = reg.provision_with_human(
        "curilla", "Jane Smith", "C-2026-001",
    )
    assert out.provisioned_by.kind == ProvisionKind.HUMAN_VA
    assert out.provisioned_by.ref == "Jane Smith"
    assert out.provisioned_by.contract_id == "C-2026-001"


def test_provision_with_human_requires_contract_id():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(ValueError):
        reg.provision_with_human("curilla", "Jane Smith", "")


def test_provision_with_human_requires_va_name():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(ValueError):
        reg.provision_with_human("curilla", "", "C-1")


def test_vacate_role():
    reg = VoiceRoleRegistry.with_canon()
    out = reg.vacate("curilla")
    assert out.provisioned_by.kind == ProvisionKind.VACANT
    assert out.provisioned_by.ref == ""


def test_vacate_unknown_raises():
    reg = VoiceRoleRegistry.with_canon()
    with pytest.raises(KeyError):
        reg.vacate("nope")


def test_roles_with_kind_ai():
    reg = VoiceRoleRegistry.with_canon()
    ai_roles = reg.roles_with_kind(ProvisionKind.AI_ENGINE)
    assert len(ai_roles) >= 30


def test_roles_with_kind_human_after_swap():
    reg = VoiceRoleRegistry.with_canon()
    reg.provision_with_human(
        "curilla", "Jane Smith", "C-1",
    )
    humans = reg.roles_with_kind(ProvisionKind.HUMAN_VA)
    assert len(humans) == 1
    assert humans[0].role_id == "curilla"


def test_roles_for_archetype_hero():
    reg = VoiceRoleRegistry.with_canon()
    heroes = reg.roles_for_archetype(Archetype.HERO)
    assert len(heroes) >= 5
    assert all(r.archetype == Archetype.HERO for r in heroes)


def test_roles_for_archetype_villain():
    reg = VoiceRoleRegistry.with_canon()
    villains = reg.roles_for_archetype(Archetype.VILLAIN)
    assert any(
        r.role_id == "shadow_lord" for r in villains
    )


def test_provisioning_summary_starts_all_ai():
    reg = VoiceRoleRegistry.with_canon()
    s = reg.provisioning_summary()
    assert s[ProvisionKind.AI_ENGINE.value] == s["total"]
    assert s[ProvisionKind.HUMAN_VA.value] == 0
    assert s[ProvisionKind.VACANT.value] == 0


def test_provisioning_summary_after_swap():
    reg = VoiceRoleRegistry.with_canon()
    reg.provision_with_human(
        "curilla", "Jane Smith", "C-1",
    )
    reg.vacate("trion")
    s = reg.provisioning_summary()
    assert s[ProvisionKind.HUMAN_VA.value] == 1
    assert s[ProvisionKind.VACANT.value] == 1


def test_role_dataclass_frozen():
    import dataclasses as _d
    r = _role()
    with pytest.raises(_d.FrozenInstanceError):
        r.character_name = "Other"  # type: ignore[misc]


def test_canon_includes_all_5_crystal_warriors():
    cw = [
        r for r in BUILTIN_ROLES
        if r.role_id.startswith("cw_")
    ]
    assert len(cw) >= 5


def test_canon_includes_shadow_lord():
    ids = {r.role_id for r in BUILTIN_ROLES}
    assert "shadow_lord" in ids


def test_canon_includes_shantotto():
    ids = {r.role_id for r in BUILTIN_ROLES}
    assert "shantotto" in ids


def test_role_spec_has_languages():
    reg = VoiceRoleRegistry.with_canon()
    ayame = reg.lookup("ayame")
    assert ayame.spec.language_primary == "en"
    assert "ja" in ayame.spec.language_secondaries


def test_swap_then_swap_back():
    reg = VoiceRoleRegistry.with_canon()
    reg.provision_with_human(
        "maat", "Sir Patrick", "C-99",
    )
    reg.provision_with_ai("maat", "higgs_v2")
    role = reg.lookup("maat")
    assert role.provisioned_by.kind == ProvisionKind.AI_ENGINE


def test_register_role_persists_in_all_roles():
    reg = VoiceRoleRegistry()
    reg.register_role(_role("a"))
    reg.register_role(_role("b"))
    ids = {r.role_id for r in reg.all_roles()}
    assert ids == {"a", "b"}


def test_archetype_narrator_present():
    reg = VoiceRoleRegistry.with_canon()
    nars = reg.roles_for_archetype(Archetype.NARRATOR)
    assert len(nars) >= 1
