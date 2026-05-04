"""Tests for the UI context menu."""
from __future__ import annotations

from server.ui_context_menu import (
    ContextActionKind,
    DEFAULT_BAZAAR_TAX_PCT,
    UIContextMenu,
)


def test_default_menu_has_all_actions():
    m = UIContextMenu()
    menu = m.build_menu(
        viewer_id="alice", target_id="bob",
        has_last_tell=True,
        target_has_bazaar=True,
        friends_already=False,
    )
    kinds = {a.kind for a in menu.actions}
    assert ContextActionKind.TELL in kinds
    assert ContextActionKind.REPLY in kinds
    assert ContextActionKind.CHECK in kinds
    assert ContextActionKind.BROWSE_WARES in kinds
    assert ContextActionKind.BLOCK in kinds
    assert ContextActionKind.REPORT in kinds


def test_reply_disabled_without_last_tell():
    m = UIContextMenu()
    menu = m.build_menu(
        viewer_id="a", target_id="b",
        has_last_tell=False,
    )
    reply = next(
        a for a in menu.actions
        if a.kind == ContextActionKind.REPLY
    )
    assert not reply.enabled


def test_browse_wares_disabled_without_bazaar():
    m = UIContextMenu()
    menu = m.build_menu(
        viewer_id="a", target_id="b",
        target_has_bazaar=False,
    )
    bw = next(
        a for a in menu.actions
        if a.kind == ContextActionKind.BROWSE_WARES
    )
    assert not bw.enabled


def test_browse_wares_note_announces_tax():
    m = UIContextMenu(bazaar_tax_pct=10)
    menu = m.build_menu(
        viewer_id="a", target_id="b",
        target_has_bazaar=True,
    )
    bw = next(
        a for a in menu.actions
        if a.kind == ContextActionKind.BROWSE_WARES
    )
    assert "10%" in bw.note


def test_add_friend_disabled_when_already_friends():
    m = UIContextMenu()
    menu = m.build_menu(
        viewer_id="a", target_id="b",
        friends_already=True,
    )
    af = next(
        a for a in menu.actions
        if a.kind == ContextActionKind.ADD_FRIEND
    )
    assert not af.enabled


def test_block_then_menu_pruned():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    menu = m.build_menu(
        viewer_id="a", target_id="b",
    )
    assert menu.target_blocked
    kinds = {x.kind for x in menu.actions}
    assert kinds == {
        ContextActionKind.UNBLOCK,
        ContextActionKind.REPORT,
    }


def test_block_self_rejected():
    m = UIContextMenu()
    assert not m.block(
        viewer_id="alice", target_id="alice",
    )


def test_double_block_returns_false():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    assert not m.block(viewer_id="a", target_id="b")


def test_unblock_unblocks():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    assert m.unblock(viewer_id="a", target_id="b")
    assert not m.is_blocked(
        viewer_id="a", target_id="b",
    )


def test_unblock_not_blocked_returns_false():
    m = UIContextMenu()
    assert not m.unblock(
        viewer_id="a", target_id="b",
    )


def test_report_increments_count():
    m = UIContextMenu()
    n1 = m.report(viewer_id="a", target_id="b")
    n2 = m.report(viewer_id="a", target_id="b")
    assert n1 == 1 and n2 == 2


def test_report_self_returns_zero():
    m = UIContextMenu()
    assert m.report(
        viewer_id="alice", target_id="alice",
    ) == 0


def test_invoke_browse_wares_returns_tax():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.BROWSE_WARES,
        target_has_bazaar=True,
    )
    assert res.accepted
    assert res.bazaar_result is not None
    assert res.bazaar_result.tax_pct == DEFAULT_BAZAAR_TAX_PCT


def test_invoke_browse_wares_no_bazaar_rejected():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.BROWSE_WARES,
        target_has_bazaar=False,
    )
    assert not res.accepted


def test_invoke_browse_wares_blocked_target_rejected():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.BROWSE_WARES,
        target_has_bazaar=True,
    )
    assert not res.accepted


def test_invoke_block_returns_ok():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.BLOCK,
    )
    assert res.accepted
    assert m.is_blocked(viewer_id="a", target_id="b")


def test_invoke_block_already_blocked_rejected():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.BLOCK,
    )
    assert not res.accepted


def test_invoke_unblock_works():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.UNBLOCK,
    )
    assert res.accepted


def test_invoke_report_logs():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.REPORT,
    )
    assert res.accepted
    assert "report 1" in res.note


def test_invoke_self_block_rejected():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="alice", target_id="alice",
        action=ContextActionKind.BLOCK,
    )
    assert not res.accepted


def test_invoke_check_passthrough_succeeds():
    m = UIContextMenu()
    res = m.invoke(
        viewer_id="a", target_id="b",
        action=ContextActionKind.CHECK,
    )
    assert res.accepted


def test_total_block_targets():
    m = UIContextMenu()
    m.block(viewer_id="a", target_id="b")
    m.block(viewer_id="a", target_id="c")
    assert m.total_block_targets(viewer_id="a") == 2
