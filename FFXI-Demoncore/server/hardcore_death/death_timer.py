"""1-hour KO timer per HARDCORE_DEATH.md.

A character that dies has 1 real-time hour to be raised by another
player or NPC. If the timer expires, the character is permanently
lost to its owner — no /unstuck, no GM intervention, no second
chance. The character is then resurrected as a Fomor.

Raise paths that cancel the timer:
    - Raise / Raise II / Raise III
    - Tractor + raise
    - Raise scroll item
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Doc: '1 real-time hour'.
DEATH_TIMER_SECONDS: int = 3600


class DeathState(str, enum.Enum):
    KO = "ko"                              # within 1-hour window
    RAISED = "raised"                      # someone raised them
    EXPIRED = "expired"                    # timer ran out -> fomor pending
    OPTED_OUT = "opted_out"                # owner declined fomor at expiry


class RaiseSource(str, enum.Enum):
    """Doc-named raise paths."""
    RAISE_SPELL = "raise_spell"
    RAISE_II = "raise_ii"
    RAISE_III = "raise_iii"
    TRACTOR_THEN_RAISE = "tractor_then_raise"
    RAISE_SCROLL = "raise_scroll"


@dataclasses.dataclass
class DeathRecord:
    """One pending fomor candidate.

    The 1-hour timer is in real-time seconds (Vana'diel time mods
    don't apply — death is a real-world wall-clock thing).
    """
    char_id: str
    death_zone_id: str
    died_at: float
    state: DeathState = DeathState.KO
    raised_at: t.Optional[float] = None
    raised_by_source: t.Optional[RaiseSource] = None
    expires_at: float = 0.0

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.died_at + DEATH_TIMER_SECONDS

    def remaining_seconds(self, *, now: float) -> float:
        if self.state != DeathState.KO:
            return 0.0
        if now >= self.expires_at:
            return 0.0
        return self.expires_at - now

    def is_expired(self, *, now: float) -> bool:
        return self.state == DeathState.KO and now >= self.expires_at


def open_death_record(*,
                          char_id: str,
                          death_zone_id: str,
                          now: float
                          ) -> DeathRecord:
    """LSB calls this from onPlayerDeath. Per the doc the record
    persists to char_fomor_pending."""
    return DeathRecord(
        char_id=char_id, death_zone_id=death_zone_id, died_at=now,
    )


def apply_raise(record: DeathRecord,
                  *,
                  source: RaiseSource,
                  now: float) -> bool:
    """LSB calls this from onRaise. Returns True if the raise
    landed (record was in KO state and timer hadn't expired)."""
    if record.state != DeathState.KO:
        return False
    if record.is_expired(now=now):
        return False
    record.state = DeathState.RAISED
    record.raised_at = now
    record.raised_by_source = source
    return True


def maybe_expire(record: DeathRecord, *, now: float) -> bool:
    """fomorTimerExpire cron tick. Returns True if state advanced
    KO -> EXPIRED on this call."""
    if record.state != DeathState.KO:
        return False
    if record.is_expired(now=now):
        record.state = DeathState.EXPIRED
        return True
    return False


def opt_out_at_expiry(record: DeathRecord) -> bool:
    """Per doc open question 4: 'Should a fomor's owner get a
    one-time prompt at expiry to decline (toon goes to grave, no
    fomor spawns)? Probably yes — opt-out preserves player agency.'

    Caller invokes this if the owner declined the fomor flow.
    Returns True if the opt-out was honored.
    """
    if record.state != DeathState.EXPIRED:
        return False
    record.state = DeathState.OPTED_OUT
    return True
