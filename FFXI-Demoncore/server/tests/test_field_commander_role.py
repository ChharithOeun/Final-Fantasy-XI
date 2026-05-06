"""Tests for field_commander_role."""
from __future__ import annotations

from server.field_commander_role import (
    FieldCommanderRole,
    FormationOrder,
    ORDER_COOLDOWN_SECONDS,
    ORDER_DURATION_SECONDS,
)


def test_designate_happy():
    f = FieldCommanderRole()
    assert f.designate(
        alliance_id="alpha", commander_id="alice",
    ) is True
    assert f.commander(alliance_id="alpha") == "alice"


def test_blank_alliance_blocked():
    f = FieldCommanderRole()
    assert f.designate(
        alliance_id="", commander_id="alice",
    ) is False


def test_designate_same_blocked():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    assert f.designate(
        alliance_id="alpha", commander_id="alice",
    ) is False


def test_vacate():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    assert f.vacate(alliance_id="alpha") is True
    assert f.commander(alliance_id="alpha") is None


def test_issue_order_happy():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    out = f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    assert out.accepted is True
    assert out.order == FormationOrder.TURTLE


def test_issue_order_not_commander():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    out = f.issue_order(
        alliance_id="alpha", commander_id="bob",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    assert out.accepted is False


def test_issue_order_unknown_alliance():
    f = FieldCommanderRole()
    out = f.issue_order(
        alliance_id="ghost", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    assert out.accepted is False


def test_issue_order_cooldown():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    blocked = f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.RUSH, now_seconds=20,
    )
    assert blocked.accepted is False
    later = f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.RUSH,
        now_seconds=10 + ORDER_COOLDOWN_SECONDS + 1,
    )
    assert later.accepted is True


def test_active_order_during_window():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    out = f.active_order(alliance_id="alpha", now_seconds=15)
    assert out == FormationOrder.TURTLE


def test_active_order_expires():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    out = f.active_order(
        alliance_id="alpha",
        now_seconds=10 + ORDER_DURATION_SECONDS + 1,
    )
    assert out is None


def test_turtle_modifiers():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.TURTLE, now_seconds=10,
    )
    m = f.modifiers(alliance_id="alpha", now_seconds=15)
    assert m.damage_taken_pct == 70
    assert m.movement_pct == 50


def test_rush_modifiers():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.RUSH, now_seconds=10,
    )
    m = f.modifiers(alliance_id="alpha", now_seconds=15)
    assert m.damage_out_pct == 120
    assert m.healing_recv_pct == 50


def test_hold_modifiers_and_blocks_chase():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.HOLD, now_seconds=10,
    )
    m = f.modifiers(alliance_id="alpha", now_seconds=15)
    assert m.threat_pct == 125
    blocked = f.blocked_actions(
        alliance_id="alpha", now_seconds=15,
    )
    assert "chase" in blocked


def test_regroup_blocks_damage_spell():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.REGROUP, now_seconds=10,
    )
    blocked = f.blocked_actions(
        alliance_id="alpha", now_seconds=15,
    )
    assert "damage_spell" in blocked


def test_scatter_blocks_synergy():
    f = FieldCommanderRole()
    f.designate(alliance_id="alpha", commander_id="alice")
    f.issue_order(
        alliance_id="alpha", commander_id="alice",
        order=FormationOrder.SCATTER, now_seconds=10,
    )
    blocked = f.blocked_actions(
        alliance_id="alpha", now_seconds=15,
    )
    assert "synergy_ability" in blocked


def test_no_active_order_default_modifiers():
    f = FieldCommanderRole()
    m = f.modifiers(alliance_id="alpha", now_seconds=15)
    assert m.damage_out_pct == 100
    assert f.blocked_actions(
        alliance_id="alpha", now_seconds=15,
    ) == ()


def test_unknown_alliance_safe():
    f = FieldCommanderRole()
    assert f.commander(alliance_id="ghost") is None
    assert f.active_order(
        alliance_id="ghost", now_seconds=0,
    ) is None


def test_six_distinct_orders():
    assert len(list(FormationOrder)) == 6
