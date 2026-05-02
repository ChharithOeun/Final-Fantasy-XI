"""Inn system — rest at inn for HP/MP + Mog House home points.

Pay an inn-keeper, pick a tier, get full HP/MP and a Home Point
attune at that inn. Higher tier inns offer Mog House-equivalent
amenities. Conquest-tier owners get a discount in their nation's
inns.

Public surface
--------------
    InnTier enum (BASIC, COMFORT, MOG_HOUSE)
    InnSpec catalog
    rest_at_inn(player, inn, gil, controller_nation) -> RestResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class InnTier(str, enum.Enum):
    BASIC = "basic"          # bare rest; HP only
    COMFORT = "comfort"      # HP + MP
    MOG_HOUSE = "mog_house"  # HP + MP + storage access


@dataclasses.dataclass(frozen=True)
class InnSpec:
    inn_id: str
    name: str
    nation: str              # bastok / sandy / windy / neutral
    tier: InnTier
    base_gil_cost: int


INN_CATALOG: tuple[InnSpec, ...] = (
    InnSpec("bastok_metalworks_inn", "Iron Eatery",
            nation="bastok", tier=InnTier.COMFORT, base_gil_cost=80),
    InnSpec("south_sandoria_inn", "Phoenix Feather Inn",
            nation="sandy", tier=InnTier.COMFORT, base_gil_cost=80),
    InnSpec("windurst_walls_inn", "Saltwater Spire",
            nation="windy", tier=InnTier.COMFORT, base_gil_cost=80),
    InnSpec("selbina_inn", "Tavern of Selbina",
            nation="neutral", tier=InnTier.BASIC, base_gil_cost=40),
    InnSpec("mhaura_inn", "Tavern of Mhaura",
            nation="neutral", tier=InnTier.BASIC, base_gil_cost=40),
    InnSpec("bastok_mog_house", "Bastok Mog House",
            nation="bastok", tier=InnTier.MOG_HOUSE,
            base_gil_cost=0),
    InnSpec("sandy_mog_house", "San d'Oria Mog House",
            nation="sandy", tier=InnTier.MOG_HOUSE,
            base_gil_cost=0),
    InnSpec("windy_mog_house", "Windurst Mog House",
            nation="windy", tier=InnTier.MOG_HOUSE,
            base_gil_cost=0),
)

INN_BY_ID: dict[str, InnSpec] = {i.inn_id: i for i in INN_CATALOG}


@dataclasses.dataclass(frozen=True)
class RestResult:
    accepted: bool
    inn_id: str
    gil_charged: int = 0
    hp_restored: bool = False
    mp_restored: bool = False
    home_point_set: bool = False
    storage_accessible: bool = False
    reason: t.Optional[str] = None


# Conquest tier discount ramp.
def _gil_with_discount(
    base_gil: int, *,
    inn_nation: str,
    nation_conquest_tier: int,
) -> int:
    """0..3 conquest tier shaves 0/10/20/30% off base_gil."""
    if inn_nation == "neutral":
        return base_gil
    tier = max(0, min(3, nation_conquest_tier))
    discount = 0.10 * tier
    return int(base_gil * (1.0 - discount))


def rest_at_inn(
    *,
    inn_id: str,
    player_gil: int,
    player_nation: str,
    nation_conquest_tier: int = 0,
) -> RestResult:
    """Rest at an inn. Returns the outcome.

    Mog House inns are home-only, free, and require player to be in
    their own nation.
    """
    inn = INN_BY_ID.get(inn_id)
    if inn is None:
        return RestResult(False, inn_id, reason="unknown inn")
    if inn.tier == InnTier.MOG_HOUSE:
        if inn.nation != player_nation:
            return RestResult(
                False, inn_id,
                reason="mog house only in own nation",
            )
        return RestResult(
            accepted=True, inn_id=inn_id,
            hp_restored=True, mp_restored=True,
            home_point_set=True, storage_accessible=True,
        )
    cost = _gil_with_discount(
        inn.base_gil_cost,
        inn_nation=inn.nation,
        nation_conquest_tier=nation_conquest_tier,
    )
    if player_gil < cost:
        return RestResult(
            False, inn_id,
            reason=f"insufficient gil (need {cost})",
        )
    return RestResult(
        accepted=True, inn_id=inn_id,
        gil_charged=cost,
        hp_restored=True,
        mp_restored=(inn.tier != InnTier.BASIC),
        home_point_set=True,
        storage_accessible=False,
    )


__all__ = [
    "InnTier", "InnSpec",
    "INN_CATALOG", "INN_BY_ID",
    "RestResult", "rest_at_inn",
]
