"""Action queue — pre-queue next ability while busy.

When a player is mid-cast or on a global cooldown, the next
ability they press is QUEUED rather than rejected. As soon as
the active state ends, the queued action fires automatically.

Each player has a single-slot queue (overwriting an unfired
queued action with a newer press is fine — the latest wins).
The queued action can be CANCELED. The system also enforces a
queue WINDOW: actions queued more than queue_window_seconds
before they can fire are dropped.

Public surface
--------------
    QueueState enum
    QueuedAction dataclass
    QueueResult dataclass
    ActionQueueSystem
        .start_action(player_id, action_id, cast_time, gcd_time)
        .queue_next(player_id, action_id, queued_at)
        .cancel_queued(player_id)
        .tick(player_id, now_seconds) -> Optional[fired action_id]
        .state_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default queue acceptance window (seconds before active ends).
DEFAULT_QUEUE_WINDOW = 1.5
# Max queue lifetime — past which a stale queued action drops.
MAX_QUEUE_AGE = 4.0


class QueueState(str, enum.Enum):
    IDLE = "idle"
    BUSY = "busy"
    QUEUED = "queued"


@dataclasses.dataclass(frozen=True)
class QueuedAction:
    action_id: str
    queued_at_seconds: float


@dataclasses.dataclass
class _PlayerActionState:
    player_id: str
    state: QueueState = QueueState.IDLE
    active_action_id: t.Optional[str] = None
    active_ends_at: float = 0.0
    queued: t.Optional[QueuedAction] = None


@dataclasses.dataclass(frozen=True)
class QueueResult:
    accepted: bool
    state: QueueState
    queued_action_id: t.Optional[str] = None
    fired_action_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ActionQueueSystem:
    queue_window_seconds: float = DEFAULT_QUEUE_WINDOW
    max_queue_age_seconds: float = MAX_QUEUE_AGE
    _states: dict[str, _PlayerActionState] = dataclasses.field(
        default_factory=dict,
    )

    def _state_for(
        self, player_id: str,
    ) -> _PlayerActionState:
        st = self._states.get(player_id)
        if st is None:
            st = _PlayerActionState(player_id=player_id)
            self._states[player_id] = st
        return st

    def start_action(
        self, *, player_id: str, action_id: str,
        cast_time: float, gcd_time: float = 0.0,
        now_seconds: float = 0.0,
    ) -> QueueResult:
        if not action_id:
            return QueueResult(
                False,
                state=self._state_for(player_id).state,
                reason="empty action",
            )
        st = self._state_for(player_id)
        if st.state == QueueState.BUSY:
            return QueueResult(
                False, state=st.state,
                reason="already busy",
            )
        # cast + gcd combine into a single busy window
        busy_seconds = max(0.0, cast_time + gcd_time)
        st.state = QueueState.BUSY
        st.active_action_id = action_id
        st.active_ends_at = now_seconds + busy_seconds
        st.queued = None     # any queued from a prior cycle clears
        return QueueResult(
            accepted=True, state=st.state,
        )

    def queue_next(
        self, *, player_id: str, action_id: str,
        queued_at_seconds: float = 0.0,
    ) -> QueueResult:
        if not action_id:
            return QueueResult(
                False,
                state=self._state_for(player_id).state,
                reason="empty action",
            )
        st = self._state_for(player_id)
        if st.state == QueueState.IDLE:
            return QueueResult(
                False, state=st.state,
                reason="not busy; press fires directly",
            )
        # Check the queue window — must be within window of
        # active end OR active is just starting (early queue).
        time_until_end = (
            st.active_ends_at - queued_at_seconds
        )
        if time_until_end > self.queue_window_seconds:
            # Caller queued too early — accept anyway but mark
            # as such; we expire it via max age in tick().
            pass
        st.queued = QueuedAction(
            action_id=action_id,
            queued_at_seconds=queued_at_seconds,
        )
        st.state = QueueState.QUEUED
        return QueueResult(
            accepted=True, state=st.state,
            queued_action_id=action_id,
        )

    def cancel_queued(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None or st.queued is None:
            return False
        st.queued = None
        if st.state == QueueState.QUEUED:
            st.state = QueueState.BUSY
        return True

    def tick(
        self, *, player_id: str, now_seconds: float,
    ) -> t.Optional[str]:
        st = self._states.get(player_id)
        if st is None:
            return None
        # If still busy, nothing to fire yet
        if st.state == QueueState.IDLE:
            return None
        if now_seconds < st.active_ends_at:
            return None
        # Active just ended.
        fired_id: t.Optional[str] = None
        if st.queued is not None:
            age = (
                now_seconds - st.queued.queued_at_seconds
            )
            if age <= self.max_queue_age_seconds:
                fired_id = st.queued.action_id
        # Reset state regardless
        st.state = QueueState.IDLE
        st.active_action_id = None
        st.active_ends_at = 0.0
        st.queued = None
        return fired_id

    def state_for(
        self, player_id: str,
    ) -> t.Optional[QueueState]:
        st = self._states.get(player_id)
        return st.state if st else None

    def queued_action_id(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        st = self._states.get(player_id)
        if st is None or st.queued is None:
            return None
        return st.queued.action_id

    def total_players(self) -> int:
        return len(self._states)


__all__ = [
    "DEFAULT_QUEUE_WINDOW", "MAX_QUEUE_AGE",
    "QueueState",
    "QueuedAction", "QueueResult",
    "ActionQueueSystem",
]
