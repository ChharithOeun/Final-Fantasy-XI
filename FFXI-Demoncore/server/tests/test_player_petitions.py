"""Tests for player_petitions."""
from __future__ import annotations

from server.player_petitions import (
    Petition, PetitionState, PlayerPetitions, Response,
)


def _petition(pid="p1", office="bastok_president",
              drafter="bob", target=10,
              drafted=10, expires=40, nation="bastok"):
    return Petition(
        petition_id=pid, addressed_office_id=office,
        drafter_id=drafter, title="Repeal the bread tax",
        body="The cost of food is too high.",
        signature_target=target,
        drafted_day=drafted, expires_day=expires,
        nation=nation,
    )


def test_draft_happy():
    p = PlayerPetitions()
    assert p.draft_petition(
        _petition(), drafter_nation="bastok",
    ) is True


def test_draft_blank_blocked():
    p = PlayerPetitions()
    bad = Petition(
        petition_id="", addressed_office_id="o",
        drafter_id="b", title="t", body="b",
        signature_target=10, drafted_day=10,
        expires_day=20, nation="bastok",
    )
    assert p.draft_petition(
        bad, drafter_nation="bastok",
    ) is False


def test_draft_zero_target_blocked():
    p = PlayerPetitions()
    bad = _petition(target=0)
    assert p.draft_petition(
        bad, drafter_nation="bastok",
    ) is False


def test_draft_invalid_dates_blocked():
    p = PlayerPetitions()
    bad = _petition(drafted=20, expires=15)
    assert p.draft_petition(
        bad, drafter_nation="bastok",
    ) is False


def test_draft_wrong_nation_blocked():
    p = PlayerPetitions()
    assert p.draft_petition(
        _petition(), drafter_nation="sandy",
    ) is False


def test_draft_dup_blocked():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.draft_petition(
        _petition(), drafter_nation="bastok",
    ) is False


def test_drafter_is_first_signer():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.signature_count(petition_id="p1") == 1


def test_sign_happy():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    ) is True
    assert p.signature_count(petition_id="p1") == 2


def test_sign_wrong_nation_blocked():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="sandy",
    ) is False


def test_sign_dup_blocked():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    assert p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    ) is False


def test_sign_drafter_dup_blocked():
    """Drafter is implicit signer, can't re-sign."""
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.sign(
        petition_id="p1", signer_id="bob",
        signer_nation="bastok",
    ) is False


def test_quorum_met_state():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=3), drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="dave",
        signer_nation="bastok",
    )
    assert p.state(
        petition_id="p1",
    ) == PetitionState.QUORUM_MET


def test_sign_after_quorum_blocked():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=2), drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    # Already quorum-met
    assert p.sign(
        petition_id="p1", signer_id="dave",
        signer_nation="bastok",
    ) is False


def test_respond_accept():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=2), drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    assert p.respond(
        petition_id="p1", by_holder_id="cid",
        response=Response.ACCEPT,
    ) is True
    assert p.state(
        petition_id="p1",
    ) == PetitionState.ADDRESSED
    assert p.response_of(
        petition_id="p1",
    ) == Response.ACCEPT


def test_respond_pre_quorum_blocked():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.respond(
        petition_id="p1", by_holder_id="cid",
        response=Response.ACCEPT,
    ) is False


def test_respond_blank_holder_blocked():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=2), drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    assert p.respond(
        petition_id="p1", by_holder_id="",
        response=Response.ACCEPT,
    ) is False


def test_withdraw_open():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.withdraw(
        petition_id="p1", by_drafter_id="bob",
    ) is True
    assert p.state(
        petition_id="p1",
    ) == PetitionState.WITHDRAWN


def test_withdraw_other_player_blocked():
    p = PlayerPetitions()
    p.draft_petition(_petition(), drafter_nation="bastok")
    assert p.withdraw(
        petition_id="p1", by_drafter_id="cara",
    ) is False


def test_withdraw_after_quorum_blocked():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=2), drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    assert p.withdraw(
        petition_id="p1", by_drafter_id="bob",
    ) is False


def test_tick_expires():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(expires=40), drafter_nation="bastok",
    )
    expired = p.tick(now_day=50)
    assert "p1" in expired
    assert p.state(
        petition_id="p1",
    ) == PetitionState.EXPIRED


def test_tick_doesnt_expire_quorum():
    p = PlayerPetitions()
    p.draft_petition(
        _petition(target=2, expires=40),
        drafter_nation="bastok",
    )
    p.sign(
        petition_id="p1", signer_id="cara",
        signer_nation="bastok",
    )
    expired = p.tick(now_day=50)
    assert expired == []
    # Still quorum_met
    assert p.state(
        petition_id="p1",
    ) == PetitionState.QUORUM_MET


def test_pending_for_office():
    p = PlayerPetitions()
    p.draft_petition(
        _petition("a", target=2),
        drafter_nation="bastok",
    )
    p.sign(
        petition_id="a", signer_id="cara",
        signer_nation="bastok",
    )
    out = p.pending_for_office(
        office_id="bastok_president",
    )
    assert len(out) == 1
    assert out[0].petition_id == "a"


def test_response_of_unknown():
    p = PlayerPetitions()
    assert p.response_of(petition_id="ghost") is None


def test_five_petition_states():
    assert len(list(PetitionState)) == 5


def test_three_responses():
    assert len(list(Response)) == 3
