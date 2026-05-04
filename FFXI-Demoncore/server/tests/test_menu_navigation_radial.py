"""Tests for the radial menu navigator."""
from __future__ import annotations

from server.menu_navigation_radial import (
    MenuItem,
    MenuNavigationRadial,
    NavInput,
)


def _seed_three_menus(m: MenuNavigationRadial):
    m.define_menu(
        menu_id="root", label="Main",
        items=(
            MenuItem(
                item_id="combat", label="Combat",
                drill_into="combat_menu",
            ),
            MenuItem(
                item_id="magic", label="Magic",
                drill_into="magic_menu",
            ),
            MenuItem(
                item_id="status", label="Status",
                payload="open_status",
            ),
        ),
    )
    m.define_menu(
        menu_id="combat_menu", label="Combat",
        items=(
            MenuItem(item_id="attack", label="Attack"),
            MenuItem(
                item_id="weaponskill", label="Weapon Skill",
            ),
        ),
    )
    m.define_menu(
        menu_id="magic_menu", label="Magic",
        items=(
            MenuItem(item_id="spell_a", label="Cure"),
            MenuItem(
                item_id="spell_b", label="Banish",
                enabled=False,
            ),
        ),
    )


def test_define_menu():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    assert m.total_menus() == 3


def test_define_no_items_rejected():
    m = MenuNavigationRadial()
    res = m.define_menu(
        menu_id="empty", label="Empty", items=(),
    )
    assert res is None


def test_double_define_rejected():
    m = MenuNavigationRadial()
    m.define_menu(
        menu_id="x", label="x",
        items=(
            MenuItem(item_id="a", label="A"),
        ),
    )
    res = m.define_menu(
        menu_id="x", label="y",
        items=(
            MenuItem(item_id="a", label="A"),
        ),
    )
    assert res is None


def test_open_root_unknown_returns_false():
    m = MenuNavigationRadial()
    assert not m.open_root(
        player_id="alice", menu_id="ghost",
    )


def test_open_root_succeeds():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    assert m.open_root(
        player_id="alice", menu_id="root",
    )
    node = m.current_node(player_id="alice")
    assert node.menu_id == "root"


def test_input_next_cycles():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.input(player_id="alice", action=NavInput.NEXT)
    st = m.state_for("alice")
    assert st.highlighted_index == 1


def test_input_prev_wraps():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.input(player_id="alice", action=NavInput.PREV)
    st = m.state_for("alice")
    assert st.highlighted_index == 2


def test_confirm_drills_into_child():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    res = m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )
    assert res.drilled_into
    node = m.current_node(player_id="alice")
    assert node.menu_id == "combat_menu"


def test_confirm_leaf_item_returns_payload():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.point_to(player_id="alice", slot_index=2)   # Status
    res = m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )
    assert res.accepted
    assert not res.drilled_into
    assert res.item.payload == "open_status"


def test_confirm_disabled_item_rejected():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="magic_menu")
    m.point_to(player_id="alice", slot_index=1)   # Banish
    res = m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )
    assert not res.accepted
    assert "disabled" in res.note


def test_back_pops_stack():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )   # drill into combat
    res = m.input(
        player_id="alice", action=NavInput.BACK,
    )
    assert res.accepted
    assert (
        m.current_node(player_id="alice").menu_id == "root"
    )


def test_back_at_root_rejected():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    res = m.input(
        player_id="alice", action=NavInput.BACK,
    )
    assert not res.accepted


def test_close_clears_state():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.input(player_id="alice", action=NavInput.CLOSE)
    assert m.state_for("alice") is None


def test_input_no_state_returns_none():
    m = MenuNavigationRadial()
    res = m.input(
        player_id="alice", action=NavInput.NEXT,
    )
    assert res is None


def test_point_to_invalid_slot():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    assert not m.point_to(
        player_id="alice", slot_index=99,
    )


def test_point_to_no_state():
    m = MenuNavigationRadial()
    assert not m.point_to(
        player_id="alice", slot_index=0,
    )


def test_drill_into_undefined_target():
    m = MenuNavigationRadial()
    m.define_menu(
        menu_id="root", label="r",
        items=(
            MenuItem(
                item_id="x", label="X",
                drill_into="ghost_menu",
            ),
        ),
    )
    m.open_root(player_id="alice", menu_id="root")
    res = m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )
    assert not res.accepted
    assert "drill target" in res.note


def test_back_resets_highlight():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.input(
        player_id="alice", action=NavInput.CONFIRM,
    )   # drill into combat
    m.input(
        player_id="alice", action=NavInput.NEXT,
    )
    m.input(
        player_id="alice", action=NavInput.BACK,
    )
    assert m.state_for("alice").highlighted_index == 0


def test_per_player_isolation():
    m = MenuNavigationRadial()
    _seed_three_menus(m)
    m.open_root(player_id="alice", menu_id="root")
    m.open_root(player_id="bob", menu_id="combat_menu")
    assert (
        m.current_node(player_id="alice").menu_id != (
            m.current_node(player_id="bob").menu_id
        )
    )
