"""City hospital — paid healing services + recovery beds.

Each capital city operates a HOSPITAL (or "infirmary"
in beastman cities). Players who don't have a WHM in
party — or who've blown through their /heal regen budget
— can pay an NPC chirurgeon for HEALING (HP restore),
status removal, or a RECOVERY BED slot.

A recovery bed is the heavy option: lie down, pay a
flat gil rate per game-hour, and accumulate full HP +
MP + status cleanse over a real cooldown. Beds are
rate-limited per hospital — a player can't squat
indefinitely.

Service kinds:
    HP_RESTORE        flat-rate HP restore
    MP_RESTORE        flat-rate MP restore
    REMOVE_POISON     remove poison
    REMOVE_PARALYZE   remove paralyze
    REMOVE_DISEASE    remove disease
    REMOVE_CURSE      remove curse (the costly one)
    RAISE_AT_DESK     low-tier raise (no XP loss
                      reduction, but instant)
    BED_REST          enter a recovery bed

Public surface
--------------
    ServiceKind enum
    BedState enum
    HospitalService dataclass (frozen)
    BedOccupancy dataclass (frozen)
    CityHospitalSystem
        .open_hospital(hospital_id, city,
                       bed_capacity) -> bool
        .set_price(hospital_id, kind, gil) -> bool
        .render_service(hospital_id, kind, player_id,
                        gil_paid) -> tuple[bool, str]
        .request_bed(hospital_id, player_id,
                     gil_paid_per_hour, hours,
                     now_hour) -> Optional[str]
        .release_bed(occupancy_id, now_hour) -> bool
        .occupied_count(hospital_id) -> int
        .occupancies(hospital_id) -> list[BedOccupancy]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ServiceKind(str, enum.Enum):
    HP_RESTORE = "hp_restore"
    MP_RESTORE = "mp_restore"
    REMOVE_POISON = "remove_poison"
    REMOVE_PARALYZE = "remove_paralyze"
    REMOVE_DISEASE = "remove_disease"
    REMOVE_CURSE = "remove_curse"
    RAISE_AT_DESK = "raise_at_desk"
    BED_REST = "bed_rest"


class BedState(str, enum.Enum):
    OCCUPIED = "occupied"
    RELEASED = "released"


@dataclasses.dataclass(frozen=True)
class HospitalService:
    hospital_id: str
    kind: ServiceKind
    price_gil: int


@dataclasses.dataclass(frozen=True)
class BedOccupancy:
    occupancy_id: str
    hospital_id: str
    player_id: str
    gil_per_hour: int
    booked_hours: int
    started_hour: int
    ended_hour: t.Optional[int]
    state: BedState


@dataclasses.dataclass
class _Hosp:
    hospital_id: str
    city: str
    bed_capacity: int
    prices: dict[ServiceKind, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class CityHospitalSystem:
    _hosps: dict[str, _Hosp] = dataclasses.field(
        default_factory=dict,
    )
    _occupancies: dict[str, BedOccupancy] = (
        dataclasses.field(default_factory=dict)
    )
    _next_occ: int = 1

    def open_hospital(
        self, *, hospital_id: str, city: str,
        bed_capacity: int,
    ) -> bool:
        if not hospital_id or not city:
            return False
        if bed_capacity < 0:
            return False
        if hospital_id in self._hosps:
            return False
        self._hosps[hospital_id] = _Hosp(
            hospital_id=hospital_id, city=city,
            bed_capacity=bed_capacity,
        )
        return True

    def set_price(
        self, *, hospital_id: str, kind: ServiceKind,
        gil: int,
    ) -> bool:
        if hospital_id not in self._hosps:
            return False
        if gil < 0:
            return False
        self._hosps[hospital_id].prices[kind] = gil
        return True

    def render_service(
        self, *, hospital_id: str, kind: ServiceKind,
        player_id: str, gil_paid: int,
    ) -> tuple[bool, str]:
        if hospital_id not in self._hosps:
            return (False, "no_hospital")
        if not player_id:
            return (False, "bad_player")
        if kind == ServiceKind.BED_REST:
            return (False, "use_request_bed")
        h = self._hosps[hospital_id]
        if kind not in h.prices:
            return (False, "unpriced")
        if gil_paid < h.prices[kind]:
            return (False, "insufficient_gil")
        return (True, "ok")

    def request_bed(
        self, *, hospital_id: str, player_id: str,
        gil_paid_per_hour: int, hours: int,
        now_hour: int,
    ) -> t.Optional[str]:
        if hospital_id not in self._hosps:
            return None
        if not player_id:
            return None
        if hours <= 0 or now_hour < 0:
            return None
        if gil_paid_per_hour < 0:
            return None
        h = self._hosps[hospital_id]
        bed_price = h.prices.get(ServiceKind.BED_REST, 0)
        if gil_paid_per_hour < bed_price:
            return None
        # Capacity check
        if self.occupied_count(
            hospital_id=hospital_id,
        ) >= h.bed_capacity:
            return None
        oid = f"bed_{self._next_occ}"
        self._next_occ += 1
        self._occupancies[oid] = BedOccupancy(
            occupancy_id=oid, hospital_id=hospital_id,
            player_id=player_id,
            gil_per_hour=gil_paid_per_hour,
            booked_hours=hours, started_hour=now_hour,
            ended_hour=None,
            state=BedState.OCCUPIED,
        )
        return oid

    def release_bed(
        self, *, occupancy_id: str, now_hour: int,
    ) -> bool:
        if occupancy_id not in self._occupancies:
            return False
        occ = self._occupancies[occupancy_id]
        if occ.state != BedState.OCCUPIED:
            return False
        if now_hour < occ.started_hour:
            return False
        self._occupancies[occupancy_id] = (
            dataclasses.replace(
                occ, ended_hour=now_hour,
                state=BedState.RELEASED,
            )
        )
        return True

    def occupied_count(
        self, *, hospital_id: str,
    ) -> int:
        return sum(
            1 for o in self._occupancies.values()
            if (o.hospital_id == hospital_id
                and o.state == BedState.OCCUPIED)
        )

    def occupancies(
        self, *, hospital_id: str,
    ) -> list[BedOccupancy]:
        return [
            o for o in self._occupancies.values()
            if o.hospital_id == hospital_id
        ]


__all__ = [
    "ServiceKind", "BedState", "HospitalService",
    "BedOccupancy", "CityHospitalSystem",
]
