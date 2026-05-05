"""Siren tribute — buy off mermaid sirens for safe passage.

Captains and parties can pay TRIBUTE to a siren to silence
her song over a specific lane for a window of time. Tribute
amounts must clear a SIREN_PRICE that scales with song power
and with the captain's standing in the SILMARIL_SIRENHALL
mermaid faction. High-rep tributaries get DISCOUNTS; pirates
and outlaws get SURCHARGED.

Tribute kinds:
  GIL       - direct gil payment, baseline
  PEARL     - mermaid pearl item; counts 3x of its gil value
  RESCUED   - return of an abducted mermaid kin (free passage
              for one full day)

When tribute is accepted:
  * the lane named in the tribute is granted SAFE_PASSAGE for
    duration_seconds
  * the siren_lure system should suppress songs against the
    payer's ship_id during that window (callers wire that)
  * mermaid faction reputation increases by REP_PER_TRIBUTE

Public surface
--------------
    TributeKind enum    GIL / PEARL / RESCUED
    TributeOffer dataclass
    TributeGrant dataclass
    SirenTribute
        .siren_price(power, faction_rep, is_outlaw)
        .pay_tribute(siren_id, payer_ship_id, lane_id, kind,
                     amount, faction_rep, is_outlaw, song_power,
                     now_seconds)
        .has_safe_passage(lane_id, ship_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TributeKind(str, enum.Enum):
    GIL = "gil"
    PEARL = "pearl"
    RESCUED = "rescued"


# baseline price by song power (matches siren_lure tiers)
_BASE_PRICE: dict[str, int] = {
    "whisper": 500,
    "chord": 2_000,
    "hymn": 8_000,
    "requiem": 25_000,
}

# duration of safe passage for each tribute kind (seconds)
_SAFE_PASSAGE_SECONDS: dict[TributeKind, int] = {
    TributeKind.GIL:     30 * 60,    # 30 min
    TributeKind.PEARL:   2 * 3_600,  # 2h
    TributeKind.RESCUED: 24 * 3_600, # one full day
}

REP_PER_TRIBUTE = 25


@dataclasses.dataclass(frozen=True)
class TributeGrant:
    accepted: bool
    lane_id: str
    ship_id: str
    expires_at: int = 0
    rep_delta: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PassageWindow:
    lane_id: str
    ship_id: str
    expires_at: int


@dataclasses.dataclass
class SirenTribute:
    _passage: list[_PassageWindow] = dataclasses.field(default_factory=list)

    @staticmethod
    def siren_price(
        *, power: str, faction_rep: int, is_outlaw: bool,
    ) -> int:
        base = _BASE_PRICE.get(power.lower())
        if base is None:
            return 0
        if is_outlaw:
            return base * 3
        # discount: -1% per 10 rep, capped at 50% off
        discount = min(50, max(0, faction_rep) // 10)
        return max(1, base - (base * discount) // 100)

    def pay_tribute(
        self, *, siren_id: str,
        payer_ship_id: str,
        lane_id: str,
        kind: TributeKind,
        amount: int,
        faction_rep: int,
        is_outlaw: bool,
        song_power: str,
        now_seconds: int,
    ) -> TributeGrant:
        if (
            not siren_id or not payer_ship_id or not lane_id
        ):
            return TributeGrant(
                accepted=False, lane_id=lane_id,
                ship_id=payer_ship_id, reason="bad ids",
            )
        if amount <= 0:
            return TributeGrant(
                accepted=False, lane_id=lane_id,
                ship_id=payer_ship_id, reason="bad amount",
            )
        price = self.siren_price(
            power=song_power,
            faction_rep=faction_rep,
            is_outlaw=is_outlaw,
        )
        if price == 0:
            return TributeGrant(
                accepted=False, lane_id=lane_id,
                ship_id=payer_ship_id, reason="unknown power",
            )
        # multipliers per kind
        if kind == TributeKind.GIL:
            effective = amount
        elif kind == TributeKind.PEARL:
            effective = amount * 3
        elif kind == TributeKind.RESCUED:
            # RESCUED gives full passage regardless of "amount"
            effective = price
        else:
            return TributeGrant(
                accepted=False, lane_id=lane_id,
                ship_id=payer_ship_id, reason="unknown kind",
            )
        if effective < price:
            return TributeGrant(
                accepted=False, lane_id=lane_id,
                ship_id=payer_ship_id, reason="insufficient",
            )
        duration = _SAFE_PASSAGE_SECONDS[kind]
        expires = now_seconds + duration
        self._passage.append(_PassageWindow(
            lane_id=lane_id, ship_id=payer_ship_id,
            expires_at=expires,
        ))
        return TributeGrant(
            accepted=True, lane_id=lane_id,
            ship_id=payer_ship_id,
            expires_at=expires,
            rep_delta=REP_PER_TRIBUTE,
        )

    def has_safe_passage(
        self, *, lane_id: str, ship_id: str, now_seconds: int,
    ) -> bool:
        for w in self._passage:
            if (
                w.lane_id == lane_id
                and w.ship_id == ship_id
                and w.expires_at > now_seconds
            ):
                return True
        return False


__all__ = [
    "TributeKind", "TributeGrant", "REP_PER_TRIBUTE",
    "SirenTribute",
]
