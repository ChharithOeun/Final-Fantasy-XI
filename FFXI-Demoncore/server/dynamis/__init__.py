"""Dynamis — timed instanced raid content + dynamis currency.

Each Dynamis zone runs as an instance: a party enters with a token,
the timer starts at 1 hour, mobs drop dynamis_currency_X (varies by
zone) plus AF1 currency. Hourglass extensions (30 min each) bought
via in-zone NPC up to 2 hours total.

Public surface
--------------
    DynamisZone enum
    DynamisInstance lifecycle
        .extend(now_tick) -> bool
        .tick(now_tick) -> True if still active
        .record_kill(currency_drops)
        .conclude(now_tick) -> total currency at exit
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DynamisZone(str, enum.Enum):
    DYNAMIS_BASTOK = "dynamis_bastok"
    DYNAMIS_SAN_DORIA = "dynamis_san_doria"
    DYNAMIS_WINDURST = "dynamis_windurst"
    DYNAMIS_JEUNO = "dynamis_jeuno"
    DYNAMIS_BEAUCEDINE = "dynamis_beaucedine"
    DYNAMIS_XARCABARD = "dynamis_xarcabard"


# Currency per zone (the 100-piece, 10000-piece, etc.)
ZONE_CURRENCY: dict[DynamisZone, str] = {
    DynamisZone.DYNAMIS_BASTOK: "ordelle_bronze",
    DynamisZone.DYNAMIS_SAN_DORIA: "montiont_silver",
    DynamisZone.DYNAMIS_WINDURST: "ranperre_gold",
    DynamisZone.DYNAMIS_JEUNO: "tenshodo_invitation",
    DynamisZone.DYNAMIS_BEAUCEDINE: "elder_currency",
    DynamisZone.DYNAMIS_XARCABARD: "elder_currency",
}


BASE_INSTANCE_SECONDS = 60 * 60                    # 1 hour
EXTENSION_SECONDS = 30 * 60                         # 30 min each
MAX_EXTENSIONS = 2                                  # 2hr total


@dataclasses.dataclass(frozen=True)
class CurrencyLoot:
    currency_id: str
    amount: int


@dataclasses.dataclass
class DynamisInstance:
    instance_id: str
    zone: DynamisZone
    leader_id: str
    started_at_tick: int
    expires_at_tick: int
    extensions_used: int = 0
    concluded: bool = False
    currency_total: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    @property
    def is_active(self) -> bool:
        return not self.concluded

    def time_remaining(self, *, now_tick: int) -> int:
        if self.concluded:
            return 0
        return max(0, self.expires_at_tick - now_tick)

    def extend(self, *, now_tick: int) -> bool:
        if self.concluded:
            return False
        if self.extensions_used >= MAX_EXTENSIONS:
            return False
        if now_tick > self.expires_at_tick:
            # already expired
            return False
        self.expires_at_tick += EXTENSION_SECONDS
        self.extensions_used += 1
        return True

    def tick(self, *, now_tick: int) -> bool:
        """Returns True if instance is still active."""
        if self.concluded:
            return False
        if now_tick >= self.expires_at_tick:
            self.concluded = True
            return False
        return True

    def record_kill(self, *, drops: t.Iterable[CurrencyLoot]) -> None:
        if self.concluded:
            return
        for d in drops:
            if d.amount <= 0:
                continue
            self.currency_total[d.currency_id] = (
                self.currency_total.get(d.currency_id, 0) + d.amount
            )

    def conclude(self, *, now_tick: int) -> dict[str, int]:
        self.concluded = True
        return dict(self.currency_total)


def open_instance(
    *, instance_id: str, zone: DynamisZone,
    leader_id: str, now_tick: int,
) -> DynamisInstance:
    return DynamisInstance(
        instance_id=instance_id, zone=zone,
        leader_id=leader_id,
        started_at_tick=now_tick,
        expires_at_tick=now_tick + BASE_INSTANCE_SECONDS,
    )


__all__ = [
    "DynamisZone", "ZONE_CURRENCY",
    "BASE_INSTANCE_SECONDS", "EXTENSION_SECONDS",
    "MAX_EXTENSIONS",
    "CurrencyLoot", "DynamisInstance",
    "open_instance",
]
