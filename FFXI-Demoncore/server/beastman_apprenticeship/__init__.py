"""Beastman apprenticeship — race-master training relationship.

Each beastman city hosts a roster of MASTER NPCs, each
specializing in a specific TRADE (combat-arts, magic-arts,
craft, lore). A player BINDS to a single master at a time;
training sessions deliver a TRADE_XP yield calibrated to the
master's tier (NOVICE_MASTER / SEASONED_MASTER / GRAND_MASTER)
and the player's current trade level.

Higher-tier masters teach faster but require a HIGHER PLAYER
LEVEL (NOVICE_MASTER 1+, SEASONED 30+, GRAND 75+) and pay a
SESSION_GIL fee.

Public surface
--------------
    Trade enum     COMBAT_ARTS / MAGIC_ARTS / CRAFT / LORE
    MasterTier enum
    Master dataclass
    BeastmanApprenticeship
        .register_master(master_id, trade, tier, base_xp,
                         session_gil_cost)
        .bind(player_id, master_id, player_level)
        .train(player_id, gil_held, trade_level)
        .unbind(player_id)
        .bound_master(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Trade(str, enum.Enum):
    COMBAT_ARTS = "combat_arts"
    MAGIC_ARTS = "magic_arts"
    CRAFT = "craft"
    LORE = "lore"


class MasterTier(str, enum.Enum):
    NOVICE_MASTER = "novice_master"
    SEASONED_MASTER = "seasoned_master"
    GRAND_MASTER = "grand_master"


_TIER_LEVEL_FLOOR: dict[MasterTier, int] = {
    MasterTier.NOVICE_MASTER: 1,
    MasterTier.SEASONED_MASTER: 30,
    MasterTier.GRAND_MASTER: 75,
}


_TIER_XP_MULTIPLIER: dict[MasterTier, int] = {
    MasterTier.NOVICE_MASTER: 100,
    MasterTier.SEASONED_MASTER: 200,
    MasterTier.GRAND_MASTER: 350,
}


@dataclasses.dataclass(frozen=True)
class Master:
    master_id: str
    trade: Trade
    tier: MasterTier
    base_xp: int
    session_gil_cost: int


@dataclasses.dataclass(frozen=True)
class BindResult:
    accepted: bool
    master_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TrainResult:
    accepted: bool
    master_id: str
    trade: Trade = Trade.LORE
    xp_awarded: int = 0
    gil_charged: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanApprenticeship:
    _masters: dict[str, Master] = dataclasses.field(default_factory=dict)
    _bound: dict[str, str] = dataclasses.field(default_factory=dict)

    def register_master(
        self, *, master_id: str,
        trade: Trade,
        tier: MasterTier,
        base_xp: int,
        session_gil_cost: int,
    ) -> t.Optional[Master]:
        if master_id in self._masters:
            return None
        if base_xp <= 0 or session_gil_cost < 0:
            return None
        m = Master(
            master_id=master_id,
            trade=trade, tier=tier,
            base_xp=base_xp,
            session_gil_cost=session_gil_cost,
        )
        self._masters[master_id] = m
        return m

    def bind(
        self, *, player_id: str,
        master_id: str,
        player_level: int,
    ) -> BindResult:
        m = self._masters.get(master_id)
        if m is None:
            return BindResult(
                False, master_id, reason="unknown master",
            )
        if player_level < _TIER_LEVEL_FLOOR[m.tier]:
            return BindResult(
                False, master_id, reason="player level too low",
            )
        if player_id in self._bound:
            return BindResult(
                False, master_id,
                reason="already bound to a master",
            )
        self._bound[player_id] = master_id
        return BindResult(accepted=True, master_id=master_id)

    def train(
        self, *, player_id: str,
        gil_held: int,
        trade_level: int,
    ) -> TrainResult:
        master_id = self._bound.get(player_id)
        if master_id is None:
            return TrainResult(
                False, "", reason="not bound",
            )
        if trade_level < 0:
            return TrainResult(
                False, master_id, reason="negative trade level",
            )
        m = self._masters[master_id]
        if gil_held < m.session_gil_cost:
            return TrainResult(
                False, master_id, reason="insufficient gil",
            )
        # XP scaled by tier multiplier (percent), softened by trade level
        # so high-trade players see diminishing returns
        xp_scaled = (m.base_xp * _TIER_XP_MULTIPLIER[m.tier]) // 100
        # Diminishment: every 10 trade levels reduces by 5%, floor 25%
        diminish_steps = trade_level // 10
        retain_pct = max(25, 100 - diminish_steps * 5)
        xp_awarded = (xp_scaled * retain_pct) // 100
        return TrainResult(
            accepted=True,
            master_id=master_id,
            trade=m.trade,
            xp_awarded=xp_awarded,
            gil_charged=m.session_gil_cost,
        )

    def unbind(
        self, *, player_id: str,
    ) -> bool:
        if player_id not in self._bound:
            return False
        del self._bound[player_id]
        return True

    def bound_master(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        return self._bound.get(player_id)

    def total_masters(self) -> int:
        return len(self._masters)


__all__ = [
    "Trade", "MasterTier",
    "Master", "BindResult", "TrainResult",
    "BeastmanApprenticeship",
]
