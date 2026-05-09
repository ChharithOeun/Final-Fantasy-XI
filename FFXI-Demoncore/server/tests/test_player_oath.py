"""Tests for player_oath."""
from __future__ import annotations

from server.player_oath import (
    PlayerOathSystem, OathKind, OathState,
)


def _swear(
    s: PlayerOathSystem,
    swearer: str = "naji", deadline: int = 30,
    witnesses: tuple[str, ...] = ("bob", "cara"),
) -> str:
    return s.swear(
        swearer_id=swearer, kind=OathKind.ABSTAIN,
        description="No combat for 30 days",
        sworn_day=10, deadline_day=deadline,
        witnesses=witnesses,
    )


def test_swear_happy():
    s = PlayerOathSystem()
    oid = _swear(s)
    assert oid is not None


def test_swear_empty_swearer_blocked():
    s = PlayerOathSystem()
    assert s.swear(
        swearer_id="", kind=OathKind.ABSTAIN,
        description="d", sworn_day=10,
        deadline_day=30,
    ) is None


def test_swear_empty_description_blocked():
    s = PlayerOathSystem()
    assert s.swear(
        swearer_id="naji", kind=OathKind.ABSTAIN,
        description="", sworn_day=10,
        deadline_day=30,
    ) is None


def test_swear_deadline_before_sworn_blocked():
    s = PlayerOathSystem()
    assert s.swear(
        swearer_id="naji", kind=OathKind.ABSTAIN,
        description="d", sworn_day=10,
        deadline_day=5,
    ) is None


def test_swear_self_witness_blocked():
    s = PlayerOathSystem()
    assert s.swear(
        swearer_id="naji", kind=OathKind.ABSTAIN,
        description="d", sworn_day=10,
        deadline_day=30, witnesses=("naji",),
    ) is None


def test_swear_dup_witness_blocked():
    s = PlayerOathSystem()
    assert s.swear(
        swearer_id="naji", kind=OathKind.ABSTAIN,
        description="d", sworn_day=10,
        deadline_day=30, witnesses=("bob", "bob"),
    ) is None


def test_fulfill_within_window():
    s = PlayerOathSystem()
    oid = _swear(s)
    honor = s.fulfill(
        oath_id=oid, swearer_id="naji",
        current_day=25,
    )
    assert honor == 30


def test_fulfill_state_set():
    s = PlayerOathSystem()
    oid = _swear(s)
    s.fulfill(
        oath_id=oid, swearer_id="naji",
        current_day=25,
    )
    assert s.oath(
        oath_id=oid,
    ).state == OathState.FULFILLED


def test_fulfill_after_deadline_blocked():
    s = PlayerOathSystem()
    oid = _swear(s)
    assert s.fulfill(
        oath_id=oid, swearer_id="naji",
        current_day=40,
    ) is None


def test_fulfill_wrong_swearer_blocked():
    s = PlayerOathSystem()
    oid = _swear(s)
    assert s.fulfill(
        oath_id=oid, swearer_id="bob",
        current_day=25,
    ) is None


def test_break_oath_returns_penalty():
    s = PlayerOathSystem()
    oid = _swear(s)
    delta = s.break_oath(
        oath_id=oid, current_day=15,
    )
    assert delta == -60


def test_break_state_set():
    s = PlayerOathSystem()
    oid = _swear(s)
    s.break_oath(oath_id=oid, current_day=15)
    assert s.oath(
        oath_id=oid,
    ).state == OathState.BROKEN


def test_break_after_fulfill_blocked():
    s = PlayerOathSystem()
    oid = _swear(s)
    s.fulfill(
        oath_id=oid, swearer_id="naji",
        current_day=25,
    )
    assert s.break_oath(
        oath_id=oid, current_day=26,
    ) is None


def test_auto_expire_passes_deadline():
    s = PlayerOathSystem()
    oid = _swear(s)
    assert s.auto_expire(
        oath_id=oid, current_day=40,
    ) is True
    assert s.oath(
        oath_id=oid,
    ).state == OathState.BROKEN


def test_auto_expire_before_deadline_blocked():
    s = PlayerOathSystem()
    oid = _swear(s)
    assert s.auto_expire(
        oath_id=oid, current_day=20,
    ) is False


def test_active_oaths_lookup():
    s = PlayerOathSystem()
    o1 = _swear(s)
    o2 = _swear(s)
    s.fulfill(
        oath_id=o1, swearer_id="naji",
        current_day=15,
    )
    actives = s.active_oaths(swearer_id="naji")
    assert len(actives) == 1
    assert actives[0].oath_id == o2


def test_lifetime_honor_aggregates():
    s = PlayerOathSystem()
    o1 = _swear(s)
    o2 = _swear(s)
    o3 = _swear(s)
    s.fulfill(
        oath_id=o1, swearer_id="naji",
        current_day=15,
    )
    s.fulfill(
        oath_id=o2, swearer_id="naji",
        current_day=16,
    )
    s.break_oath(oath_id=o3, current_day=15)
    # 30 + 30 - 60 = 0
    assert s.lifetime_honor_delta(
        swearer_id="naji",
    ) == 0


def test_fulfilled_oaths_listing():
    s = PlayerOathSystem()
    o1 = _swear(s)
    o2 = _swear(s)
    s.fulfill(
        oath_id=o1, swearer_id="naji",
        current_day=15,
    )
    s.break_oath(oath_id=o2, current_day=15)
    fulfilled = s.fulfilled_oaths(swearer_id="naji")
    assert len(fulfilled) == 1
    assert fulfilled[0].oath_id == o1


def test_witnesses_recorded():
    s = PlayerOathSystem()
    oid = _swear(s)
    o = s.oath(oath_id=oid)
    assert "bob" in o.witnesses
    assert "cara" in o.witnesses


def test_unknown_oath():
    s = PlayerOathSystem()
    assert s.oath(oath_id="ghost") is None


def test_active_oaths_unknown_swearer():
    s = PlayerOathSystem()
    assert s.active_oaths(swearer_id="ghost") == []


def test_lifetime_honor_unknown_zero():
    s = PlayerOathSystem()
    assert s.lifetime_honor_delta(
        swearer_id="ghost",
    ) == 0


def test_enum_counts():
    assert len(list(OathKind)) == 4
    assert len(list(OathState)) == 3
