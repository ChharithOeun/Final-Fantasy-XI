"""Guild hall — physical buildings owned by linkshells.

Beyond the abstract linkshell membership, an established
LS can purchase or build a GUILD HALL — a physical space
in a city, decorated and configured by the LS leadership.
A hall has:
    hall_id
    owning_ls_id
    zone_id          city zone the hall is located in
    name             display name
    tier             SMALL / MEDIUM / LARGE / GRAND
    rooms            list of installed RoomKind
    purchased_day
    upkeep_due_day   the next day rent is due

Tiers determine room slot count:
    SMALL   3 rooms (basic LS — meeting hall + 2 spare)
    MEDIUM  6 rooms
    LARGE   10 rooms
    GRAND   16 rooms (multi-floor, requires a server-
                      first or major fame achievement)

Room kinds:
    MEETING_HALL     the main gathering room (required)
    TREASURY_VAULT   unlocks guild_treasury physical
                     access
    TROPHY_ROOM      displays guild's defeated NM heads
    LIBRARY          reading room with LS-tied books
    DUEL_PIT         small arena for in-LS duels
    KITCHEN          cooking buffs for members
    BARRACKS         fast travel hub for members
    ARMORY           shared LS-tier equipment cache
    SHRINE           provides daily LS-blessing buff
    GREENHOUSE       LS-tier mog_garden plots

Upkeep: paid weekly (default 7 game-days). If unpaid for
14 days the hall enters DELINQUENT and rooms lock down;
30 days unpaid -> hall reverts to vacant.

Public surface
--------------
    Tier enum
    RoomKind enum
    HallStatus enum
    GuildHall dataclass (frozen)
    GuildHallSystem
        .purchase(ls_id, zone_id, name, tier, day) -> Optional[str]
        .install_room(hall_id, room_kind) -> bool
        .pay_upkeep(hall_id, gil_amount, now_day) -> bool
        .tick(now_day) -> list[(hall_id, HallStatus)]
        .hall_for_ls(ls_id) -> Optional[GuildHall]
        .rooms_in(hall_id) -> list[RoomKind]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_UPKEEP_INTERVAL_DAYS = 7
_DELINQUENT_GRACE_DAYS = 14
_FORFEIT_AFTER_DAYS = 30
_TIER_PURCHASE_GIL = {
    "small": 100_000,
    "medium": 500_000,
    "large": 2_000_000,
    "grand": 10_000_000,
}
_TIER_ROOM_SLOTS = {
    "small": 3,
    "medium": 6,
    "large": 10,
    "grand": 16,
}
_TIER_UPKEEP_GIL = {
    "small": 5_000,
    "medium": 25_000,
    "large": 100_000,
    "grand": 500_000,
}


class Tier(str, enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    GRAND = "grand"


class RoomKind(str, enum.Enum):
    MEETING_HALL = "meeting_hall"
    TREASURY_VAULT = "treasury_vault"
    TROPHY_ROOM = "trophy_room"
    LIBRARY = "library"
    DUEL_PIT = "duel_pit"
    KITCHEN = "kitchen"
    BARRACKS = "barracks"
    ARMORY = "armory"
    SHRINE = "shrine"
    GREENHOUSE = "greenhouse"


class HallStatus(str, enum.Enum):
    ACTIVE = "active"
    DELINQUENT = "delinquent"
    VACANT = "vacant"


@dataclasses.dataclass(frozen=True)
class GuildHall:
    hall_id: str
    owning_ls_id: str
    zone_id: str
    name: str
    tier: Tier
    rooms: tuple[RoomKind, ...]
    purchased_day: int
    upkeep_due_day: int
    status: HallStatus


@dataclasses.dataclass
class _Hall:
    spec: GuildHall


@dataclasses.dataclass
class GuildHallSystem:
    _halls: dict[str, _Hall] = dataclasses.field(
        default_factory=dict,
    )
    _ls_to_hall: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def purchase(
        self, *, ls_id: str, zone_id: str, name: str,
        tier: Tier, day: int,
    ) -> t.Optional[str]:
        if not ls_id or not zone_id or not name:
            return None
        if day < 0:
            return None
        if ls_id in self._ls_to_hall:
            return None
        hall_id = f"hall_{self._next_id}"
        self._next_id += 1
        # MEETING_HALL is auto-installed
        spec = GuildHall(
            hall_id=hall_id, owning_ls_id=ls_id,
            zone_id=zone_id, name=name, tier=tier,
            rooms=(RoomKind.MEETING_HALL,),
            purchased_day=day,
            upkeep_due_day=day + _UPKEEP_INTERVAL_DAYS,
            status=HallStatus.ACTIVE,
        )
        self._halls[hall_id] = _Hall(spec=spec)
        self._ls_to_hall[ls_id] = hall_id
        return hall_id

    def install_room(
        self, *, hall_id: str, room_kind: RoomKind,
    ) -> bool:
        if hall_id not in self._halls:
            return False
        st = self._halls[hall_id]
        if st.spec.status != HallStatus.ACTIVE:
            return False
        if room_kind in st.spec.rooms:
            return False
        slot_cap = _TIER_ROOM_SLOTS[st.spec.tier.value]
        if len(st.spec.rooms) >= slot_cap:
            return False
        new_rooms = st.spec.rooms + (room_kind,)
        st.spec = dataclasses.replace(
            st.spec, rooms=new_rooms,
        )
        return True

    def pay_upkeep(
        self, *, hall_id: str, gil_paid: int,
        now_day: int,
    ) -> bool:
        if hall_id not in self._halls:
            return False
        if gil_paid <= 0:
            return False
        st = self._halls[hall_id]
        if st.spec.status == HallStatus.VACANT:
            return False
        required = _TIER_UPKEEP_GIL[st.spec.tier.value]
        if gil_paid < required:
            return False
        st.spec = dataclasses.replace(
            st.spec,
            upkeep_due_day=(
                now_day + _UPKEEP_INTERVAL_DAYS
            ),
            status=HallStatus.ACTIVE,
        )
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, HallStatus]]:
        changes: list[tuple[str, HallStatus]] = []
        for hall_id, st in list(self._halls.items()):
            if st.spec.status == HallStatus.VACANT:
                continue
            days_overdue = now_day - st.spec.upkeep_due_day
            new_status = st.spec.status
            if days_overdue >= _FORFEIT_AFTER_DAYS:
                new_status = HallStatus.VACANT
            elif days_overdue >= _DELINQUENT_GRACE_DAYS:
                new_status = HallStatus.DELINQUENT
            if new_status != st.spec.status:
                st.spec = dataclasses.replace(
                    st.spec, status=new_status,
                )
                changes.append((hall_id, new_status))
                # Forfeit clears LS ownership
                if new_status == HallStatus.VACANT:
                    self._ls_to_hall.pop(
                        st.spec.owning_ls_id, None,
                    )
        return changes

    def hall_for_ls(
        self, *, ls_id: str,
    ) -> t.Optional[GuildHall]:
        if ls_id not in self._ls_to_hall:
            return None
        hall_id = self._ls_to_hall[ls_id]
        return self._halls[hall_id].spec

    def rooms_in(
        self, *, hall_id: str,
    ) -> list[RoomKind]:
        if hall_id not in self._halls:
            return []
        return list(self._halls[hall_id].spec.rooms)

    def hall(
        self, *, hall_id: str,
    ) -> t.Optional[GuildHall]:
        if hall_id not in self._halls:
            return None
        return self._halls[hall_id].spec


__all__ = [
    "Tier", "RoomKind", "HallStatus", "GuildHall",
    "GuildHallSystem",
]
