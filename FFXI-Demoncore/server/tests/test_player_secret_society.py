"""Tests for player_secret_society."""
from __future__ import annotations

from server.player_secret_society import (
    PlayerSecretSocietySystem, Rank,
    MembershipState,
)


def _found(s, **overrides):
    args = dict(
        society_id="silent_lotus",
        name="The Silent Lotus",
        founder_id="bob", founded_day=10,
        oath_kinds=["secrecy", "loyalty"],
    )
    args.update(overrides)
    return s.found(**args)


def test_found_happy():
    s = PlayerSecretSocietySystem()
    assert _found(s) is True


def test_found_blank():
    s = PlayerSecretSocietySystem()
    assert _found(s, society_id="") is False


def test_found_no_oaths():
    s = PlayerSecretSocietySystem()
    assert _found(s, oath_kinds=[]) is False


def test_found_dup_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    assert _found(s) is False


def test_founder_is_grandmaster():
    s = PlayerSecretSocietySystem()
    _found(s)
    m = s.membership(
        society_id="silent_lotus", player_id="bob",
    )
    assert m.rank == Rank.GRANDMASTER
    assert m.state == MembershipState.INDUCTED


def test_induct_happy():
    s = PlayerSecretSocietySystem()
    _found(s)
    assert s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    ) is True


def test_induct_self_sponsor_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    assert s.induct(
        society_id="silent_lotus",
        player_id="bob", sponsor_id="bob",
        now_day=20,
    ) is False


def test_induct_unknown_sponsor():
    s = PlayerSecretSocietySystem()
    _found(s)
    assert s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="ghost",
        now_day=20,
    ) is False


def test_induct_initiate_cannot_sponsor():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    assert s.induct(
        society_id="silent_lotus",
        player_id="dave", sponsor_id="cara",
        now_day=21,
    ) is False


def test_induct_promoted_can_sponsor():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    s.promote(
        society_id="silent_lotus",
        player_id="cara",
    )
    assert s.induct(
        society_id="silent_lotus",
        player_id="dave", sponsor_id="cara",
        now_day=21,
    ) is True


def test_induct_apostate_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    s.mark_apostate(
        society_id="silent_lotus",
        player_id="cara", now_day=30,
    )
    assert s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=40,
    ) is False


def test_induct_active_member_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    assert s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=21,
    ) is False


def test_promote_through_ranks():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    # Initiate -> Acolyte
    s.promote(
        society_id="silent_lotus",
        player_id="cara",
    )
    assert s.membership(
        society_id="silent_lotus",
        player_id="cara",
    ).rank == Rank.ACOLYTE


def test_promote_to_grandmaster_blocked_when_filled():
    s = PlayerSecretSocietySystem()
    _found(s)
    # Bob is the GRANDMASTER (founder)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    # Promote cara: INITIATE -> ACOLYTE -> ADEPT
    # -> MASTER
    for _ in range(3):
        s.promote(
            society_id="silent_lotus",
            player_id="cara",
        )
    # Now MASTER -> GRANDMASTER is blocked because
    # bob already has it
    assert s.promote(
        society_id="silent_lotus",
        player_id="cara",
    ) is False


def test_promote_after_grandmaster_departs():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    for _ in range(3):
        s.promote(
            society_id="silent_lotus",
            player_id="cara",
        )
    # Bob departs
    s.depart(
        society_id="silent_lotus",
        player_id="bob", now_day=50,
    )
    # Now cara can promote to GRANDMASTER
    assert s.promote(
        society_id="silent_lotus",
        player_id="cara",
    ) is True
    assert s.society(
        society_id="silent_lotus",
    ).grandmaster_id == "cara"


def test_promote_at_top_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    # Bob is already GRANDMASTER
    assert s.promote(
        society_id="silent_lotus",
        player_id="bob",
    ) is False


def test_depart():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    assert s.depart(
        society_id="silent_lotus",
        player_id="cara", now_day=50,
    ) is True


def test_depart_double_blocked():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    s.depart(
        society_id="silent_lotus",
        player_id="cara", now_day=50,
    )
    assert s.depart(
        society_id="silent_lotus",
        player_id="cara", now_day=51,
    ) is False


def test_mark_apostate():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    assert s.mark_apostate(
        society_id="silent_lotus",
        player_id="cara", now_day=30,
    ) is True


def test_mark_deceased():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    assert s.mark_deceased(
        society_id="silent_lotus",
        player_id="cara", now_day=30,
    ) is True


def test_members_of_filters_inducted():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    s.induct(
        society_id="silent_lotus",
        player_id="dave", sponsor_id="bob",
        now_day=21,
    )
    s.depart(
        society_id="silent_lotus",
        player_id="dave", now_day=50,
    )
    out = s.members_of(society_id="silent_lotus")
    ids = [m.player_id for m in out]
    assert "bob" in ids
    assert "cara" in ids
    assert "dave" not in ids


def test_societies_of_player():
    s = PlayerSecretSocietySystem()
    _found(s, society_id="a", name="A")
    _found(s, society_id="b", name="B",
           founder_id="other_founder")
    s.induct(
        society_id="b", player_id="bob",
        sponsor_id="other_founder", now_day=20,
    )
    out = s.societies_of(player_id="bob")
    ids = sorted(soc.society_id for soc in out)
    assert ids == ["a", "b"]


def test_societies_of_excludes_apostate():
    s = PlayerSecretSocietySystem()
    _found(s)
    s.induct(
        society_id="silent_lotus",
        player_id="cara", sponsor_id="bob",
        now_day=20,
    )
    s.mark_apostate(
        society_id="silent_lotus",
        player_id="cara", now_day=30,
    )
    assert s.societies_of(player_id="cara") == []


def test_society_unknown():
    s = PlayerSecretSocietySystem()
    assert s.society(society_id="ghost") is None


def test_membership_unknown():
    s = PlayerSecretSocietySystem()
    assert s.membership(
        society_id="ghost", player_id="bob",
    ) is None


def test_enum_counts():
    assert len(list(Rank)) == 5
    assert len(list(MembershipState)) == 4
