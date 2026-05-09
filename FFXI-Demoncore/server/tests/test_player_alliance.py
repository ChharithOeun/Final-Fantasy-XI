"""Tests for player_alliance."""
from __future__ import annotations

from server.player_alliance import (
    PlayerAllianceSystem, AllianceState,
)


def _form_active(s: PlayerAllianceSystem) -> str:
    aid = s.found(
        name="Iron Pact", founder_id="naji",
        formed_day=10,
    )
    s.add_member(alliance_id=aid, member_id="bob")
    return aid


def test_found_happy():
    s = PlayerAllianceSystem()
    aid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert aid is not None


def test_found_dup_name_blocked():
    s = PlayerAllianceSystem()
    s.found(
        name="X", founder_id="a", formed_day=10,
    )
    assert s.found(
        name="X", founder_id="b", formed_day=10,
    ) is None


def test_found_empty_name_blocked():
    s = PlayerAllianceSystem()
    assert s.found(
        name="", founder_id="naji", formed_day=10,
    ) is None


def test_starts_forming():
    s = PlayerAllianceSystem()
    aid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert s.alliance(
        alliance_id=aid,
    ).state == AllianceState.FORMING


def test_active_at_min_members():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.alliance(
        alliance_id=aid,
    ).state == AllianceState.ACTIVE


def test_add_member_cap():
    s = PlayerAllianceSystem()
    aid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    for i in range(11):
        s.add_member(
            alliance_id=aid, member_id=f"m{i}",
        )
    assert s.add_member(
        alliance_id=aid, member_id="overflow",
    ) is False


def test_add_dup_member_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.add_member(
        alliance_id=aid, member_id="bob",
    ) is False


def test_remove_member_happy():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.add_member(alliance_id=aid, member_id="cara")
    assert s.remove_member(
        alliance_id=aid, member_id="cara",
    ) is True


def test_remove_drops_to_forming():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.remove_member(
        alliance_id=aid, member_id="bob",
    )
    assert s.alliance(
        alliance_id=aid,
    ).state == AllianceState.FORMING


def test_remove_founder_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.remove_member(
        alliance_id=aid, member_id="naji",
    ) is False


def test_contribute_to_pool():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.contribute_to_pool(
        alliance_id=aid, contributor_id="naji",
        amount_gil=5000,
    ) is True
    assert s.alliance(
        alliance_id=aid,
    ).defense_pool_gil == 5000


def test_contribute_non_member_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.contribute_to_pool(
        alliance_id=aid, contributor_id="cara",
        amount_gil=5000,
    ) is False


def test_contribute_in_forming_blocked():
    s = PlayerAllianceSystem()
    aid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert s.contribute_to_pool(
        alliance_id=aid, contributor_id="naji",
        amount_gil=5000,
    ) is False


def test_report_attack_happy():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    eid = s.report_attack(
        alliance_id=aid, victim_id="bob",
        attacker_id="volker", occurred_day=15,
    )
    assert eid is not None


def test_report_attack_member_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    # Attacker is also a member — internal squabble,
    # not the alliance's defense business
    assert s.report_attack(
        alliance_id=aid, victim_id="bob",
        attacker_id="naji", occurred_day=15,
    ) is None


def test_report_attack_non_member_victim_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.report_attack(
        alliance_id=aid, victim_id="cara",
        attacker_id="volker", occurred_day=15,
    ) is None


def test_provocation_grants_after_attack():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.report_attack(
        alliance_id=aid, victim_id="bob",
        attacker_id="volker", occurred_day=15,
    )
    assert s.has_provocation_against(
        alliance_id=aid, attacker_id="volker",
    ) is True


def test_no_provocation_unattacked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.has_provocation_against(
        alliance_id=aid, attacker_id="volker",
    ) is False


def test_dissolve_happy():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.contribute_to_pool(
        alliance_id=aid, contributor_id="naji",
        amount_gil=10000,
    )
    final = s.dissolve(
        alliance_id=aid, founder_id="naji",
    )
    assert final == 10000


def test_dissolve_wrong_founder_blocked():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    assert s.dissolve(
        alliance_id=aid, founder_id="bob",
    ) is None


def test_dissolved_no_more_actions():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.dissolve(alliance_id=aid, founder_id="naji")
    assert s.add_member(
        alliance_id=aid, member_id="cara",
    ) is False


def test_attacks_against_query():
    s = PlayerAllianceSystem()
    aid = _form_active(s)
    s.report_attack(
        alliance_id=aid, victim_id="bob",
        attacker_id="volker", occurred_day=15,
    )
    s.report_attack(
        alliance_id=aid, victim_id="naji",
        attacker_id="volker", occurred_day=16,
    )
    assert len(s.attacks_against(
        alliance_id=aid,
    )) == 2


def test_unknown_alliance():
    s = PlayerAllianceSystem()
    assert s.alliance(alliance_id="ghost") is None


def test_enum_count():
    assert len(list(AllianceState)) == 3
