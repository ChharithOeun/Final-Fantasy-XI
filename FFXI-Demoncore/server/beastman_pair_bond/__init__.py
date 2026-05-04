"""Beastman pair-bond — beastman wedding ritual + bond stat bonus.

The beastman analog to the hume marriage system. Two beastman
players formally bond at the SHATHAR HIGH ALTAR through a 3-phase
ritual:

  PROPOSE   - one player proposes; the other has 7 in-game days
              to accept or decline (else the proposal lapses)
  CONSECRATE - both players present at the altar with the
               required offerings (one prime feather + one
               coral scale + one lacquered stone + one reaver
               bone — symbolic of pan-race unity)
  SEAL      - the bond goes live; both partners gain +5% fame
              when adventuring in the same zone, and a private
              shared stash slot

Either partner may DISSOLVE the bond at any time, with a 30-day
cooldown before a new proposal can be made.

Public surface
--------------
    BondPhase enum   PROPOSED / CONSECRATED / SEALED / DISSOLVED
    Bond dataclass
    BeastmanPairBond
        .propose(proposer_id, partner_id, now_day)
        .accept(partner_id, now_day)
        .consecrate(bond_id, offerings, now_day)
        .seal(bond_id, now_day)
        .dissolve(bond_id, initiator_id, now_day)
        .bond_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BondPhase(str, enum.Enum):
    PROPOSED = "proposed"
    CONSECRATED = "consecrated"
    SEALED = "sealed"
    DISSOLVED = "dissolved"


_PROPOSAL_LAPSE_DAYS = 7
_DISSOLVE_COOLDOWN_DAYS = 30
_REQUIRED_OFFERINGS = {
    "prime_feather": 1,
    "coral_scale": 1,
    "lacquered_stone": 1,
    "reaver_bone": 1,
}


@dataclasses.dataclass
class Bond:
    bond_id: int
    proposer_id: str
    partner_id: str
    phase: BondPhase
    proposed_at_day: int
    consecrated_at_day: t.Optional[int] = None
    sealed_at_day: t.Optional[int] = None
    dissolved_at_day: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class ProposeResult:
    accepted: bool
    bond_id: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class PhaseResult:
    accepted: bool
    bond_id: int
    phase: BondPhase
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanPairBond:
    _bonds: dict[int, Bond] = dataclasses.field(default_factory=dict)
    _next_id: int = 1
    # Track most recent dissolve day per player for cooldown
    _last_dissolve: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def _active_bond_for(
        self, player_id: str,
    ) -> t.Optional[Bond]:
        for b in self._bonds.values():
            if b.phase == BondPhase.DISSOLVED:
                continue
            if (
                b.proposer_id == player_id
                or b.partner_id == player_id
            ):
                return b
        return None

    def propose(
        self, *, proposer_id: str,
        partner_id: str,
        now_day: int,
    ) -> ProposeResult:
        if proposer_id == partner_id:
            return ProposeResult(
                False, reason="cannot bond with self",
            )
        if not proposer_id or not partner_id:
            return ProposeResult(
                False, reason="missing partner",
            )
        # Cooldown after dissolve
        last = self._last_dissolve.get(proposer_id)
        if last is not None and now_day - last < _DISSOLVE_COOLDOWN_DAYS:
            return ProposeResult(
                False, reason="cooldown after dissolve",
            )
        last_p = self._last_dissolve.get(partner_id)
        if last_p is not None and now_day - last_p < _DISSOLVE_COOLDOWN_DAYS:
            return ProposeResult(
                False, reason="partner cooldown after dissolve",
            )
        if self._active_bond_for(proposer_id) is not None:
            return ProposeResult(
                False, reason="proposer already in bond",
            )
        if self._active_bond_for(partner_id) is not None:
            return ProposeResult(
                False, reason="partner already in bond",
            )
        bid = self._next_id
        self._next_id += 1
        b = Bond(
            bond_id=bid,
            proposer_id=proposer_id,
            partner_id=partner_id,
            phase=BondPhase.PROPOSED,
            proposed_at_day=now_day,
        )
        self._bonds[bid] = b
        return ProposeResult(accepted=True, bond_id=bid)

    def accept(
        self, *, partner_id: str, bond_id: int, now_day: int,
    ) -> PhaseResult:
        b = self._bonds.get(bond_id)
        if b is None:
            return PhaseResult(
                False, bond_id, BondPhase.DISSOLVED,
                reason="unknown bond",
            )
        if b.partner_id != partner_id:
            return PhaseResult(
                False, bond_id, b.phase,
                reason="not the proposed partner",
            )
        if b.phase != BondPhase.PROPOSED:
            return PhaseResult(
                False, bond_id, b.phase,
                reason="wrong phase",
            )
        if now_day - b.proposed_at_day > _PROPOSAL_LAPSE_DAYS:
            b.phase = BondPhase.DISSOLVED
            b.dissolved_at_day = now_day
            return PhaseResult(
                False, bond_id, b.phase,
                reason="proposal lapsed",
            )
        # Stay in PROPOSED until offerings consecrate it.
        # accept() just acknowledges the partner — phase advances
        # only on consecrate.
        return PhaseResult(
            accepted=True, bond_id=bond_id, phase=b.phase,
        )

    def consecrate(
        self, *, bond_id: int,
        offerings: dict[str, int],
        now_day: int,
    ) -> PhaseResult:
        b = self._bonds.get(bond_id)
        if b is None:
            return PhaseResult(
                False, bond_id, BondPhase.DISSOLVED,
                reason="unknown bond",
            )
        if b.phase != BondPhase.PROPOSED:
            return PhaseResult(
                False, bond_id, b.phase,
                reason="wrong phase",
            )
        for item_id, qty in _REQUIRED_OFFERINGS.items():
            if offerings.get(item_id, 0) < qty:
                return PhaseResult(
                    False, bond_id, b.phase,
                    reason=f"missing offering:{item_id}",
                )
        b.phase = BondPhase.CONSECRATED
        b.consecrated_at_day = now_day
        return PhaseResult(
            accepted=True, bond_id=bond_id, phase=b.phase,
        )

    def seal(
        self, *, bond_id: int, now_day: int,
    ) -> PhaseResult:
        b = self._bonds.get(bond_id)
        if b is None:
            return PhaseResult(
                False, bond_id, BondPhase.DISSOLVED,
                reason="unknown bond",
            )
        if b.phase != BondPhase.CONSECRATED:
            return PhaseResult(
                False, bond_id, b.phase,
                reason="not consecrated",
            )
        b.phase = BondPhase.SEALED
        b.sealed_at_day = now_day
        return PhaseResult(
            accepted=True, bond_id=bond_id, phase=b.phase,
        )

    def dissolve(
        self, *, bond_id: int,
        initiator_id: str,
        now_day: int,
    ) -> PhaseResult:
        b = self._bonds.get(bond_id)
        if b is None:
            return PhaseResult(
                False, bond_id, BondPhase.DISSOLVED,
                reason="unknown bond",
            )
        if initiator_id not in (b.proposer_id, b.partner_id):
            return PhaseResult(
                False, bond_id, b.phase,
                reason="not a partner",
            )
        if b.phase == BondPhase.DISSOLVED:
            return PhaseResult(
                False, bond_id, b.phase,
                reason="already dissolved",
            )
        b.phase = BondPhase.DISSOLVED
        b.dissolved_at_day = now_day
        self._last_dissolve[b.proposer_id] = now_day
        self._last_dissolve[b.partner_id] = now_day
        return PhaseResult(
            accepted=True, bond_id=bond_id, phase=b.phase,
        )

    def bond_for(
        self, *, player_id: str,
    ) -> t.Optional[Bond]:
        return self._active_bond_for(player_id)

    def total_bonds(self) -> int:
        return len(self._bonds)


__all__ = [
    "BondPhase", "Bond",
    "ProposeResult", "PhaseResult",
    "BeastmanPairBond",
]
