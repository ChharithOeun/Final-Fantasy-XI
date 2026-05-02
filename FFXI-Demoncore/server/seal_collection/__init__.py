"""Seal collection — AF1 seal grouping for armor exchange.

Each job has 5 AF1 seals (head/body/hands/legs/feet); collect 3 of
the same seal type and trade for the corresponding AF armor piece.
Seals drop from level-appropriate mobs; AF1 is the entry-tier
artifact armor.

Public surface
--------------
    SealKind enum (head/body/hands/legs/feet)
    SealSpec catalog (per-job-per-slot)
    PlayerSealBag
        .add(seal_id)
        .can_trade(seal_id)
        .trade_for_af(seal_id) -> ArmorReward | None
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SealKind(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"


SEALS_NEEDED_PER_TRADE = 3


@dataclasses.dataclass(frozen=True)
class SealSpec:
    seal_id: str          # e.g. "warrior_head_seal"
    job: str
    kind: SealKind
    af_armor_id: str      # e.g. "warrior_mask"


# Sample catalog - 6 jobs x 5 slots = 30 entries. Trim to 4 jobs.
def _build_catalog() -> tuple[SealSpec, ...]:
    out: list[SealSpec] = []
    armors = {
        "warrior":     ("warrior_mask", "warrior_mufflers",
                         "warrior_lorica", "warrior_cuisses",
                         "warrior_calligae"),
        "monk":        ("temple_crown", "temple_gloves",
                         "temple_cyclas", "temple_hose",
                         "temple_gaiters"),
        "white_mage":  ("healers_cap", "healers_mitts",
                         "healers_briault", "healers_pantaloons",
                         "healers_duckbills"),
        "black_mage":  ("wizards_petasos", "wizards_gloves",
                         "wizards_coat", "wizards_tonban",
                         "wizards_sabots"),
    }
    slot_order = (SealKind.HEAD, SealKind.HANDS, SealKind.BODY,
                  SealKind.LEGS, SealKind.FEET)
    for job, pieces in armors.items():
        for slot, piece in zip(slot_order, pieces):
            out.append(SealSpec(
                seal_id=f"{job}_{slot.value}_seal",
                job=job, kind=slot,
                af_armor_id=piece,
            ))
    return tuple(out)


SEAL_CATALOG: tuple[SealSpec, ...] = _build_catalog()
SEAL_BY_ID: dict[str, SealSpec] = {s.seal_id: s for s in SEAL_CATALOG}


@dataclasses.dataclass(frozen=True)
class TradeResult:
    accepted: bool
    seal_id: str
    af_armor_id: t.Optional[str] = None
    seals_consumed: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerSealBag:
    player_id: str
    counts: dict[str, int] = dataclasses.field(default_factory=dict)

    def add(self, *, seal_id: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        if seal_id not in SEAL_BY_ID:
            return False
        self.counts[seal_id] = self.counts.get(seal_id, 0) + quantity
        return True

    def count(self, seal_id: str) -> int:
        return self.counts.get(seal_id, 0)

    def can_trade(self, *, seal_id: str) -> bool:
        return self.count(seal_id) >= SEALS_NEEDED_PER_TRADE

    def trade_for_af(self, *, seal_id: str) -> TradeResult:
        spec = SEAL_BY_ID.get(seal_id)
        if spec is None:
            return TradeResult(False, seal_id, reason="unknown seal")
        if not self.can_trade(seal_id=seal_id):
            return TradeResult(
                False, seal_id,
                reason=f"need {SEALS_NEEDED_PER_TRADE} seals",
            )
        self.counts[seal_id] -= SEALS_NEEDED_PER_TRADE
        if self.counts[seal_id] == 0:
            del self.counts[seal_id]
        return TradeResult(
            accepted=True, seal_id=seal_id,
            af_armor_id=spec.af_armor_id,
            seals_consumed=SEALS_NEEDED_PER_TRADE,
        )

    def total_seals(self) -> int:
        return sum(self.counts.values())


__all__ = [
    "SealKind", "SealSpec",
    "SEAL_CATALOG", "SEAL_BY_ID",
    "SEALS_NEEDED_PER_TRADE",
    "TradeResult", "PlayerSealBag",
]
