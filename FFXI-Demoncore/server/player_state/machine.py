"""Player lifecycle state machine.

Per HARDCORE_DEATH.md + FOMOR_GEAR_PROGRESSION.md + EQUIPMENT_WEAR.md.
The apex difficulty pillar:

States:
    ALIVE                  — normal play
    KO                     — knocked out, awaiting Raise/Reraise
                              (ONLY at level 1-29; sub-permadeath tier)
    KO_INSTANCE            — knocked out inside a BCNM/raid/dungeon;
                              3-min in-instance revive window before
                              auto-warp-out + permadeath timer
    KO_PERMADEATH_TIMER    — knocked out at lvl 30+; 1-hour timer;
                              if not Raised → FOMOR
    FOMOR                  — character became AI-controlled Fomor

Tier-scaled death penalties:
    Levels 1-29:    -10% durability; 1 level loss; standard recovery
                     (no permadeath; just regular Raise)
    Levels 30-89:   -25% durability; 1 level loss; 1-hour permadeath
                     timer; if not Raised → FOMOR
    Levels 90-98:   -40% durability; 1 level loss; 1-hour permadeath
                     timer + 2-day Reraise lockout
    Level 99:       100% durability LOSS; no level loss; 1-hour
                     permadeath timer; the apex tier

Instance KO (BCNM/raid/dungeon):
    On death inside an instance → KO_INSTANCE for 3 minutes
    Party has 3 minutes to Raise inside the instance.
    If timer expires → warped out + transitions to
    KO_PERMADEATH_TIMER (or KO if level < 30) and the standard
    1-hour permadeath countdown begins.

Pure-Python deterministic; no I/O. The LSB combat broker calls
notify_death/notify_raised/notify_permadeath_timer_expired/
notify_instance_evict_timer_expired and the machine outputs the
state transitions + side-effects.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PlayerLifecycle(str, enum.Enum):
    ALIVE = "alive"
    KO = "ko"                                  # sub-permadeath knockout (lvl 1-29)
    KO_INSTANCE = "ko_instance"                 # 3-min in-instance revive window
    KO_PERMADEATH_TIMER = "ko_permadeath_timer" # 1-hour permadeath countdown (lvl 30+)
    FOMOR = "fomor"                             # transitioned; AI-controlled


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
    in_instance: bool = False            # died inside BCNM/raid/dungeon?
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

    # Instance-KO 3-minute window
    instance_evict_at: t.Optional[float] = None  # when 3-min timer expires
    instance_id: t.Optional[str] = None           # which BCNM/dungeon

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

PERMADEATH_TIMER_SECONDS = 3600.0    # 1 hour permadeath countdown (lvl 30+)
INSTANCE_EVICT_SECONDS = 180.0       # 3-minute instance revive window
PERMADEATH_THRESHOLD_LEVEL = 30      # below this, no permadeath risk


def _compute_penalty(level: int) -> DeathPenalty:
    """Per HARDCORE_DEATH.md (revised tier).
    Permadeath now applies at level 30+ (was 99+). The level-99 special
    case keeps the apex 100% durability loss."""
    if level >= 99:
        return DeathPenalty(
            durability_pct_lost=1.0,
            levels_lost=0,
            reraise_lockout_seconds=0.0,
            permadeath_timer_seconds=PERMADEATH_TIMER_SECONDS,
            mood_event="died_with_full_durability_loss",
        )
    elif level >= 90:
        return DeathPenalty(
            durability_pct_lost=0.40,
            levels_lost=1,
            reraise_lockout_seconds=2 * 86400.0,
            permadeath_timer_seconds=PERMADEATH_TIMER_SECONDS,
            mood_event="player_died",
        )
    elif level >= PERMADEATH_THRESHOLD_LEVEL:
        # Permadeath active at lvl 30+
        return DeathPenalty(
            durability_pct_lost=0.25,
            levels_lost=1,
            reraise_lockout_seconds=0.0,
            permadeath_timer_seconds=PERMADEATH_TIMER_SECONDS,
            mood_event="player_died",
        )
    else:
        # Sub-permadeath tier (lvl 1-29): standard recovery
        return DeathPenalty(
            durability_pct_lost=0.10,
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

    def notify_death(self, event: DeathEvent,
                       instance_id: t.Optional[str] = None) -> DeathPenalty:
        """Player just died. Compute and apply penalty. Update lifecycle.

        If event.in_instance is True, transitions to KO_INSTANCE with
        a 3-minute revive window before the permadeath countdown starts.
        Otherwise transitions directly to KO (lvl 1-29) or
        KO_PERMADEATH_TIMER (lvl 30+)."""
        if self.snap.lifecycle == PlayerLifecycle.FOMOR:
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
        if event.in_instance:
            # Instance KO: 3-min in-instance revive window FIRST
            self.snap.lifecycle = PlayerLifecycle.KO_INSTANCE
            self.snap.instance_evict_at = event.timestamp + INSTANCE_EVICT_SECONDS
            self.snap.instance_id = instance_id
            self.snap.permadeath_started_at = None    # not yet
        elif penalty.permadeath_timer_seconds > 0:
            # Permadeath threshold met (lvl 30+)
            self.snap.lifecycle = PlayerLifecycle.KO_PERMADEATH_TIMER
            self.snap.permadeath_started_at = event.timestamp
        else:
            # Sub-permadeath (lvl 1-29) standard knockout
            self.snap.lifecycle = PlayerLifecycle.KO
            self.snap.permadeath_started_at = None

        if penalty.reraise_lockout_seconds > 0:
            self.snap.reraise_locked_until = (
                event.timestamp + penalty.reraise_lockout_seconds
            )
        else:
            self.snap.reraise_locked_until = None

        return penalty

    def notify_instance_evict_timer_expired(self,
                                              now: float = 0.0) -> bool:
        """3 minutes elapsed without in-instance Raise → warp out + start
        permadeath countdown.

        Returns True if eviction happened (state transitioned)."""
        if self.snap.lifecycle != PlayerLifecycle.KO_INSTANCE:
            return False
        if self.snap.instance_evict_at is None:
            return False
        if now < self.snap.instance_evict_at:
            return False    # timer hasn't expired yet

        # Evicted from instance
        self.snap.instance_evict_at = None
        self.snap.instance_id = None

        # Now start the post-instance death pipeline (lvl 30+ → permadeath)
        if _compute_penalty(self.snap.level).permadeath_timer_seconds > 0:
            self.snap.lifecycle = PlayerLifecycle.KO_PERMADEATH_TIMER
            self.snap.permadeath_started_at = now
        else:
            # Sub-permadeath: still KO but in the open world now
            self.snap.lifecycle = PlayerLifecycle.KO
            self.snap.permadeath_started_at = None
        return True

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
        self.snap.instance_evict_at = None
        self.snap.instance_id = None
        return True

    # ------------------------------------------------------------------
    # Permadeath timer expiration → Fomor transition
    # ------------------------------------------------------------------

    def notify_permadeath_timer_expired(self, now: float = 0.0) -> bool:
        """Called when the 1-hour permadeath timer expires.

        If the player is still KO_PERMADEATH_TIMER (not raised), they
        become a Fomor. Returns True if the transition happened.
        """
        if self.snap.lifecycle != PlayerLifecycle.KO_PERMADEATH_TIMER:
            return False
        if self.snap.permadeath_started_at is None:
            return False

        elapsed = now - self.snap.permadeath_started_at
        if elapsed < PERMADEATH_TIMER_SECONDS:
            return False    # timer hasn't expired yet

        self.snap.lifecycle = PlayerLifecycle.FOMOR
        self.snap.fomor_at = now
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.ALIVE

    def is_in_instance_ko(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.KO_INSTANCE

    def is_in_permadeath_timer(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER

    def time_until_permadeath(self, now: float = 0.0) -> t.Optional[float]:
        """Seconds remaining on permadeath timer, or None if not active."""
        if self.snap.lifecycle != PlayerLifecycle.KO_PERMADEATH_TIMER:
            return None
        if self.snap.permadeath_started_at is None:
            return None
        elapsed = now - self.snap.permadeath_started_at
        remaining = PERMADEATH_TIMER_SECONDS - elapsed
        return max(0.0, remaining)

    def time_until_instance_evict(self, now: float = 0.0) -> t.Optional[float]:
        """Seconds remaining in the 3-min in-instance revive window."""
        if self.snap.lifecycle != PlayerLifecycle.KO_INSTANCE:
            return None
        if self.snap.instance_evict_at is None:
            return None
        return max(0.0, self.snap.instance_evict_at - now)

    def is_fomor(self) -> bool:
        return self.snap.lifecycle == PlayerLifecycle.FOMOR
