"""Tests for player_sworn_brotherhood."""
from __future__ import annotations

from server.player_sworn_brotherhood import (
    PlayerSwornBrotherhoodSystem, BrotherhoodState,
)


def _found_active(
    s: PlayerSwornBrotherhoodSystem,
) -> str:
    bid = s.found(
        name="Three Lions", founder_id="naji",
        formed_day=10,
    )
    s.swear_in(brotherhood_id=bid, member_id="bob")
    return bid


def test_found_happy():
    s = PlayerSwornBrotherhoodSystem()
    bid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert bid is not None


def test_found_dup_name_blocked():
    s = PlayerSwornBrotherhoodSystem()
    s.found(
        name="X", founder_id="a", formed_day=10,
    )
    assert s.found(
        name="X", founder_id="b", formed_day=10,
    ) is None


def test_starts_proposed():
    s = PlayerSwornBrotherhoodSystem()
    bid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert s.brotherhood(
        brotherhood_id=bid,
    ).state == BrotherhoodState.PROPOSED


def test_active_at_min_size():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.brotherhood(
        brotherhood_id=bid,
    ).state == BrotherhoodState.ACTIVE


def test_swear_in_dup_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.swear_in(
        brotherhood_id=bid, member_id="bob",
    ) is False


def test_swear_in_at_cap():
    s = PlayerSwornBrotherhoodSystem()
    bid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    for i in range(6):
        s.swear_in(
            brotherhood_id=bid, member_id=f"m{i}",
        )
    assert s.swear_in(
        brotherhood_id=bid, member_id="overflow",
    ) is False


def test_can_sense_active_brothers():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.can_sense(
        brotherhood_id=bid, seeker_id="naji",
        target_id="bob",
    ) is True


def test_cannot_sense_self():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.can_sense(
        brotherhood_id=bid, seeker_id="naji",
        target_id="naji",
    ) is False


def test_cannot_sense_non_member():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.can_sense(
        brotherhood_id=bid, seeker_id="naji",
        target_id="cara",
    ) is False


def test_cannot_sense_in_proposed():
    s = PlayerSwornBrotherhoodSystem()
    bid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert s.can_sense(
        brotherhood_id=bid, seeker_id="naji",
        target_id="bob",
    ) is False


def test_add_fame_grows_pool():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.add_fame(brotherhood_id=bid, fame_amount=50)
    s.add_fame(brotherhood_id=bid, fame_amount=30)
    assert s.brotherhood(
        brotherhood_id=bid,
    ).shared_fame == 80


def test_add_fame_in_proposed_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = s.found(
        name="X", founder_id="naji", formed_day=10,
    )
    assert s.add_fame(
        brotherhood_id=bid, fame_amount=50,
    ) is False


def test_add_negative_fame_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.add_fame(
        brotherhood_id=bid, fame_amount=-10,
    ) is False


def test_vote_disband_partial_no_dissolve():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.swear_in(brotherhood_id=bid, member_id="cara")
    s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    )
    # Only 1 of 3 votes — still ACTIVE
    assert s.brotherhood(
        brotherhood_id=bid,
    ).state == BrotherhoodState.ACTIVE


def test_vote_disband_unanimous_dissolves():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.swear_in(brotherhood_id=bid, member_id="cara")
    s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    )
    s.vote_disband(
        brotherhood_id=bid, voter_id="bob",
    )
    s.vote_disband(
        brotherhood_id=bid, voter_id="cara",
    )
    assert s.brotherhood(
        brotherhood_id=bid,
    ).state == BrotherhoodState.DISBANDED


def test_vote_disband_non_member_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.vote_disband(
        brotherhood_id=bid, voter_id="cara",
    ) is False


def test_vote_disband_double_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    )
    assert s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    ) is False


def test_withdraw_disband_vote():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    )
    assert s.withdraw_disband_vote(
        brotherhood_id=bid, voter_id="naji",
    ) is True
    # naji can vote again
    assert s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    ) is True


def test_withdraw_without_vote_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    assert s.withdraw_disband_vote(
        brotherhood_id=bid, voter_id="naji",
    ) is False


def test_actions_after_disband_blocked():
    s = PlayerSwornBrotherhoodSystem()
    bid = _found_active(s)
    s.vote_disband(
        brotherhood_id=bid, voter_id="naji",
    )
    s.vote_disband(
        brotherhood_id=bid, voter_id="bob",
    )
    assert s.swear_in(
        brotherhood_id=bid, member_id="cara",
    ) is False
    assert s.add_fame(
        brotherhood_id=bid, fame_amount=10,
    ) is False


def test_brotherhoods_of_player():
    s = PlayerSwornBrotherhoodSystem()
    s.found(
        name="A", founder_id="naji", formed_day=10,
    )
    s.found(
        name="B", founder_id="naji", formed_day=10,
    )
    s.found(
        name="C", founder_id="bob", formed_day=10,
    )
    assert len(
        s.brotherhoods_of(member_id="naji"),
    ) == 2


def test_unknown_brotherhood():
    s = PlayerSwornBrotherhoodSystem()
    assert s.brotherhood(
        brotherhood_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(BrotherhoodState)) == 3
