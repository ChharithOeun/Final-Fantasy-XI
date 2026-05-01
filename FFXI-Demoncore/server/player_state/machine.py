"""Player lifecycle state machine.

Per HARDCORE_DEATH.md + FOMOR_GEAR_PROGRESSION.md + EQUIPMENT_WEAR.md.
The apex difficulty pillar:

States:
    ALIVE        — normal play
    KO           — knocked out, awaiting Raise/Reraise
    KO_LVL_99    — knocked out at lvl 99; permadeath timer started
    FOMOR        — character became an AI-controlled Fomor

Death penalties scale with level:
    Levels 1-89:  -25% durability on all gear; level loss; standard XP penalty
    Levels 90-98: -40% durability; level loss; 2-day Reraise lockout
    Level 99:     100% durability loss; 1-hour permadeath timer;
                  if not Raised in time → FOMOR transition

Pure-Python deterministic; no I/O. The LSB combat broker calls
notify_death/notify_raised/notify_permadeath_timer_expired and the
machine outputs the state transitions + side-effects (durability
deductions, level adjustments, mood-event emissions for the
orchestrator).
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PlayerLifecycle(str, enum.Enum):
    ALIVE = "alive"
    KO = "ko"                            # standard knockout, raisable
    KO_LVL_99 = "ko_lvl_99"             # permadeath timer running
    FOMOR = "fomor"                      # transitioned; AI-controlled


@dataclasses.dataclass
class DeathPenalty:
    """The cost of dying. Returned by notify_death so the LSB / orchestrator
    can apply it."""
    durability_pct_lost: float           # fraction of all-gear durability gone
    levels_lost: int                     # XP-level reductions
    reraise_lockout_seconds: float       # how long until Reraise can fire
    permadeath_timer_seconds: float      # 0 unless lvl 99
    mood_event: str                      # event_kind to push to orchestrator


@dataclasses.dataclass
class DeathEvent:
    """Input record describing the death."""
    cause: str                            # "killed_by_mob:goblin_pickpocket", etc
    by_player_pvp: bool = False          # PvP outlaw kill?
    in_outlaw_zone: bool = False         # were they in PvP-enabled territory?
    timestamp: float = 0.0


@dataclasses.dataclass
class PlayerSnapshot:
    """Full player state. Serializable for DB persistence."""
    player_id: str
    level: int = 1
    lifecycle: PlayerLifecycle = PlayerLifecycle.ALIVE
    death_count: int = 0
    fomor_at: t.Optional[float] = None
    permadeath_started_at: t.Optional[float] = None

    # Last death context (for raise / re-spawn flow)
    last_death_cause: t.Optional[str] = None
    last_death_at: t.Optional[float] = None
    reraise_locked_until: t.Optional[float] = None

    # Cumulative tracking
    total_levels_lost_to_death: int = 0
    total_durability_lost_to_death_pct: float = 0.0


# ----------------------------------------------------------------------
# Penalty tables
# ----------------------------------------------------------------------

PERMADEATH_TIMER_SECONDS = 3600.0   # 1 hour at level 99


def _compute_penalty(level: int) -> DeathPenalty:
    """Per HARDCORE_DEATH.md."""
    if level >= 99:
        return DeathPenalty(
            durability_pct_lost=1.0,           # 100% durability loss
            levels_lost=0,                      # no level loss; permadeath timer instead
            reraise_lockout_seconds=0.0,
            permadeath_timer_seconds=PERMADEATH_TIMER_SECONDS,
            mood_event="died_with_full_durability_loss",
        )
    elif level >= 90:
        return DeathPenalty(
            durability_pct_lost=0.40,
            levels_lost=1,
            reraise_lockout_seconds=2 * 86400.0,   # 2 days
            permadeath_timer_seconds=0.0,
            mood_event="player_died",
        )
    else:
        return DeathPenalty(
            durability_pct_lost=0.25,
            levels_lost=1,
            reraise_lockout_seconds=0.0,
            permadeath_timer_seconds=0.0,
            mood_event="player_died",
        )


# ----------------------------------------------------------------------
# State machine
# ----------------------------------------------------------------------

class PlayerStateMachine:
    """One state machine per player. State persists in PlayerSnapshot.

    Methods are pure functions on the state — no I/O. The LSB / orchestrator
    persist the snapshot externally.
    """

    def __init__(self, snapshot: PlayerSnapshot):
        self.snap = snapshot

    # ------------------------------------------------------------------
    # Death
    # ------------------------------------------------------------------

    def notify_death(self, event: DeathEvent) -> DeathPenalty:
        """Player just died. Compute and apply penalty. Update lifecycle."""
        if self.snap.lifecycle == PlayerLifecycle.FOMOR:
            # Already a fomor; this would be the fomor itself dying
            raise ValueError(
                f"player {self.snap.player_id} is FOMOR; cannot die normally"
            )

        penalty = _compute_penalty(self.snap.level)

        self.snap.death_count += 1
        self.snap.last_death_cause = event.cause
        self.snap.last_death_at = event.timestamp
        self.snap.total_durability_lost_to_death_pct += penalty.durability_pct_lost

        if penalty.levels_lost > 0:
            self.snap.level = max(1, self.snap.level - penalty.levels_lost)
            self.snap.total_levels_lost_to_death += penalty.levels_lost

        # Lifecycle transition
        if self.snap.level >= 99 or penalty.permadeath_timer_seconds > 0:
            self.snap.lifecycle = PlayerLifecycle.KO_LVL_99
            self.snap.permadeath_started_at = event.timestamp
        else:
            self.snap.lifecycle = PlayerLifecycle.KO
            self.snap.permadeath_started_at = None

        if penalty.reraise_lockout_seconds > 0:
            self.snap.reraise_locked_until = (
                event.timestamp + penalty.reraise_lockout_seconds
            )
        else:
            self.snap.reraise_locked_until = None

        return penalty

    # ------------------------------------------------------------------
    # Raise / Reraise
    # ------------------------------------------------------------------

    def notify_raised(self, *, raise_tier: int = 1,
                       now: float = 0.0) -> bool:
        """Player got Raised. Returns True if raise was accepted, False
        if Reraise is locked out."""
        if self.snap.lifecycle == PlayerLifecycle.ALIVE:
            return False
        if self.snap.lifecycle == PlayerLifecycle.FOMOR:
            return False
        if (self.snap.reraise_locked_until is not None
                and now < self.snap.reraise_locked_until):
            return False

        # Raised — return to alive
        self.snap.lifecycle = PlayerLifecycle.ALIVE
        self.snap.permadeath_started_at = None
        return True

    # ------------------------------------------------------------------
    # Permadeath timer expiration → Fomor transition
    # ------------------------------------------------------------------

    def notify_permadeath_timer_expired(self, now: float = 0.0) -> bool:
        """Called when the 1-hour permadeath timer expires.

        If the player is still KO_LVL_99 (not raised), they become a
        Fomor. Returns True if the transition happened.
        """
        if self.snap.lifecycle != PlayerLifecycle.KO_LVL_99:
            return False
        if self.snap.permadeath_started_at is None:
            return False

        elapsed = now - self.snap.permadeath_started_at
        if elapsed < PERMADEATH_TIMER_SECONDS:
            return False    # timer hasn't expired yet

        # Transition to Fomor
        self.snap.lifecycle = PlayerLifecycle.FOMOR
        self.snap.fomor_at = now
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.ALIVE

    def is_in_permadeath_timer(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.KO_LVL_99

    def time_until_permadeath(self, now: float = 0.0) -> t.Optional[float]:
        """Seconds remaining on permadeath timer, or None if not active."""
        if self.snap.lifecycle != PlayerLifecycle.KO_LVL_99:
            return None
        if self.snap.permadeath_started_at is None:
            return None
        elapsed = now - self.snap.permadeath_started_at
        remaining = PERMADEATH_TIMER_SECONDS - elapsed
        return max(0.0, remaining)

    def is_fomor(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.FOMOR
