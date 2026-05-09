"""Tests for npc_family_consequences."""
from __future__ import annotations

from server.npc_family_consequences import (
    NPCFamilyConsequencesSystem, KinKind, Severity,
)


def test_add_kin_happy():
    s = NPCFamilyConsequencesSystem()
    assert s.add_kin(
        npc_id="off_volker",
        relative_id="naomi_volker",
        kind=KinKind.SIBLING,
    ) is True


def test_add_kin_self_blocked():
    s = NPCFamilyConsequencesSystem()
    assert s.add_kin(
        npc_id="o", relative_id="o",
        kind=KinKind.SIBLING,
    ) is False


def test_add_kin_blank():
    s = NPCFamilyConsequencesSystem()
    assert s.add_kin(
        npc_id="", relative_id="x",
        kind=KinKind.SIBLING,
    ) is False


def test_add_kin_dup_blocked():
    s = NPCFamilyConsequencesSystem()
    s.add_kin(
        npc_id="o", relative_id="r",
        kind=KinKind.SIBLING,
    )
    assert s.add_kin(
        npc_id="o", relative_id="r",
        kind=KinKind.SIBLING,
    ) is False


def test_kin_of():
    s = NPCFamilyConsequencesSystem()
    s.add_kin(
        npc_id="off_volker",
        relative_id="naomi", kind=KinKind.SIBLING,
    )
    s.add_kin(
        npc_id="off_volker",
        relative_id="father", kind=KinKind.PARENT,
    )
    out = s.kin_of(npc_id="off_volker")
    assert len(out) == 2


def test_apply_consequence():
    s = NPCFamilyConsequencesSystem()
    cid = s.apply_consequence(
        relative_id="naomi",
        defector_id="off_volker",
        severity=Severity.SHUNNED,
        note="brother defected",
        occurred_day=400,
    )
    assert cid is not None


def test_apply_blank():
    s = NPCFamilyConsequencesSystem()
    cid = s.apply_consequence(
        relative_id="", defector_id="x",
        severity=Severity.SHUNNED,
        note="x", occurred_day=400,
    )
    assert cid is None


def test_revoke_consequence():
    s = NPCFamilyConsequencesSystem()
    cid = s.apply_consequence(
        relative_id="naomi",
        defector_id="off_volker",
        severity=Severity.SURVEILLANCE,
        note="x", occurred_day=400,
    )
    assert s.revoke_consequence(
        consequence_id=cid, now_day=500,
        reason="cleared by judge",
    ) is True


def test_revoke_double_blocked():
    s = NPCFamilyConsequencesSystem()
    cid = s.apply_consequence(
        relative_id="naomi",
        defector_id="off_volker",
        severity=Severity.SHUNNED, note="x",
        occurred_day=400,
    )
    s.revoke_consequence(
        consequence_id=cid, now_day=500, reason="x",
    )
    assert s.revoke_consequence(
        consequence_id=cid, now_day=501, reason="y",
    ) is False


def test_revoke_before_occurred_blocked():
    s = NPCFamilyConsequencesSystem()
    cid = s.apply_consequence(
        relative_id="naomi",
        defector_id="off_volker",
        severity=Severity.SHUNNED, note="x",
        occurred_day=400,
    )
    assert s.revoke_consequence(
        consequence_id=cid, now_day=300, reason="x",
    ) is False


def test_consequences_for_relative():
    s = NPCFamilyConsequencesSystem()
    s.apply_consequence(
        relative_id="naomi",
        defector_id="o1",
        severity=Severity.SHUNNED, note="x",
        occurred_day=10,
    )
    s.apply_consequence(
        relative_id="naomi",
        defector_id="o2",
        severity=Severity.SURVEILLANCE,
        note="y", occurred_day=20,
    )
    s.apply_consequence(
        relative_id="other",
        defector_id="o1",
        severity=Severity.SHUNNED, note="z",
        occurred_day=30,
    )
    out = s.consequences_for_relative(
        relative_id="naomi",
    )
    assert len(out) == 2


def test_active_consequences():
    s = NPCFamilyConsequencesSystem()
    cid_a = s.apply_consequence(
        relative_id="n", defector_id="o",
        severity=Severity.SHUNNED, note="x",
        occurred_day=10,
    )
    cid_b = s.apply_consequence(
        relative_id="n", defector_id="o",
        severity=Severity.SURVEILLANCE,
        note="y", occurred_day=20,
    )
    s.revoke_consequence(
        consequence_id=cid_a, now_day=30,
        reason="x",
    )
    out = s.active_consequences(relative_id="n")
    assert len(out) == 1
    assert out[0].consequence_id == cid_b


def test_auto_apply_assigns_default_severities():
    s = NPCFamilyConsequencesSystem()
    s.add_kin(
        npc_id="off_volker",
        relative_id="naomi", kind=KinKind.SIBLING,
    )
    s.add_kin(
        npc_id="off_volker",
        relative_id="dad", kind=KinKind.PARENT,
    )
    s.add_kin(
        npc_id="off_volker",
        relative_id="apprentice_kid",
        kind=KinKind.APPRENTICE,
    )
    applied = s.auto_apply_on_defection(
        defector_id="off_volker", now_day=400,
    )
    assert len(applied) == 3
    sevs = {
        s.consequence(
            consequence_id=cid,
        ).severity
        for cid in applied
    }
    assert Severity.SURVEILLANCE in sevs  # sibling
    assert Severity.SHUNNED in sevs        # parent
    assert Severity.EMPLOYMENT in sevs     # apprentice


def test_auto_apply_protected_relatives():
    s = NPCFamilyConsequencesSystem()
    s.add_kin(
        npc_id="off_volker",
        relative_id="naomi", kind=KinKind.SIBLING,
    )
    s.add_kin(
        npc_id="off_volker",
        relative_id="dad", kind=KinKind.PARENT,
    )
    applied = s.auto_apply_on_defection(
        defector_id="off_volker", now_day=400,
        protected_relatives=["naomi"],
    )
    # Naomi got PROTECTED, dad got SHUNNED
    naomi_cons = s.consequences_for_relative(
        relative_id="naomi",
    )
    dad_cons = s.consequences_for_relative(
        relative_id="dad",
    )
    assert naomi_cons[0].severity == Severity.PROTECTED
    assert dad_cons[0].severity == Severity.SHUNNED


def test_auto_apply_skips_unrelated():
    s = NPCFamilyConsequencesSystem()
    s.add_kin(
        npc_id="off_naji", relative_id="r1",
        kind=KinKind.SIBLING,
    )
    s.add_kin(
        npc_id="off_volker", relative_id="r2",
        kind=KinKind.SIBLING,
    )
    applied = s.auto_apply_on_defection(
        defector_id="off_volker", now_day=400,
    )
    # Only Volker's relatives get hit
    assert len(applied) == 1
    assert s.consequences_for_relative(
        relative_id="r1",
    ) == []


def test_consequence_unknown():
    s = NPCFamilyConsequencesSystem()
    assert s.consequence(
        consequence_id="ghost",
    ) is None


def test_revoke_unknown():
    s = NPCFamilyConsequencesSystem()
    assert s.revoke_consequence(
        consequence_id="ghost", now_day=10,
        reason="x",
    ) is False


def test_enum_counts():
    assert len(list(KinKind)) == 8
    assert len(list(Severity)) == 6
