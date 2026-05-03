"""Tests for mob pack hierarchy."""
from __future__ import annotations

from server.mob_pack_hierarchy import (
    ALPHA_DAMAGE_BUFF_PCT,
    ALPHA_DEATH_MORALE_PENALTY,
    MobPackHierarchyRegistry,
    PackRole,
)


def test_form_pack_creates_alpha():
    reg = MobPackHierarchyRegistry()
    pack = reg.form_pack(
        pack_id="orc_clan", alpha_uid="orc_chief",
    )
    assert pack is not None
    assert pack.alpha_uid == "orc_chief"
    assert pack.members["orc_chief"].role == PackRole.ALPHA


def test_double_form_rejected():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    second = reg.form_pack(pack_id="p1", alpha_uid="b")
    assert second is None


def test_add_beta_member():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    assert reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA, strength=70,
    )
    assert reg.pack("p1").members["b"].role == PackRole.BETA


def test_cannot_add_second_alpha():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    assert not reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.ALPHA,
    )


def test_add_member_unknown_pack():
    reg = MobPackHierarchyRegistry()
    assert not reg.add_member(
        pack_id="ghost", member_uid="b",
        role=PackRole.BETA,
    )


def test_add_duplicate_member_rejected():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b", role=PackRole.BETA,
    )
    assert not reg.add_member(
        pack_id="p1", member_uid="b", role=PackRole.OMEGA,
    )


def test_alpha_buffs_active():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    buffs = reg.alpha_buffs("p1")
    assert buffs is not None
    assert buffs.damage_pct == ALPHA_DAMAGE_BUFF_PCT


def test_alpha_buffs_none_after_alpha_killed():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.kill_member(pack_id="p1", member_uid="a")
    # No beta, so no successor; alpha_buffs is None
    buffs = reg.alpha_buffs("p1")
    assert buffs is None


def test_alpha_buffs_unknown_pack():
    reg = MobPackHierarchyRegistry()
    assert reg.alpha_buffs("ghost") is None


def test_kill_alpha_promotes_strongest_beta():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b1",
        role=PackRole.BETA, strength=60,
    )
    reg.add_member(
        pack_id="p1", member_uid="b2",
        role=PackRole.BETA, strength=80,
    )
    succession = reg.kill_member(
        pack_id="p1", member_uid="a",
    )
    assert succession is not None
    assert succession.new_alpha == "b2"


def test_kill_alpha_lowers_morale():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA, strength=50,
    )
    succession = reg.kill_member(
        pack_id="p1", member_uid="a",
    )
    assert (
        succession.morale_after
        == 100 - ALPHA_DEATH_MORALE_PENALTY
    )


def test_kill_alpha_no_beta_returns_no_successor():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="o1",
        role=PackRole.OMEGA, strength=20,
    )
    succession = reg.kill_member(
        pack_id="p1", member_uid="a",
    )
    assert succession is not None
    assert succession.new_alpha is None
    assert "no beta available" in succession.note


def test_kill_beta_no_succession():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA,
    )
    succession = reg.kill_member(
        pack_id="p1", member_uid="b",
    )
    assert succession is None


def test_kill_unknown_member():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    assert reg.kill_member(
        pack_id="p1", member_uid="ghost",
    ) is None


def test_kill_member_twice_returns_none():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA,
    )
    reg.kill_member(pack_id="p1", member_uid="b")
    assert reg.kill_member(
        pack_id="p1", member_uid="b",
    ) is None


def test_omega_promoted_to_beta_on_succession():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA, strength=80,
    )
    reg.add_member(
        pack_id="p1", member_uid="o1",
        role=PackRole.OMEGA, strength=40,
    )
    reg.kill_member(pack_id="p1", member_uid="a")
    # o1 should have been promoted
    assert reg.pack("p1").members["o1"].role == PackRole.BETA


def test_members_by_role_filters_alive():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b1",
        role=PackRole.BETA,
    )
    reg.add_member(
        pack_id="p1", member_uid="b2",
        role=PackRole.BETA,
    )
    reg.kill_member(pack_id="p1", member_uid="b1")
    living_betas = reg.members_by_role(
        pack_id="p1", role=PackRole.BETA,
    )
    assert len(living_betas) == 1
    assert living_betas[0].member_uid == "b2"


def test_succession_count_increments():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.add_member(
        pack_id="p1", member_uid="b",
        role=PackRole.BETA, strength=80,
    )
    reg.kill_member(pack_id="p1", member_uid="a")
    assert reg.pack("p1").succession_count == 1


def test_total_packs():
    reg = MobPackHierarchyRegistry()
    reg.form_pack(pack_id="p1", alpha_uid="a")
    reg.form_pack(pack_id="p2", alpha_uid="x")
    assert reg.total_packs() == 2
