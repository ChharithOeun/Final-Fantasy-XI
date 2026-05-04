"""Beastman war campaign — mass-combat campaign system.

The macro layer above individual raids and PvP. Hume nations
(San d'Oria, Bastok, Windurst, Adoulin, Tavnazia) and beastman
cities (Yagudo, Quadav, Lamia, Orc) wage CAMPAIGNS against each
other across CAMPAIGN ZONES (the contested borderlands).

Each ACTIVE FRONT tracks a hume side, a beastman side, and a
PUSH SCORE on a -100..+100 axis. Every combat contribution
(NPC kills, NM kills, fortification rubble, supply burns) shifts
the score; when the front hits ±100, that side wins the front
and the opposite side loses territory in their conquest tally.

A campaign also has a TICK system — every 60 minutes, AI factions
contribute a baseline push that simulates background NPC armies.

Public surface
--------------
    HumeNation enum
    BeastmanCity enum
    FrontKind enum
    ContributionKind enum
    Front dataclass
    ContributionResult / TickResult dataclasses
    BeastmanWarCampaign
        .open_front(front_id, hume_nation, beastman_city,
                    zone_id, kind)
        .contribute(player_id, front_id, kind, magnitude)
        .ai_tick(front_id, hume_baseline, beastman_baseline)
        .resolve_if_capped(front_id)
        .front_status(front_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HumeNation(str, enum.Enum):
    SAN_DORIA = "san_doria"
    BASTOK = "bastok"
    WINDURST = "windurst"
    ADOULIN = "adoulin"
    TAVNAZIA = "tavnazia"


class BeastmanCity(str, enum.Enum):
    OZTROJA = "oztroja"        # yagudo
    PALBOROUGH = "palborough"  # quadav
    HALVUNG = "halvung"        # orc
    ARRAPAGO = "arrapago"      # lamia


class FrontKind(str, enum.Enum):
    BORDER_SKIRMISH = "border_skirmish"
    SIEGE = "siege"
    NAVAL_BLOCKADE = "naval_blockade"
    HOLY_WAR = "holy_war"


class ContributionKind(str, enum.Enum):
    NPC_KILL = "npc_kill"
    NM_KILL = "nm_kill"
    FORTIFICATION_RUBBLE = "fortification_rubble"
    SUPPLY_BURN = "supply_burn"
    PRISONER_FREED = "prisoner_freed"
    BANNER_PLANTED = "banner_planted"


class Side(str, enum.Enum):
    HUME = "hume"
    BEASTMAN = "beastman"


class FrontStatus(str, enum.Enum):
    ACTIVE = "active"
    HUME_VICTORY = "hume_victory"
    BEASTMAN_VICTORY = "beastman_victory"


_KIND_PUSH: dict[ContributionKind, int] = {
    ContributionKind.NPC_KILL: 1,
    ContributionKind.NM_KILL: 5,
    ContributionKind.FORTIFICATION_RUBBLE: 3,
    ContributionKind.SUPPLY_BURN: 4,
    ContributionKind.PRISONER_FREED: 2,
    ContributionKind.BANNER_PLANTED: 8,
}


@dataclasses.dataclass
class Front:
    front_id: str
    hume_nation: HumeNation
    beastman_city: BeastmanCity
    zone_id: str
    kind: FrontKind
    push_score: int = 0
    status: FrontStatus = FrontStatus.ACTIVE
    tick_count: int = 0
    contributions: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass(frozen=True)
class ContributionResult:
    accepted: bool
    front_id: str
    push_delta: int
    push_score: int
    status: FrontStatus
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TickResult:
    accepted: bool
    front_id: str
    push_score: int
    status: FrontStatus
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanWarCampaign:
    _fronts: dict[str, Front] = dataclasses.field(
        default_factory=dict,
    )

    def open_front(
        self, *, front_id: str,
        hume_nation: HumeNation,
        beastman_city: BeastmanCity,
        zone_id: str,
        kind: FrontKind,
    ) -> t.Optional[Front]:
        if front_id in self._fronts:
            return None
        if not zone_id:
            return None
        f = Front(
            front_id=front_id,
            hume_nation=hume_nation,
            beastman_city=beastman_city,
            zone_id=zone_id, kind=kind,
        )
        self._fronts[front_id] = f
        return f

    def contribute(
        self, *, player_id: str,
        front_id: str,
        side: Side,
        kind: ContributionKind,
        magnitude: int = 1,
    ) -> ContributionResult:
        f = self._fronts.get(front_id)
        if f is None:
            return ContributionResult(
                False, front_id, 0, 0,
                FrontStatus.ACTIVE,
                reason="unknown front",
            )
        if f.status != FrontStatus.ACTIVE:
            return ContributionResult(
                False, front_id, 0, f.push_score, f.status,
                reason="front already resolved",
            )
        if magnitude <= 0:
            return ContributionResult(
                False, front_id, 0, f.push_score, f.status,
                reason="non-positive magnitude",
            )
        per = _KIND_PUSH[kind]
        # Hume contributions push score toward +, beastman toward -
        sign = 1 if side == Side.HUME else -1
        delta = per * magnitude * sign
        f.push_score = max(-100, min(100, f.push_score + delta))
        f.contributions[player_id] = (
            f.contributions.get(player_id, 0) + abs(delta)
        )
        # Auto-resolve if at cap
        if f.push_score >= 100:
            f.status = FrontStatus.HUME_VICTORY
        elif f.push_score <= -100:
            f.status = FrontStatus.BEASTMAN_VICTORY
        return ContributionResult(
            accepted=True, front_id=front_id,
            push_delta=delta, push_score=f.push_score,
            status=f.status,
        )

    def ai_tick(
        self, *, front_id: str,
        hume_baseline: int,
        beastman_baseline: int,
    ) -> TickResult:
        f = self._fronts.get(front_id)
        if f is None:
            return TickResult(
                False, front_id, 0,
                FrontStatus.ACTIVE,
                reason="unknown front",
            )
        if f.status != FrontStatus.ACTIVE:
            return TickResult(
                False, front_id, f.push_score, f.status,
                reason="front already resolved",
            )
        if hume_baseline < 0 or beastman_baseline < 0:
            return TickResult(
                False, front_id, f.push_score, f.status,
                reason="negative baseline",
            )
        delta = hume_baseline - beastman_baseline
        f.push_score = max(-100, min(100, f.push_score + delta))
        f.tick_count += 1
        if f.push_score >= 100:
            f.status = FrontStatus.HUME_VICTORY
        elif f.push_score <= -100:
            f.status = FrontStatus.BEASTMAN_VICTORY
        return TickResult(
            accepted=True, front_id=front_id,
            push_score=f.push_score, status=f.status,
        )

    def front_status(
        self, *, front_id: str,
    ) -> t.Optional[FrontStatus]:
        f = self._fronts.get(front_id)
        if f is None:
            return None
        return f.status

    def push_score(
        self, *, front_id: str,
    ) -> int:
        f = self._fronts.get(front_id)
        if f is None:
            return 0
        return f.push_score

    def top_contributors(
        self, *, front_id: str, top_n: int = 5,
    ) -> list[tuple[str, int]]:
        f = self._fronts.get(front_id)
        if f is None:
            return []
        sorted_items = sorted(
            f.contributions.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        return sorted_items[:top_n]

    def total_fronts(self) -> int:
        return len(self._fronts)


__all__ = [
    "HumeNation", "BeastmanCity",
    "FrontKind", "ContributionKind",
    "Side", "FrontStatus",
    "Front",
    "ContributionResult", "TickResult",
    "BeastmanWarCampaign",
]
