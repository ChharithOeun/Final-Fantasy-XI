"""Active sign-session lifecycle.

Per NIN_HAND_SIGNS.md NIN-specific weight rules:
- Movement has NO penalty on seal speed (walking/running/sprinting/
  rolling/jumping all step_multiplier 1.00 — already encoded in
  weight_physics).
- Damage taken during seal sequence has a fixed 10% chance per hit
  to break the sequence (regardless of damage magnitude).
- Sequence pauses if interrupted and CAN RESUME from the same seal
  index if combat clears within 1.5 seconds.

The sign-session manages this state: ACTIVE -> (PAUSED -> ACTIVE | EXPIRED)
                                              -> COMPLETE
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t

from .seals import Seal
from .sequences import (
    DEFAULT_SEAL_TIME_SECONDS,
    NINJUTSU_SEQUENCES,
    sequence_for,
)


DAMAGE_INTERRUPT_CHANCE = 0.10
RESUME_WINDOW_SECONDS = 1.5


class SignState(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"          # past resume window — cast lost
    COMPLETE = "complete"
    CANCELED = "canceled"


@dataclasses.dataclass
class NinSignSession:
    """A single in-progress hand-sign sequence."""
    session_id: str
    caster_id: str
    spell: str
    sequence: list[Seal]
    started_at: float
    seal_time_seconds: float = DEFAULT_SEAL_TIME_SECONDS
    state: SignState = SignState.ACTIVE
    seal_index: int = 0           # how many seals are completed
    paused_at: t.Optional[float] = None
    # Time spent in PAUSED state, accumulated; subtracted from elapsed-time
    # math so an interrupted+resumed sequence doesn't 'auto-advance'.
    pause_accumulated: float = 0.0

    def is_finished(self) -> bool:
        return self.state in (SignState.COMPLETE, SignState.EXPIRED,
                               SignState.CANCELED)


@dataclasses.dataclass
class SignTick:
    """Per-tick observation: what changed since last tick."""
    seal_index: int
    state: SignState
    visible_seals: list[Seal]


class NinSignManager:
    """Owns the live signing sessions.

    Caller drives the lifecycle:
        begin_signing(spell, caster_id, now) -> session
        tick(session_id, now) -> SignTick     # advances seal_index
        notify_damage_taken(session_id, now, rng=None)
        attempt_resume(session_id, now) -> bool
        cancel(session_id) -> bool
    """

    def __init__(self, *, rng: t.Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._sessions: dict[str, NinSignSession] = {}
        self._next_seq = 0

    # ------------------------------------------------------------------
    # Lifecycle mutators
    # ------------------------------------------------------------------

    def begin_signing(self,
                       *,
                       spell: str,
                       caster_id: str,
                       now: float,
                       seal_time_seconds: float = DEFAULT_SEAL_TIME_SECONDS,
                       ) -> NinSignSession:
        """Start a fresh sign session for `spell` on `caster_id`."""
        seq = sequence_for(spell)
        if seq is None:
            raise KeyError(f"unknown ninjutsu spell: {spell}")
        session = NinSignSession(
            session_id=self._mint_id(),
            caster_id=caster_id,
            spell=spell.lower(),
            sequence=list(seq),
            started_at=now,
            seal_time_seconds=seal_time_seconds,
        )
        self._sessions[session.session_id] = session
        return session

    def tick(self, session_id: str, *, now: float) -> SignTick:
        """Advance the seal_index based on elapsed time. Marks
        COMPLETE when all seals are formed."""
        session = self._sessions[session_id]
        if session.state == SignState.ACTIVE:
            elapsed = now - session.started_at - session.pause_accumulated
            # Float-safe seal index: divide then floor with a small
            # epsilon to avoid 0.45/0.15 = 2.999... -> 2
            ratio = elapsed / session.seal_time_seconds
            target_idx = int(ratio + 1e-9)
            target_idx = max(0, min(target_idx, len(session.sequence)))
            session.seal_index = target_idx
            if session.seal_index >= len(session.sequence):
                session.state = SignState.COMPLETE

        return SignTick(
            seal_index=session.seal_index,
            state=session.state,
            visible_seals=session.sequence[:session.seal_index],
        )

    def notify_damage_taken(self,
                              session_id: str,
                              *,
                              now: float,
                              rng: t.Optional[random.Random] = None,
                              ) -> bool:
        """Roll the 10% damage-interrupt. Returns True if the session
        was paused. ACTIVE only — damage to a paused session has no
        further effect (it's already paused)."""
        session = self._sessions.get(session_id)
        if session is None or session.state != SignState.ACTIVE:
            return False
        roll_rng = rng or self._rng
        if roll_rng.random() < DAMAGE_INTERRUPT_CHANCE:
            session.state = SignState.PAUSED
            session.paused_at = now
            return True
        return False

    def attempt_resume(self, session_id: str, *, now: float) -> bool:
        """Try to resume a PAUSED session. Returns False if the resume
        window has elapsed (state -> EXPIRED) or if the session isn't
        paused."""
        session = self._sessions.get(session_id)
        if session is None or session.state != SignState.PAUSED:
            return False
        assert session.paused_at is not None
        if (now - session.paused_at) > RESUME_WINDOW_SECONDS:
            session.state = SignState.EXPIRED
            return False
        # Resume: track the pause duration so seal_index doesn't
        # auto-advance past where we left off.
        session.pause_accumulated += now - session.paused_at
        session.paused_at = None
        session.state = SignState.ACTIVE
        return True

    def expire_if_window_passed(self, session_id: str, *,
                                  now: float) -> bool:
        """Caller can periodically check paused sessions and force
        EXPIRED if the resume window passed without a resume attempt.
        Returns True if expired."""
        session = self._sessions.get(session_id)
        if session is None or session.state != SignState.PAUSED:
            return False
        assert session.paused_at is not None
        if (now - session.paused_at) > RESUME_WINDOW_SECONDS:
            session.state = SignState.EXPIRED
            return True
        return False

    def cancel(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.is_finished():
            return False
        session.state = SignState.CANCELED
        return True

    def get(self, session_id: str) -> t.Optional[NinSignSession]:
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def visible_seals(self, session_id: str) -> list[Seal]:
        """Seals an observer would have seen by now."""
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return session.sequence[:session.seal_index]

    def progress_pct(self, session_id: str) -> float:
        session = self._sessions.get(session_id)
        if session is None or len(session.sequence) == 0:
            return 0.0
        return min(1.0, session.seal_index / len(session.sequence))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mint_id(self) -> str:
        self._next_seq += 1
        return f"sign_{self._next_seq:08d}"
