"""Dancer steps, waltzes, and finishing moves.

DNC's resource model:
* Steps (Quickstep / Box / Stutter / Feather) cost TP and apply
  a debuff to the target. They DON'T cost MP. Each step builds
  one Finishing Move charge (cap 5).
* Waltzes spend TP to heal the party (Curing Waltz I-V). The
  amount scales with CHR + healing skill.
* Sambas / Jigs / Spectral Jig are buff dances — apply a
  status to self or party, no Finishing Move charge.
* Flourishes spend Finishing Moves for various effects.

Public surface
--------------
    StepKind / WaltzKind / SambaKind / FlourishKind enums
    DancerState
        .step(kind, current_tp) -> StepResult
        .waltz(kind, current_tp, party_avg_hp_missing) -> WaltzResult
        .samba(kind, current_tp) -> SambaResult
        .flourish(kind, charges) -> FlourishResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_FINISHING_MOVES = 5
STEP_TP_COST = 100
WALTZ_TP_COST_BASE = 200    # Curing Waltz I; scales by tier
SAMBA_TP_COST = 350         # Drain Samba etc
JIG_TP_COST = 0             # passive on activation


class StepKind(str, enum.Enum):
    QUICKSTEP = "quickstep"      # evasion down
    BOX = "box_step"             # accuracy down
    STUTTER = "stutter_step"     # magic eva down
    FEATHER = "feather_step"     # crit hit rate down


class WaltzKind(str, enum.Enum):
    CURING_I = "curing_waltz_1"
    CURING_II = "curing_waltz_2"
    CURING_III = "curing_waltz_3"
    CURING_IV = "curing_waltz_4"
    CURING_V = "curing_waltz_5"
    HEALING = "healing_waltz"      # erase
    DIVINE = "divine_waltz"        # AoE cure


class SambaKind(str, enum.Enum):
    DRAIN = "drain_samba"
    ASPIR = "aspir_samba"
    HASTE = "haste_samba"


class JigKind(str, enum.Enum):
    SPECTRAL = "spectral_jig"     # invis + speed boost
    CHOCOBO = "chocobo_jig"        # speed boost only


class FlourishKind(str, enum.Enum):
    ANIMATED = "animated_flourish"  # 1 charge — high-damage hit
    DESPERATE = "desperate_flourish"  # 1 charge — single-target stun
    REVERSE = "reverse_flourish"    # 1 charge — restores TP from FMs
    BUILDING = "building_flourish"  # 2 charges — combo finisher


_WALTZ_HP_TABLE = {
    WaltzKind.CURING_I: (60, 200),
    WaltzKind.CURING_II: (130, 350),
    WaltzKind.CURING_III: (270, 600),
    WaltzKind.CURING_IV: (450, 900),
    WaltzKind.CURING_V: (650, 1300),
    WaltzKind.HEALING: (0, 0),       # no HP, removes debuff
    WaltzKind.DIVINE: (200, 500),    # AoE
}


_WALTZ_TP_TABLE = {
    WaltzKind.CURING_I: 200,
    WaltzKind.CURING_II: 350,
    WaltzKind.CURING_III: 500,
    WaltzKind.CURING_IV: 650,
    WaltzKind.CURING_V: 800,
    WaltzKind.HEALING: 200,
    WaltzKind.DIVINE: 400,
}


@dataclasses.dataclass(frozen=True)
class StepResult:
    accepted: bool
    finishing_moves_after: int = 0
    debuff_kind: t.Optional[StepKind] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class WaltzResult:
    accepted: bool
    healed: int = 0
    tp_spent: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SambaResult:
    accepted: bool
    tp_spent: int = 0
    duration_seconds: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class FlourishResult:
    accepted: bool
    charges_consumed: int = 0
    charges_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DancerState:
    player_id: str
    finishing_moves: int = 0

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------
    def step(self, *, kind: StepKind, current_tp: int) -> StepResult:
        if current_tp < STEP_TP_COST:
            return StepResult(False, reason="not enough TP")
        self.finishing_moves = min(
            MAX_FINISHING_MOVES, self.finishing_moves + 1,
        )
        return StepResult(
            accepted=True,
            finishing_moves_after=self.finishing_moves,
            debuff_kind=kind,
        )

    # ------------------------------------------------------------------
    # Waltzes
    # ------------------------------------------------------------------
    def waltz(self, *, kind: WaltzKind, current_tp: int,
              chr_stat: int = 0,
              healing_skill: int = 0) -> WaltzResult:
        cost = _WALTZ_TP_TABLE[kind]
        if current_tp < cost:
            return WaltzResult(False, reason="not enough TP")
        lo, hi = _WALTZ_HP_TABLE[kind]
        if hi == 0:
            return WaltzResult(accepted=True, tp_spent=cost,
                                healed=0)  # erase variant
        # Scale by CHR + skill: simple linear blend
        bonus = (chr_stat + healing_skill // 2)
        healed = lo + (hi - lo) * min(bonus, 256) // 256
        return WaltzResult(
            accepted=True, healed=int(healed), tp_spent=cost,
        )

    # ------------------------------------------------------------------
    # Sambas
    # ------------------------------------------------------------------
    def samba(self, *, kind: SambaKind, current_tp: int) -> SambaResult:
        if current_tp < SAMBA_TP_COST:
            return SambaResult(False, reason="not enough TP")
        # Sambas last ~2 minutes (120s) regardless of subkind for now.
        return SambaResult(
            accepted=True, tp_spent=SAMBA_TP_COST,
            duration_seconds=120,
        )

    # ------------------------------------------------------------------
    # Flourishes
    # ------------------------------------------------------------------
    def flourish(self, *, kind: FlourishKind) -> FlourishResult:
        cost_map = {
            FlourishKind.ANIMATED: 1,
            FlourishKind.DESPERATE: 1,
            FlourishKind.REVERSE: 1,
            FlourishKind.BUILDING: 2,
        }
        cost = cost_map[kind]
        if self.finishing_moves < cost:
            return FlourishResult(
                False, reason="not enough finishing moves",
            )
        self.finishing_moves -= cost
        return FlourishResult(
            accepted=True, charges_consumed=cost,
            charges_remaining=self.finishing_moves,
        )


__all__ = [
    "MAX_FINISHING_MOVES", "STEP_TP_COST", "WALTZ_TP_COST_BASE",
    "SAMBA_TP_COST", "JIG_TP_COST",
    "StepKind", "WaltzKind", "SambaKind", "JigKind", "FlourishKind",
    "StepResult", "WaltzResult", "SambaResult", "FlourishResult",
    "DancerState",
]
