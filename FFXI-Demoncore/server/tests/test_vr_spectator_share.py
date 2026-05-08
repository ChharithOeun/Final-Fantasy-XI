"""Tests for vr_spectator_share."""
from __future__ import annotations

from server.vr_spectator_share import (
    ShareMode, VrSpectatorShare,
)


def test_start_share_happy():
    s = VrSpectatorShare()
    assert s.start_share(
        host_id="bob", mode=ShareMode.SMOOTH,
    ) is True


def test_start_share_blank_host_blocked():
    s = VrSpectatorShare()
    assert s.start_share(
        host_id="", mode=ShareMode.POV,
    ) is False


def test_start_share_dup_host_blocked():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.start_share(
        host_id="bob", mode=ShareMode.SMOOTH,
    ) is False


def test_start_share_negative_delay_blocked():
    s = VrSpectatorShare()
    assert s.start_share(
        host_id="bob", mode=ShareMode.POV,
        delay_seconds=-1,
    ) is False


def test_start_share_huge_delay_blocked():
    s = VrSpectatorShare()
    assert s.start_share(
        host_id="bob", mode=ShareMode.POV,
        delay_seconds=999,
    ) is False


def test_stop_share():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.stop_share(host_id="bob") is True
    assert s.active_hosts() == []


def test_stop_share_unknown():
    s = VrSpectatorShare()
    assert s.stop_share(host_id="ghost") is False


def test_add_viewer():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.add_viewer(
        host_id="bob", viewer_id="cara",
    ) is True
    assert s.can_view(
        host_id="bob", viewer_id="cara",
    ) is True


def test_add_viewer_unknown_host_blocked():
    s = VrSpectatorShare()
    assert s.add_viewer(
        host_id="ghost", viewer_id="cara",
    ) is False


def test_add_viewer_self_blocked():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.add_viewer(
        host_id="bob", viewer_id="bob",
    ) is False


def test_add_viewer_dup_blocked():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    s.add_viewer(host_id="bob", viewer_id="cara")
    assert s.add_viewer(
        host_id="bob", viewer_id="cara",
    ) is False


def test_remove_viewer():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    s.add_viewer(host_id="bob", viewer_id="cara")
    assert s.remove_viewer(
        host_id="bob", viewer_id="cara",
    ) is True
    assert s.can_view(
        host_id="bob", viewer_id="cara",
    ) is False


def test_remove_viewer_unknown_blocked():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.remove_viewer(
        host_id="bob", viewer_id="ghost",
    ) is False


def test_change_mode():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    s.add_viewer(host_id="bob", viewer_id="cara")
    assert s.change_mode(
        host_id="bob", mode=ShareMode.SMOOTH,
    ) is True
    ticket = s.ticket(host_id="bob", viewer_id="cara")
    assert ticket.mode == ShareMode.SMOOTH


def test_change_mode_same_mode_no_op():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.change_mode(
        host_id="bob", mode=ShareMode.POV,
    ) is False


def test_ticket_carries_delay():
    s = VrSpectatorShare()
    s.start_share(
        host_id="bob", mode=ShareMode.SMOOTH,
        delay_seconds=10,
    )
    s.add_viewer(host_id="bob", viewer_id="cara")
    t = s.ticket(host_id="bob", viewer_id="cara")
    assert t is not None
    assert t.delay_seconds == 10


def test_ticket_no_subscription_returns_none():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    assert s.ticket(
        host_id="bob", viewer_id="cara",
    ) is None


def test_active_hosts_listing():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    s.start_share(host_id="anya", mode=ShareMode.SMOOTH)
    assert s.active_hosts() == ["anya", "bob"]


def test_viewers_of_listing():
    s = VrSpectatorShare()
    s.start_share(host_id="bob", mode=ShareMode.POV)
    s.add_viewer(host_id="bob", viewer_id="cara")
    s.add_viewer(host_id="bob", viewer_id="anya")
    assert s.viewers_of(host_id="bob") == ["anya", "cara"]


def test_viewers_of_unknown_host():
    s = VrSpectatorShare()
    assert s.viewers_of(host_id="ghost") == []


def test_two_share_modes():
    assert len(list(ShareMode)) == 2
