"""Engage/disengage state machine — drawn vs sheathed weapon.

Canonical FFXI distinction:
* SHEATHED — weapon away. Passive HP/MP regen at full rate.
  Can teleport. Can sit (extra regen). No target lock.
* DRAWN, IDLE — engaged but not actively swinging.
  Combat-rate regen (slower). Target locked. Can't teleport.
* DRAWN, AUTO_ATTACKING — actively swinging at target.
  Even slower regen, locked target, JA/spell windows still
  available between swings.

Public surface
--------------
    EngageState enum (SHEATHED / DRAWN_IDLE / DRAWN_ATTACKING)
    EngageStateMachine
        .engage(target_id) -> bool
        .disengage() -> bool
        .start_attacking() / .stop_attacking()
        .can_teleport() -> bool
        .regen_rate_multiplier() -> float
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Regen multipliers applied to base HP/MP per-tick rate
SHEATHED_REGEN_MULT = 1.0       # full passive regen
DRAWN_IDLE_REGEN_MULT = 0.5     # half regen when locked-on
ATTACKING_REGEN_MULT = 0.0      # no regen mid-swing


class EngageState(str, enum.Enum):
    SHEATHED = "sheathed"
    DRAWN_IDLE = "drawn_idle"
    DRAWN_ATTACKING = "drawn_attacking"


@dataclasses.dataclass(frozen=True)
class EngageResult:
    accepted: bool
    new_state: t.Optional[EngageState] = None
    target_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class EngageStateMachine:
    player_id: str
    state: EngageState = EngageState.SHEATHED
    target_id: t.Optional[str] = None

    @property
    def is_drawn(self) -> bool:
        return self.state in (
            EngageState.DRAWN_IDLE,
            EngageState.DRAWN_ATTACKING,
        )

    @property
    def is_attacking(self) -> bool:
        return self.state == EngageState.DRAWN_ATTACKING

    def can_teleport(self) -> bool:
        return self.state == EngageState.SHEATHED

    def can_sit(self) -> bool:
        return self.state == EngageState.SHEATHED

    def regen_rate_multiplier(self) -> float:
        return {
            EngageState.SHEATHED: SHEATHED_REGEN_MULT,
            EngageState.DRAWN_IDLE: DRAWN_IDLE_REGEN_MULT,
            EngageState.DRAWN_ATTACKING: ATTACKING_REGEN_MULT,
        }[self.state]

    def engage(self, *, target_id: str) -> EngageResult:
        if not target_id:
            return EngageResult(False, reason="target required")
        if self.state == EngageState.SHEATHED:
            self.state = EngageState.DRAWN_IDLE
            self.target_id = target_id
            return EngageResult(
                True, new_state=self.state, target_id=target_id,
            )
        # Already drawn — treat as a target swap
        self.target_id = target_id
        return EngageResult(
            True, new_state=self.state, target_id=target_id,
        )

    def disengage(self) -> EngageResult:
        if self.state == EngageState.SHEATHED:
            return EngageResult(False, reason="already sheathed")
        prev_target = self.target_id
        self.state = EngageState.SHEATHED
        self.target_id = None
        return EngageResult(
            True, new_state=self.state, target_id=prev_target,
        )

    def start_attacking(self) -> bool:
        if self.state != EngageState.DRAWN_IDLE:
            return False
        self.state = EngageState.DRAWN_ATTACKING
        return True

    def stop_attacking(self) -> bool:
        if self.state != EngageState.DRAWN_ATTACKING:
            return False
        self.state = EngageState.DRAWN_IDLE
        return True

    def force_disengage_on_death(self) -> bool:
        """Called when the player dies — fully resets the FSM."""
        self.state = EngageState.SHEATHED
        self.target_id = None
        return True


__all__ = [
    "SHEATHED_REGEN_MULT", "DRAWN_IDLE_REGEN_MULT",
    "ATTACKING_REGEN_MULT",
    "EngageState", "EngageResult",
    "EngageStateMachine",
]
