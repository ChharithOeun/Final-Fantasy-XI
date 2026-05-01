"""AFK + macro-bot detection.

A player is `AFK` if their behavior fails THREE checks simultaneously
for a configurable threshold (default 5 minutes):

1. **Position diversity**: are they actually moving around, or stuck
   in a 2-meter radius?
2. **Action diversity**: are they using >1 distinct skill, or just
   one skill on a loop?
3. **Pattern entropy**: are their action timestamps regularly-spaced
   (macro-loop signature), or human-irregular?

Each check is independent. AFK requires ALL three to fail. A skilled
single-target farmer who's actively kiting a mob won't trigger
because their position is changing even if their skill rotation is
narrow.

Returns AFKState transitions: ACTIVE → SUSPECTED → CONFIRMED. Once
CONFIRMED, the FomorSpawnPolicy queues a Fomor-party encounter on
the player.
"""
from __future__ import annotations

import dataclasses
import enum
import math
import statistics
import typing as t


class AFKState(str, enum.Enum):
    ACTIVE = "active"            # confirmed legitimate activity
    SUSPECTED = "suspected"       # at least one check failing
    CONFIRMED = "confirmed"       # all three checks failed > threshold


@dataclasses.dataclass
class PlayerActivity:
    """One activity event from the player. The detector consumes a
    stream of these."""
    player_id: str
    timestamp: float
    x_cm: float
    y_cm: float
    z_cm: float
    action_id: t.Optional[str] = None    # weapon skill id, spell id, etc
    is_movement: bool = False             # walked / ran / jumped


# Tuning constants
POSITION_RADIUS_CM = 200.0           # 2m: anything tighter = stuck
MIN_DISTINCT_ACTIONS = 2              # < this for the window = suspect
PATTERN_REGULARITY_THRESHOLD = 0.15   # std/mean ratio < this = macro

DEFAULT_AFK_WINDOW_SECONDS = 300.0    # 5 minutes
DEFAULT_AFK_CONFIRM_SECONDS = 300.0   # additional 5 min in SUSPECTED → CONFIRMED


@dataclasses.dataclass
class _PlayerHistory:
    activities: list[PlayerActivity] = dataclasses.field(default_factory=list)
    state: AFKState = AFKState.ACTIVE
    suspected_at: t.Optional[float] = None
    confirmed_at: t.Optional[float] = None


class AFKDetector:
    """One detector instance can track many players."""

    def __init__(self, *,
                 afk_window_seconds: float = DEFAULT_AFK_WINDOW_SECONDS,
                 afk_confirm_seconds: float = DEFAULT_AFK_CONFIRM_SECONDS):
        self.afk_window = afk_window_seconds
        self.afk_confirm = afk_confirm_seconds
        self._players: dict[str, _PlayerHistory] = {}

    def observe(self, activity: PlayerActivity) -> AFKState:
        """Record an activity event. Returns the player's current
        AFK state."""
        h = self._players.setdefault(activity.player_id, _PlayerHistory())
        h.activities.append(activity)

        # Trim the rolling window to the most recent afk_window seconds
        cutoff = activity.timestamp - self.afk_window
        h.activities = [a for a in h.activities if a.timestamp >= cutoff]

        new_state = self._evaluate(h, now=activity.timestamp)
        self._transition(h, new_state, now=activity.timestamp)
        return h.state

    def state_of(self, player_id: str) -> AFKState:
        h = self._players.get(player_id)
        return h.state if h else AFKState.ACTIVE

    def reset(self, player_id: str) -> None:
        """Clear state — used when player logs out."""
        self._players.pop(player_id, None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate(self, h: _PlayerHistory, now: float) -> AFKState:
        """Evaluate the three checks against the activity window."""
        if not h.activities:
            return AFKState.ACTIVE

        window_seconds = now - h.activities[0].timestamp
        if window_seconds < self.afk_window * 0.6:
            # Not enough data yet
            return AFKState.ACTIVE

        position_stuck = self._is_position_stuck(h.activities)
        actions_repetitive = self._is_actions_repetitive(h.activities)
        timing_macro_like = self._is_timing_macro_like(h.activities)

        failed_checks = sum([position_stuck, actions_repetitive, timing_macro_like])
        if failed_checks == 3:
            return AFKState.SUSPECTED   # initial suspicion; needs confirm window
        return AFKState.ACTIVE

    def _transition(self, h: _PlayerHistory, new_state: AFKState,
                     now: float) -> None:
        """State machine transitions with confirm window."""
        # ACTIVE → SUSPECTED
        if h.state == AFKState.ACTIVE and new_state == AFKState.SUSPECTED:
            h.state = AFKState.SUSPECTED
            h.suspected_at = now
            return

        # SUSPECTED → CONFIRMED if afk_confirm seconds have elapsed
        if h.state == AFKState.SUSPECTED:
            if new_state == AFKState.ACTIVE:
                # Player did something legit — clear suspicion
                h.state = AFKState.ACTIVE
                h.suspected_at = None
                return
            if (h.suspected_at is not None
                    and now - h.suspected_at >= self.afk_confirm):
                h.state = AFKState.CONFIRMED
                h.confirmed_at = now

        # CONFIRMED stays confirmed until reset/legit-activity-stream
        if h.state == AFKState.CONFIRMED and new_state == AFKState.ACTIVE:
            # Strong signal of legit activity → clear
            h.state = AFKState.ACTIVE
            h.suspected_at = None
            h.confirmed_at = None

    @staticmethod
    def _is_position_stuck(activities: list[PlayerActivity]) -> bool:
        """All recorded positions within POSITION_RADIUS_CM of the first."""
        if not activities:
            return True
        cx, cy, cz = activities[0].x_cm, activities[0].y_cm, activities[0].z_cm
        for a in activities:
            dx = a.x_cm - cx
            dy = a.y_cm - cy
            dz = a.z_cm - cz
            if math.sqrt(dx * dx + dy * dy + dz * dz) > POSITION_RADIUS_CM:
                return False
        return True

    @staticmethod
    def _is_actions_repetitive(activities: list[PlayerActivity]) -> bool:
        """Distinct action_id count below threshold."""
        actions = {a.action_id for a in activities if a.action_id}
        return len(actions) < MIN_DISTINCT_ACTIONS

    @staticmethod
    def _is_timing_macro_like(activities: list[PlayerActivity]) -> bool:
        """Action timestamps too regular (low coefficient of variation)."""
        timestamps = [a.timestamp for a in activities if a.action_id]
        if len(timestamps) < 4:
            return False    # too few samples to judge timing
        intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
        if not intervals:
            return False
        mean = statistics.mean(intervals)
        if mean == 0:
            return True
        try:
            stdev = statistics.stdev(intervals)
        except statistics.StatisticsError:
            return False
        return (stdev / mean) < PATTERN_REGULARITY_THRESHOLD
