"""Tests for player_marriage."""
from __future__ import annotations

from server.player_marriage import (
    PlayerMarriageSystem, MarriageState,
)


def _propose(s: PlayerMarriageSystem) -> str:
    return s.propose(
        proposer_id="naji", accepter_id="mihli",
        wedding_day=20, proposed_day=10,
    )


def _through_marriage(s: PlayerMarriageSystem) -> str:
    mid = _propose(s)
    s.accept(
        marriage_id=mid, accepter_id="mihli",
        engaged_day=11,
    )
    s.marry(marriage_id=mid, current_day=20)
    return mid


def test_propose_happy():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    assert mid is not None


def test_propose_self_blocked():
    s = PlayerMarriageSystem()
    assert s.propose(
        proposer_id="naji", accepter_id="naji",
        wedding_day=20, proposed_day=10,
    ) is None


def test_propose_wedding_before_propose_blocked():
    s = PlayerMarriageSystem()
    assert s.propose(
        proposer_id="a", accepter_id="b",
        wedding_day=5, proposed_day=10,
    ) is None


def test_propose_already_married_blocked():
    s = PlayerMarriageSystem()
    _through_marriage(s)
    # Naji can't propose to anyone else
    assert s.propose(
        proposer_id="naji", accepter_id="cara",
        wedding_day=30, proposed_day=15,
    ) is None


def test_accept_happy():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    assert s.accept(
        marriage_id=mid, accepter_id="mihli",
        engaged_day=11,
    ) is True


def test_accept_wrong_party_blocked():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    assert s.accept(
        marriage_id=mid, accepter_id="cara",
        engaged_day=11,
    ) is False


def test_marry_on_or_after_wedding_day():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    s.accept(
        marriage_id=mid, accepter_id="mihli",
        engaged_day=11,
    )
    assert s.marry(
        marriage_id=mid, current_day=20,
    ) is True


def test_marry_before_wedding_day_blocked():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    s.accept(
        marriage_id=mid, accepter_id="mihli",
        engaged_day=11,
    )
    assert s.marry(
        marriage_id=mid, current_day=15,
    ) is False


def test_marry_skip_engagement_blocked():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    assert s.marry(
        marriage_id=mid, current_day=20,
    ) is False


def test_is_married_query():
    s = PlayerMarriageSystem()
    _through_marriage(s)
    assert s.is_married(player_id="naji") is True
    assert s.is_married(player_id="mihli") is True
    assert s.is_married(player_id="cara") is False


def test_enable_shared_inventory():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.enable_shared_inventory(
        marriage_id=mid, party_id="naji",
    ) is True
    assert s.marriage(
        marriage_id=mid,
    ).shared_inventory is True


def test_shared_inventory_double_blocked():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    s.enable_shared_inventory(
        marriage_id=mid, party_id="naji",
    )
    assert s.enable_shared_inventory(
        marriage_id=mid, party_id="mihli",
    ) is False


def test_shared_inventory_third_party_blocked():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.enable_shared_inventory(
        marriage_id=mid, party_id="cara",
    ) is False


def test_deposit_pool_happy():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.deposit_pool(
        marriage_id=mid, party_id="naji",
        amount_gil=5000,
    ) is True
    assert s.marriage(
        marriage_id=mid,
    ).shared_pool_gil == 5000


def test_deposit_third_party_blocked():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.deposit_pool(
        marriage_id=mid, party_id="cara",
        amount_gil=5000,
    ) is False


def test_deposit_negative_blocked():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.deposit_pool(
        marriage_id=mid, party_id="naji",
        amount_gil=-100,
    ) is False


def test_divorce_splits_50_50():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    s.deposit_pool(
        marriage_id=mid, party_id="naji",
        amount_gil=10000,
    )
    proposer_share, accepter_share = s.divorce(
        marriage_id=mid, filer_id="naji",
        current_day=100,
    )
    assert proposer_share == 5000
    assert accepter_share == 5000


def test_divorce_odd_remainder_to_filer():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    s.deposit_pool(
        marriage_id=mid, party_id="naji",
        amount_gil=10001,
    )
    proposer_share, accepter_share = s.divorce(
        marriage_id=mid, filer_id="mihli",
        current_day=100,
    )
    # Filer (accepter) gets the odd remainder
    assert proposer_share == 5000
    assert accepter_share == 5001


def test_divorce_state_transition():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    s.divorce(
        marriage_id=mid, filer_id="naji",
        current_day=100,
    )
    m = s.marriage(marriage_id=mid)
    assert m.state == MarriageState.DIVORCED
    assert m.shared_pool_gil == 0


def test_divorce_third_party_blocked():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    assert s.divorce(
        marriage_id=mid, filer_id="cara",
        current_day=100,
    ) is None


def test_remarry_after_divorce():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    s.divorce(
        marriage_id=mid, filer_id="naji",
        current_day=100,
    )
    # Naji can propose again now
    new_mid = s.propose(
        proposer_id="naji", accepter_id="cara",
        wedding_day=130, proposed_day=110,
    )
    assert new_mid is not None


def test_years_married():
    s = PlayerMarriageSystem()
    mid = _through_marriage(s)
    # married_day=20, current=20+365*3=1115 → 3 years
    assert s.years_married(
        marriage_id=mid, current_day=1115,
    ) == 3


def test_years_married_unmarried_zero():
    s = PlayerMarriageSystem()
    mid = _propose(s)
    assert s.years_married(
        marriage_id=mid, current_day=1000,
    ) == 0


def test_unknown_marriage():
    s = PlayerMarriageSystem()
    assert s.marriage(marriage_id="ghost") is None


def test_enum_count():
    assert len(list(MarriageState)) == 4
