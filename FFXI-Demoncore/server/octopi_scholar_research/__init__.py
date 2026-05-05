"""Octopi scholar research — CORAL_CAVERNS knowledge trade.

The cephalopod scholars of CORAL_CAVERNS run a research
exchange. Players bring DATA SAMPLES (mob research notes,
abyssal fragments, salvaged maps) and the octopi pay them
in TOMES — coral-bound spell scrolls, lore fragments, and
recipe slips that are unobtainable elsewhere.

Sample classes (what players hand over):
  MOB_NOTE       - bestiary research; cheap; stack
  ABYSSAL_FRAG   - kraken-loot fragment; mid value
  WRECK_MAP      - intact wreck map (deep_treasure_relic
                   side-product); high value
  REQUIEM_RECORD - recording of a siren requiem; rare

Tomes (what the scholars pay):
  CORAL_TOME      - low; cheap exchange
  ABYSSAL_CODEX   - mid
  REQUIEM_LIBRO   - rare; opens new spells
  KRAKEN_PRIMER   - very rare; required for one of the
                    BLU spells in the Kraken school

Each player has a STANDING with the scholars; higher
standing unlocks better trades. Standing rises when you
turn in samples; it never falls.

Public surface
--------------
    SampleKind enum
    Tome enum
    TradeOffer dataclass
    OctopiScholarResearch
        .turn_in(player_id, kind, qty)
        .standing(player_id)
        .available_trades(player_id) -> tuple[TradeOffer, ...]
        .request_tome(player_id, tome) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SampleKind(str, enum.Enum):
    MOB_NOTE = "mob_note"
    ABYSSAL_FRAG = "abyssal_frag"
    WRECK_MAP = "wreck_map"
    REQUIEM_RECORD = "requiem_record"


class Tome(str, enum.Enum):
    CORAL_TOME = "coral_tome"
    ABYSSAL_CODEX = "abyssal_codex"
    REQUIEM_LIBRO = "requiem_libro"
    KRAKEN_PRIMER = "kraken_primer"


# how much standing each sample turn-in is worth
_STANDING_VALUE: dict[SampleKind, int] = {
    SampleKind.MOB_NOTE: 1,
    SampleKind.ABYSSAL_FRAG: 5,
    SampleKind.WRECK_MAP: 12,
    SampleKind.REQUIEM_RECORD: 40,
}

# minimum standing required to request each tome,
# and how much standing it COSTS
_TOME_STANDING_REQ: dict[Tome, int] = {
    Tome.CORAL_TOME: 5,
    Tome.ABYSSAL_CODEX: 25,
    Tome.REQUIEM_LIBRO: 80,
    Tome.KRAKEN_PRIMER: 200,
}

_TOME_STANDING_COST: dict[Tome, int] = {
    Tome.CORAL_TOME: 5,
    Tome.ABYSSAL_CODEX: 20,
    Tome.REQUIEM_LIBRO: 60,
    Tome.KRAKEN_PRIMER: 150,
}


@dataclasses.dataclass(frozen=True)
class TradeOffer:
    tome: Tome
    standing_required: int
    standing_cost: int


@dataclasses.dataclass(frozen=True)
class TurnInResult:
    accepted: bool
    standing_gained: int = 0
    new_standing: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TomeRequest:
    accepted: bool
    tome: t.Optional[Tome] = None
    standing_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class OctopiScholarResearch:
    _standing: dict[str, int] = dataclasses.field(default_factory=dict)

    def turn_in(
        self, *, player_id: str,
        kind: SampleKind,
        qty: int,
    ) -> TurnInResult:
        if not player_id:
            return TurnInResult(False, reason="bad player")
        if kind not in _STANDING_VALUE:
            return TurnInResult(False, reason="unknown sample")
        if qty <= 0:
            return TurnInResult(False, reason="bad qty")
        gain = _STANDING_VALUE[kind] * qty
        new = self._standing.get(player_id, 0) + gain
        self._standing[player_id] = new
        return TurnInResult(
            accepted=True,
            standing_gained=gain,
            new_standing=new,
        )

    def standing(self, *, player_id: str) -> int:
        return self._standing.get(player_id, 0)

    def available_trades(
        self, *, player_id: str,
    ) -> tuple[TradeOffer, ...]:
        s = self.standing(player_id=player_id)
        return tuple(
            TradeOffer(
                tome=t,
                standing_required=req,
                standing_cost=_TOME_STANDING_COST[t],
            )
            for t, req in _TOME_STANDING_REQ.items()
            if s >= req
        )

    def request_tome(
        self, *, player_id: str, tome: Tome,
    ) -> TomeRequest:
        if tome not in _TOME_STANDING_REQ:
            return TomeRequest(False, reason="unknown tome")
        s = self.standing(player_id=player_id)
        if s < _TOME_STANDING_REQ[tome]:
            return TomeRequest(
                False, reason="standing too low",
            )
        cost = _TOME_STANDING_COST[tome]
        new_s = s - cost
        self._standing[player_id] = new_s
        return TomeRequest(
            accepted=True, tome=tome, standing_after=new_s,
        )


__all__ = [
    "SampleKind", "Tome",
    "TradeOffer", "TurnInResult", "TomeRequest",
    "OctopiScholarResearch",
]
