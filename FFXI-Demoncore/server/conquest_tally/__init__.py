"""Conquest tally — nation point ranking by zone control.

Players earn nation points by killing mobs in zones; the points
roll up to nation totals tracked per zone. Each weekly tally tick,
the dominant nation per zone is determined by point share, and a
global ranking emerges (1st/2nd/3rd place).

Public surface
--------------
    Nation                 enum bastok/sandy/windy
    ZoneConquest           per-zone point bucket
    ConquestBoard          all-zones aggregate
        .add_points(zone, nation, amount)
        .controller(zone)
        .weekly_tally()
        .rankings()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Nation(str, enum.Enum):
    BASTOK = "bastok"
    SANDY = "sandy"
    WINDY = "windy"


@dataclasses.dataclass
class ZoneConquest:
    zone_id: str
    points: dict[Nation, int] = dataclasses.field(
        default_factory=lambda: {n: 0 for n in Nation},
    )

    def total(self) -> int:
        return sum(self.points.values())

    def leader(self) -> t.Optional[Nation]:
        if self.total() == 0:
            return None
        # Highest score wins; tie -> stable order in Nation enum.
        best_score = max(self.points.values())
        for n in Nation:
            if self.points[n] == best_score:
                return n
        return None


@dataclasses.dataclass
class TallySnapshot:
    """Result of a weekly tally."""
    week_number: int
    zone_controllers: dict[str, t.Optional[Nation]]
    nation_zone_count: dict[Nation, int]


@dataclasses.dataclass
class NationRanking:
    nation: Nation
    rank: int                # 1, 2, 3
    zones_controlled: int


@dataclasses.dataclass
class ConquestBoard:
    _zones: dict[str, ZoneConquest] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    _last_week: int = 0

    def add_points(
        self, *,
        zone_id: str, nation: Nation, amount: int,
    ) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        zone = self._zones.setdefault(
            zone_id, ZoneConquest(zone_id=zone_id),
        )
        zone.points[nation] += amount

    def controller(self, zone_id: str) -> t.Optional[Nation]:
        zone = self._zones.get(zone_id)
        if zone is None:
            return None
        return zone.leader()

    def points_in(
        self, zone_id: str, nation: Nation,
    ) -> int:
        zone = self._zones.get(zone_id)
        if zone is None:
            return 0
        return zone.points[nation]

    def weekly_tally(self, *, week_number: int) -> TallySnapshot:
        if week_number <= self._last_week:
            raise ValueError(
                f"week_number {week_number} must be > "
                f"{self._last_week}",
            )
        self._last_week = week_number
        zone_controllers: dict[str, t.Optional[Nation]] = {}
        nation_count: dict[Nation, int] = {n: 0 for n in Nation}
        for zid, zone in self._zones.items():
            leader = zone.leader()
            zone_controllers[zid] = leader
            if leader is not None:
                nation_count[leader] += 1
        return TallySnapshot(
            week_number=week_number,
            zone_controllers=zone_controllers,
            nation_zone_count=nation_count,
        )

    def rankings(self) -> tuple[NationRanking, ...]:
        """1st/2nd/3rd by zones controlled. Stable on ties."""
        counts = {n: 0 for n in Nation}
        for zone in self._zones.values():
            leader = zone.leader()
            if leader is not None:
                counts[leader] += 1
        ordered = sorted(
            counts.items(),
            key=lambda kv: (-kv[1], list(Nation).index(kv[0])),
        )
        return tuple(
            NationRanking(
                nation=nation, rank=i + 1, zones_controlled=count,
            )
            for i, (nation, count) in enumerate(ordered)
        )

    def reset_zone(self, zone_id: str) -> None:
        """Wipe all points in a zone (e.g. after siege resolution)."""
        if zone_id in self._zones:
            self._zones[zone_id] = ZoneConquest(zone_id=zone_id)


__all__ = [
    "Nation", "ZoneConquest",
    "TallySnapshot", "NationRanking",
    "ConquestBoard",
]
