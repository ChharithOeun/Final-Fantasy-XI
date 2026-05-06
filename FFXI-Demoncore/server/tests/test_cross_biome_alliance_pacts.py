"""Tests for cross-biome alliance pacts."""
from __future__ import annotations

from server.cross_biome_alliance_pacts import (
    CrossBiomeAlliancePacts,
    DISSOLUTION_COOLDOWN_SECONDS,
    MAX_PARTNERS,
    PactStage,
    Partner,
    PartnerKind,
)


def _three_partners():
    return [
        Partner(partner_id="crew_redfin", kind=PartnerKind.CREW),
        Partner(partner_id="ls_iron_hand", kind=PartnerKind.LINKSHELL),
        Partner(
            partner_id="bastok_army",
            kind=PartnerKind.NATION_MILITARY,
        ),
    ]


def test_propose_happy():
    p = CrossBiomeAlliancePacts()
    assert p.propose(
        pact_id="p1", partners=_three_partners(), now_seconds=0,
    ) is True


def test_propose_blank_id():
    p = CrossBiomeAlliancePacts()
    assert p.propose(
        pact_id="", partners=_three_partners(), now_seconds=0,
    ) is False


def test_propose_double_blocked():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    assert p.propose(
        pact_id="p1", partners=_three_partners(), now_seconds=10,
    ) is False


def test_propose_too_few_partners():
    p = CrossBiomeAlliancePacts()
    assert p.propose(
        pact_id="p1",
        partners=[Partner(partner_id="solo", kind=PartnerKind.CREW)],
        now_seconds=0,
    ) is False


def test_propose_too_many_partners():
    p = CrossBiomeAlliancePacts()
    too_many = [
        Partner(partner_id=f"p{i}", kind=PartnerKind.CREW)
        for i in range(MAX_PARTNERS + 1)
    ]
    assert p.propose(
        pact_id="p1", partners=too_many, now_seconds=0,
    ) is False


def test_propose_duplicate_partners():
    p = CrossBiomeAlliancePacts()
    dups = [
        Partner(partner_id="a", kind=PartnerKind.CREW),
        Partner(partner_id="a", kind=PartnerKind.LINKSHELL),
    ]
    assert p.propose(
        pact_id="p1", partners=dups, now_seconds=0,
    ) is False


def test_propose_blank_partner_id():
    p = CrossBiomeAlliancePacts()
    assert p.propose(
        pact_id="p1",
        partners=[
            Partner(partner_id="a", kind=PartnerKind.CREW),
            Partner(partner_id="", kind=PartnerKind.LINKSHELL),
        ],
        now_seconds=0,
    ) is False


def test_stage_starts_proposed():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    assert p.stage_of(pact_id="p1") == PactStage.PROPOSED


def test_confirm_partial_keeps_proposed():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    p.confirm(pact_id="p1", partner_id="crew_redfin", now_seconds=10)
    assert p.stage_of(pact_id="p1") == PactStage.PROPOSED


def test_confirm_all_activates():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    p.confirm(pact_id="p1", partner_id="crew_redfin", now_seconds=10)
    p.confirm(pact_id="p1", partner_id="ls_iron_hand", now_seconds=20)
    p.confirm(pact_id="p1", partner_id="bastok_army", now_seconds=30)
    assert p.stage_of(pact_id="p1") == PactStage.ACTIVATED
    assert p.is_active(pact_id="p1") is True


def test_confirm_unknown_partner():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    assert p.confirm(
        pact_id="p1", partner_id="ghost", now_seconds=10,
    ) is False


def test_confirm_unknown_pact():
    p = CrossBiomeAlliancePacts()
    assert p.confirm(
        pact_id="ghost", partner_id="x", now_seconds=10,
    ) is False


def test_dissolve_happy():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    for partner in _three_partners():
        p.confirm(pact_id="p1", partner_id=partner.partner_id, now_seconds=10)
    assert p.dissolve(
        pact_id="p1", partner_id="crew_redfin", now_seconds=100,
    ) is True
    assert p.stage_of(pact_id="p1") == PactStage.DISSOLVED
    assert p.is_active(pact_id="p1") is False


def test_dissolve_only_when_active():
    p = CrossBiomeAlliancePacts()
    p.propose(pact_id="p1", partners=_three_partners(), now_seconds=0)
    # not all confirmed, still PROPOSED
    assert p.dissolve(
        pact_id="p1", partner_id="crew_redfin", now_seconds=10,
    ) is False


def test_dissolve_cooldown_blocks_new_pact_same_partners():
    p = CrossBiomeAlliancePacts()
    partners = _three_partners()
    p.propose(pact_id="p1", partners=partners, now_seconds=0)
    for partner in partners:
        p.confirm(pact_id="p1", partner_id=partner.partner_id, now_seconds=10)
    p.dissolve(
        pact_id="p1", partner_id="crew_redfin", now_seconds=100,
    )
    # new pact among same partners within cooldown
    ok = p.propose(
        pact_id="p2", partners=partners, now_seconds=200,
    )
    assert ok is False


def test_cooldown_lifts_after_window():
    p = CrossBiomeAlliancePacts()
    partners = _three_partners()
    p.propose(pact_id="p1", partners=partners, now_seconds=0)
    for partner in partners:
        p.confirm(pact_id="p1", partner_id=partner.partner_id, now_seconds=10)
    p.dissolve(
        pact_id="p1", partner_id="crew_redfin", now_seconds=100,
    )
    ok = p.propose(
        pact_id="p2", partners=partners,
        now_seconds=100 + DISSOLUTION_COOLDOWN_SECONDS + 10,
    )
    assert ok is True


def test_partners_of_returns_list():
    p = CrossBiomeAlliancePacts()
    partners = _three_partners()
    p.propose(pact_id="p1", partners=partners, now_seconds=0)
    out = p.partners_of(pact_id="p1")
    assert len(out) == 3


def test_partners_of_unknown():
    p = CrossBiomeAlliancePacts()
    assert p.partners_of(pact_id="ghost") == ()
