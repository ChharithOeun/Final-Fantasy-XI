"""Tests for guild_hall."""
from __future__ import annotations

from server.guild_hall import (
    GuildHallSystem, Tier, RoomKind, HallStatus,
)


def _purchase(s, **overrides):
    args = dict(
        ls_id="ls_alpha", zone_id="bastok_mines",
        name="Stoneforge Hall", tier=Tier.SMALL, day=10,
    )
    args.update(overrides)
    return s.purchase(**args)


def test_purchase_happy():
    s = GuildHallSystem()
    hid = _purchase(s)
    assert hid is not None


def test_purchase_blank_ls_blocked():
    s = GuildHallSystem()
    assert _purchase(s, ls_id="") is None


def test_purchase_blank_zone_blocked():
    s = GuildHallSystem()
    assert _purchase(s, zone_id="") is None


def test_purchase_blank_name_blocked():
    s = GuildHallSystem()
    assert _purchase(s, name="") is None


def test_purchase_negative_day_blocked():
    s = GuildHallSystem()
    assert _purchase(s, day=-1) is None


def test_purchase_dup_ls_blocked():
    s = GuildHallSystem()
    _purchase(s)
    assert _purchase(s) is None


def test_meeting_hall_auto_installed():
    s = GuildHallSystem()
    hid = _purchase(s)
    rooms = s.rooms_in(hall_id=hid)
    assert RoomKind.MEETING_HALL in rooms


def test_install_room_happy():
    s = GuildHallSystem()
    hid = _purchase(s)
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.LIBRARY,
    ) is True


def test_install_room_dup_blocked():
    s = GuildHallSystem()
    hid = _purchase(s)
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.MEETING_HALL,
    ) is False


def test_install_room_unknown_hall():
    s = GuildHallSystem()
    assert s.install_room(
        hall_id="ghost", room_kind=RoomKind.LIBRARY,
    ) is False


def test_small_tier_slot_cap():
    s = GuildHallSystem()
    hid = _purchase(s, tier=Tier.SMALL)
    # SMALL = 3 slots, MEETING_HALL pre-installed
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.LIBRARY,
    ) is True
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.KITCHEN,
    ) is True
    # Cap reached
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.SHRINE,
    ) is False


def test_grand_tier_slot_cap():
    s = GuildHallSystem()
    hid = _purchase(s, tier=Tier.GRAND)
    rooms = [
        RoomKind.TREASURY_VAULT, RoomKind.TROPHY_ROOM,
        RoomKind.LIBRARY, RoomKind.DUEL_PIT,
        RoomKind.KITCHEN, RoomKind.BARRACKS,
        RoomKind.ARMORY, RoomKind.SHRINE,
        RoomKind.GREENHOUSE,
    ]
    for r in rooms:
        assert s.install_room(
            hall_id=hid, room_kind=r,
        ) is True


def test_pay_upkeep_happy():
    s = GuildHallSystem()
    hid = _purchase(s, tier=Tier.SMALL, day=10)
    assert s.pay_upkeep(
        hall_id=hid, gil_paid=5_000, now_day=15,
    ) is True


def test_pay_upkeep_insufficient_blocked():
    s = GuildHallSystem()
    hid = _purchase(s, tier=Tier.SMALL)
    assert s.pay_upkeep(
        hall_id=hid, gil_paid=100, now_day=15,
    ) is False


def test_pay_upkeep_negative_blocked():
    s = GuildHallSystem()
    hid = _purchase(s)
    assert s.pay_upkeep(
        hall_id=hid, gil_paid=-1, now_day=15,
    ) is False


def test_pay_upkeep_unknown_hall():
    s = GuildHallSystem()
    assert s.pay_upkeep(
        hall_id="ghost", gil_paid=5_000, now_day=15,
    ) is False


def test_tick_to_delinquent():
    s = GuildHallSystem()
    hid = _purchase(s, day=0)
    # upkeep_due_day = 7; tick at day 21 -> 14 overdue -> delinquent
    changes = s.tick(now_day=21)
    assert (hid, HallStatus.DELINQUENT) in changes


def test_tick_to_vacant():
    s = GuildHallSystem()
    hid = _purchase(s, day=0)
    # upkeep_due_day = 7; tick at day 37 -> 30 overdue -> vacant
    changes = s.tick(now_day=37)
    assert (hid, HallStatus.VACANT) in changes


def test_vacant_clears_ls_lookup():
    s = GuildHallSystem()
    _purchase(s, ls_id="ls_alpha", day=0)
    s.tick(now_day=37)
    assert s.hall_for_ls(ls_id="ls_alpha") is None


def test_install_on_delinquent_blocked():
    s = GuildHallSystem()
    hid = _purchase(s, day=0)
    s.tick(now_day=21)
    assert s.install_room(
        hall_id=hid, room_kind=RoomKind.LIBRARY,
    ) is False


def test_pay_upkeep_revives_delinquent():
    s = GuildHallSystem()
    hid = _purchase(s, tier=Tier.SMALL, day=0)
    s.tick(now_day=21)
    s.pay_upkeep(
        hall_id=hid, gil_paid=5_000, now_day=21,
    )
    h = s.hall(hall_id=hid)
    assert h.status == HallStatus.ACTIVE


def test_pay_upkeep_vacant_blocked():
    s = GuildHallSystem()
    hid = _purchase(s, day=0)
    s.tick(now_day=37)
    assert s.pay_upkeep(
        hall_id=hid, gil_paid=10_000_000,
        now_day=40,
    ) is False


def test_hall_for_ls_happy():
    s = GuildHallSystem()
    hid = _purchase(s, ls_id="ls_alpha")
    h = s.hall_for_ls(ls_id="ls_alpha")
    assert h is not None and h.hall_id == hid


def test_hall_for_ls_unknown():
    s = GuildHallSystem()
    assert s.hall_for_ls(ls_id="nobody") is None


def test_rooms_in_unknown():
    s = GuildHallSystem()
    assert s.rooms_in(hall_id="ghost") == []


def test_hall_unknown():
    s = GuildHallSystem()
    assert s.hall(hall_id="ghost") is None


def test_enum_counts():
    assert len(list(Tier)) == 4
    assert len(list(RoomKind)) == 10
    assert len(list(HallStatus)) == 3
