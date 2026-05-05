"""Prize court — captured-ship adjudication; distributes spoils.

After boarding_party_pvp resolves with an ATTACKER_WINS, the
captured ship and its cargo go to the PRIZE COURT for
adjudication. The court decides:
  * how the cargo and gil are split among the boarding crew
  * whether the ship itself can be KEPT (added to attacker
    fleet) or must be SCUTTLED (broken for parts)
  * whether nation-of-flag intervenes (privateers' flag
    nation taxes the prize)

Distribution shares:
  CAPTAIN     - 30% (the boarding party LEADER)
  OFFICERS    - 30% split among up to 2 officers
  CREW        - 30% split among the rest of the crew
  NATION_TAX  - 10% (only if attacker has a letter_of_marque)

Without a letter, the 10% nation_tax goes back into the
crew share (illegal seizure means no nation cut).

Disposition:
  KEEP_AS_PRIZE - if attacker fleet has open slots
  SCUTTLE       - if no slot, ship destroyed for material
                  bonuses

Public surface
--------------
    Disposition enum
    AdjudicationResult dataclass
    PrizeCourt
        .file_prize(prize_id, captured_ship_id, attacker_party,
                    captain, officers, cargo_value, gil_in_hold,
                    has_letter_of_marque, attacker_fleet_open_slots)
        .resolve(prize_id) -> AdjudicationResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Disposition(str, enum.Enum):
    KEEP_AS_PRIZE = "keep_as_prize"
    SCUTTLE = "scuttle"


CAPTAIN_SHARE_PCT = 30
OFFICERS_SHARE_PCT = 30
CREW_SHARE_PCT = 30
NATION_TAX_PCT = 10
MAX_OFFICERS = 2


@dataclasses.dataclass
class _Prize:
    prize_id: str
    captured_ship_id: str
    attacker_party: tuple[str, ...]
    captain: str
    officers: tuple[str, ...]
    cargo_value: int
    gil_in_hold: int
    has_letter_of_marque: bool
    attacker_fleet_open_slots: int
    resolved: bool = False


@dataclasses.dataclass(frozen=True)
class AdjudicationResult:
    accepted: bool
    prize_id: str
    captain_share: int = 0
    officer_shares: dict[str, int] = dataclasses.field(default_factory=dict)
    crew_shares: dict[str, int] = dataclasses.field(default_factory=dict)
    nation_tax: int = 0
    disposition: t.Optional[Disposition] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PrizeCourt:
    _prizes: dict[str, _Prize] = dataclasses.field(default_factory=dict)

    def file_prize(
        self, *, prize_id: str,
        captured_ship_id: str,
        attacker_party: tuple[str, ...],
        captain: str,
        officers: tuple[str, ...],
        cargo_value: int,
        gil_in_hold: int,
        has_letter_of_marque: bool,
        attacker_fleet_open_slots: int,
    ) -> bool:
        if not prize_id or prize_id in self._prizes:
            return False
        if not captured_ship_id or not captain:
            return False
        if not attacker_party or captain not in attacker_party:
            return False
        if len(officers) > MAX_OFFICERS:
            return False
        for off in officers:
            if off not in attacker_party or off == captain:
                return False
        if cargo_value < 0 or gil_in_hold < 0:
            return False
        if attacker_fleet_open_slots < 0:
            return False
        self._prizes[prize_id] = _Prize(
            prize_id=prize_id,
            captured_ship_id=captured_ship_id,
            attacker_party=tuple(attacker_party),
            captain=captain,
            officers=tuple(officers),
            cargo_value=cargo_value,
            gil_in_hold=gil_in_hold,
            has_letter_of_marque=has_letter_of_marque,
            attacker_fleet_open_slots=attacker_fleet_open_slots,
        )
        return True

    def resolve(self, *, prize_id: str) -> AdjudicationResult:
        rec = self._prizes.get(prize_id)
        if rec is None:
            return AdjudicationResult(
                False, prize_id=prize_id, reason="unknown prize",
            )
        if rec.resolved:
            return AdjudicationResult(
                False, prize_id=prize_id, reason="already resolved",
            )
        total = rec.cargo_value + rec.gil_in_hold
        nation_tax = (
            (total * NATION_TAX_PCT) // 100
            if rec.has_letter_of_marque else 0
        )
        # if no letter, the nation_tax goes BACK to crew
        captain_pct = CAPTAIN_SHARE_PCT
        officer_pct = OFFICERS_SHARE_PCT
        crew_pct = (
            CREW_SHARE_PCT
            if rec.has_letter_of_marque
            else CREW_SHARE_PCT + NATION_TAX_PCT
        )
        captain_share = (total * captain_pct) // 100
        officer_pool = (total * officer_pct) // 100
        crew_pool = total - nation_tax - captain_share - officer_pool
        # divide officer_pool among officers
        officer_shares: dict[str, int] = {}
        if rec.officers:
            per_off = officer_pool // len(rec.officers)
            for off in rec.officers:
                officer_shares[off] = per_off
        # crew = attacker_party minus captain minus officers
        crew = [
            f for f in rec.attacker_party
            if f != rec.captain and f not in rec.officers
        ]
        crew_shares: dict[str, int] = {}
        if crew:
            per_crew = crew_pool // len(crew)
            for c in crew:
                crew_shares[c] = per_crew
        # disposition
        if rec.attacker_fleet_open_slots > 0:
            disposition = Disposition.KEEP_AS_PRIZE
        else:
            disposition = Disposition.SCUTTLE
        rec.resolved = True
        return AdjudicationResult(
            accepted=True,
            prize_id=prize_id,
            captain_share=captain_share,
            officer_shares=officer_shares,
            crew_shares=crew_shares,
            nation_tax=nation_tax,
            disposition=disposition,
        )


__all__ = [
    "Disposition", "AdjudicationResult", "PrizeCourt",
    "CAPTAIN_SHARE_PCT", "OFFICERS_SHARE_PCT",
    "CREW_SHARE_PCT", "NATION_TAX_PCT", "MAX_OFFICERS",
]
