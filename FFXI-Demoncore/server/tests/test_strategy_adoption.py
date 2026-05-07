"""Tests for strategy_adoption."""
from __future__ import annotations

from server.strategy_adoption import (
    PinMode, StrategyAdoption,
)
from server.strategy_publisher import (
    ClearProof, EncounterKind, EncounterRef,
    StrategyPublisher,
)


def _enc(eid="maat"):
    return EncounterRef(
        kind=EncounterKind.HTBC, encounter_id=eid,
        display_name=eid.title(),
    )


def _seed():
    p = StrategyPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    gid = p.publish(
        author_id="chharith", encounter=_enc(),
        title="Maat strat", body="Step 1: ...",
        clear_proof=ClearProof(clears_count=5, wins_count=4),
        published_at=1000,
    )
    a = StrategyAdoption(_publisher=p)
    return p, a, gid


def test_adopt_happy():
    _, a, gid = _seed()
    out = a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    assert out is not None
    assert out.player_id == "bob"


def test_adopt_blank_player_blocked():
    _, a, gid = _seed()
    assert a.adopt(
        player_id="", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    ) is None


def test_adopt_unknown_guide_blocked():
    _, a, _ = _seed()
    assert a.adopt(
        player_id="bob", guide_id="ghost",
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    ) is None


def test_adopt_revoked_blocked():
    p, a, gid = _seed()
    p.revoke(guide_id=gid, reason="bad")
    assert a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    ) is None


def test_adopt_unlisted_blocked():
    p, a, gid = _seed()
    p.unlist(author_id="chharith", guide_id=gid)
    assert a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    ) is None


def test_pinned_for_returns_match():
    _, a, gid = _seed()
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    out = a.pinned_for(player_id="bob", encounter=_enc())
    assert out is not None
    assert out.guide_id == gid


def test_pinned_for_other_encounter_none():
    _, a, gid = _seed()
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    out = a.pinned_for(
        player_id="bob",
        encounter=_enc(eid="other"),
    )
    assert out is None


def test_re_adopt_replaces_prior():
    p, a, gid1 = _seed()
    gid2 = p.publish(
        author_id="chharith", encounter=_enc(),
        title="Maat alt strat", body="different approach",
        clear_proof=ClearProof(clears_count=10, wins_count=9),
        published_at=3000,
    )
    a.adopt(
        player_id="bob", guide_id=gid1,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=4000,
    )
    a.adopt(
        player_id="bob", guide_id=gid2,
        mode=PinMode.KEEP_ALWAYS_VISIBLE, adopted_at=5000,
    )
    out = a.pinned_for(player_id="bob", encounter=_enc())
    assert out.guide_id == gid2
    assert out.mode == PinMode.KEEP_ALWAYS_VISIBLE


def test_un_adopt_removes_pin():
    _, a, gid = _seed()
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    assert a.un_adopt(
        player_id="bob", guide_id=gid,
    ) is True
    assert a.pinned_for(
        player_id="bob", encounter=_enc(),
    ) is None


def test_un_adopt_unknown():
    _, a, gid = _seed()
    assert a.un_adopt(
        player_id="bob", guide_id=gid,
    ) is False


def test_adoptions_for_lists_all():
    p, a, gid = _seed()
    other_enc = EncounterRef(
        kind=EncounterKind.NM, encounter_id="ouryu",
        display_name="Ouryu",
    )
    gid2 = p.publish(
        author_id="chharith", encounter=other_enc,
        title="Ouryu", body="kite around",
        clear_proof=ClearProof(clears_count=4, wins_count=4),
        published_at=2000,
    )
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=3000,
    )
    a.adopt(
        player_id="bob", guide_id=gid2,
        mode=PinMode.KEEP_ALWAYS_VISIBLE, adopted_at=4000,
    )
    out = a.adoptions_for(player_id="bob")
    assert len(out) == 2


def test_adoptions_for_unknown_empty():
    _, a, _ = _seed()
    assert a.adoptions_for(player_id="ghost") == []


def test_adopters_count():
    _, a, gid = _seed()
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2100,
    )
    assert a.adopters_count(guide_id=gid) == 2


def test_adopters_count_zero():
    _, a, gid = _seed()
    assert a.adopters_count(guide_id=gid) == 0


def test_adopters_count_after_replace():
    """When a player replaces their pin with a new guide,
    the OLD guide's adopters_count drops by 1."""
    p, a, gid1 = _seed()
    gid2 = p.publish(
        author_id="chharith", encounter=_enc(),
        title="alt", body="b",
        clear_proof=ClearProof(clears_count=4, wins_count=4),
        published_at=2000,
    )
    a.adopt(
        player_id="bob", guide_id=gid1,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=3000,
    )
    a.adopt(
        player_id="bob", guide_id=gid2,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=4000,
    )
    assert a.adopters_count(guide_id=gid1) == 0
    assert a.adopters_count(guide_id=gid2) == 1


def test_total_adoptions():
    _, a, gid = _seed()
    a.adopt(
        player_id="bob", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", guide_id=gid,
        mode=PinMode.PIN_DURING_FIGHT, adopted_at=2100,
    )
    assert a.total_adoptions() == 2


def test_two_pin_modes():
    assert len(list(PinMode)) == 2
