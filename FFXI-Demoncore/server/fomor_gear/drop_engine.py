"""The 3%-per-piece roll loop with anti-farming protections.

When a player kills a fomor, every piece the fomor was wearing rolls
INDEPENDENTLY at the base drop rate (3%) modified by:
- Per-fomor cooldown (1hr per spawn point)
- Per-killer daily limit (3 successful drops/day)
- Session diminishing returns (3% -> 2% -> 1.5% -> 1% -> 0.5% -> 0.25% ...)
- Killer eligibility (level/job/race/affinity match)

Each successful roll generates the piece at fomor_tier + 1 (cap +V).
The piece is then handed to the killer; the wardrobe loses it. Pieces
that fail the roll are removed from the wardrobe and 'returned to
world' (per the doc's loss-condition rule).
"""
from __future__ import annotations

import dataclasses
import random
import typing as t

from .lineage import GearPiece, GearTier, HolderType, LineageEvent
from .wardrobe import FomorWardrobe

# ----------------------------------------------------------------------
# Tuning constants
# ----------------------------------------------------------------------

BASE_DROP_RATE = 0.03                         # 3% per piece, per kill
DAILY_DROP_LIMIT = 3                          # successful drops/day/player
DAY_SECONDS = 24 * 3600
PER_FOMOR_COOLDOWN_SECONDS = 3600             # 1hr between fomor respawns at point
# Session diminishing returns. After N successful drops in this session,
# rate is SESSION_DR_RATES[min(N, len-1)].
SESSION_DR_RATES = [0.030, 0.020, 0.015, 0.010, 0.005, 0.0025]


# ----------------------------------------------------------------------
# Killer profile
# ----------------------------------------------------------------------

@dataclasses.dataclass
class KillerSnapshot:
    """The state we need about a killer to make drop decisions.

    successful_drops_history is a rolling list of timestamps for the
    daily-limit check. session_drop_count is the count of successful
    drops since last logout (resets on logout)."""
    killer_id: str
    level: int
    job: str
    sub_job: t.Optional[str] = None
    race: t.Optional[str] = None
    elemental_affinity: t.Optional[str] = None
    successful_drops_history: list[float] = dataclasses.field(default_factory=list)
    session_drop_count: int = 0


@dataclasses.dataclass
class DropResult:
    """Outcome of attempt_drops()."""
    pieces_dropped: list[GearPiece]
    pieces_failed_roll: list[GearPiece]
    pieces_skipped_ineligible: list[GearPiece]
    daily_limit_hit: bool                      # if True, no rolls happened
    fomor_on_cooldown: bool                    # spawn point cooldown blocked drops
    next_session_rate: float                   # rate that would apply on next roll


# ----------------------------------------------------------------------
# Eligibility
# ----------------------------------------------------------------------

class EligibilityChecker:
    """Static methods for the can-this-killer-equip-this-piece check.
    Anti-griefing: a level-30 char who kills a level-90 fomor doesn't
    roll for relic gear they can't use."""

    @staticmethod
    def can_equip(piece: GearPiece, killer: KillerSnapshot) -> bool:
        req = piece.template.requirements
        if killer.level < req.min_level:
            return False
        if req.job is not None and killer.job != req.job and killer.sub_job != req.job:
            return False
        if req.sub_job is not None and killer.sub_job != req.sub_job:
            return False
        if req.race is not None and killer.race != req.race:
            return False
        if (req.elemental_affinity is not None
                and killer.elemental_affinity != req.elemental_affinity):
            return False
        return True


# ----------------------------------------------------------------------
# Per-spawn-point cooldown tracker
# ----------------------------------------------------------------------

class FomorSpawnCooldownTracker:
    """Tracks last-kill timestamps per fomor spawn point. After a fomor
    is killed, that spawn point is on a 1hr cooldown — no fresh fomor
    spawns there until the cooldown elapses."""

    def __init__(self) -> None:
        self._last_kill: dict[str, float] = {}

    def is_on_cooldown(self, spawn_id: str, *, now: float) -> bool:
        last = self._last_kill.get(spawn_id)
        if last is None:
            return False
        return (now - last) < PER_FOMOR_COOLDOWN_SECONDS

    def time_remaining(self, spawn_id: str, *, now: float) -> float:
        last = self._last_kill.get(spawn_id)
        if last is None:
            return 0.0
        elapsed = now - last
        if elapsed >= PER_FOMOR_COOLDOWN_SECONDS:
            return 0.0
        return PER_FOMOR_COOLDOWN_SECONDS - elapsed

    def record_kill(self, spawn_id: str, *, now: float) -> None:
        self._last_kill[spawn_id] = now


# ----------------------------------------------------------------------
# Drop engine
# ----------------------------------------------------------------------

def _session_rate(session_drops: int) -> float:
    """Diminishing-returns rate for the Nth drop in this session."""
    if session_drops < 0:
        session_drops = 0
    if session_drops >= len(SESSION_DR_RATES):
        return SESSION_DR_RATES[-1]
    return SESSION_DR_RATES[session_drops]


def _prune_history(history: list[float], *, now: float,
                   window_seconds: float = DAY_SECONDS) -> None:
    cutoff = now - window_seconds
    while history and history[0] < cutoff:
        history.pop(0)


class DropEngine:
    """Roll fomor drops with anti-farming protections."""

    def __init__(self,
                  *,
                  rng: t.Optional[random.Random] = None,
                  cooldown_tracker: t.Optional[FomorSpawnCooldownTracker] = None) -> None:
        self.rng = rng or random.Random()
        self.cooldown_tracker = cooldown_tracker or FomorSpawnCooldownTracker()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def attempt_drops(self,
                       *,
                       killer: KillerSnapshot,
                       fomor: FomorWardrobe,
                       fomor_spawn_id: str,
                       now: float) -> DropResult:
        """Run the per-piece roll loop. Mutates the killer's history /
        session counters and the wardrobe in place. Returns DropResult."""
        # Anti-farming: per-killer daily limit check
        _prune_history(killer.successful_drops_history, now=now)
        daily_limit_hit = (
            len(killer.successful_drops_history) >= DAILY_DROP_LIMIT)

        if daily_limit_hit:
            return DropResult(
                pieces_dropped=[], pieces_failed_roll=[],
                pieces_skipped_ineligible=[],
                daily_limit_hit=True,
                fomor_on_cooldown=False,
                next_session_rate=_session_rate(killer.session_drop_count),
            )

        # Anti-farming: per-spawn-point cooldown gate. The cooldown
        # affects whether the fomor was even allowed to be killed at
        # this spawn point. We record the kill regardless so future
        # spawns at this point are blocked for 1hr.
        on_cooldown = self.cooldown_tracker.is_on_cooldown(fomor_spawn_id, now=now)

        # Roll each piece
        dropped: list[GearPiece] = []
        failed: list[GearPiece] = []
        ineligible: list[GearPiece] = []

        for piece in list(fomor.pieces):
            if not EligibilityChecker.can_equip(piece, killer):
                ineligible.append(piece)
                continue

            rate = _session_rate(killer.session_drop_count)
            roll = self.rng.random()
            if roll < rate and not on_cooldown:
                # Successful drop -> escalate to next tier, hand to killer
                piece.tier = piece.next_tier()
                piece.current_holder = killer.killer_id
                piece.current_holder_type = HolderType.PLAYER
                piece.append_lineage(LineageEvent(
                    timestamp=now,
                    holder_id=killer.killer_id,
                    holder_type=HolderType.PLAYER,
                    event="looted_from_fomor",
                    detail=f"tier -> {piece.tier.name}",
                ))
                fomor.remove(piece)
                killer.session_drop_count += 1
                killer.successful_drops_history.append(now)
                dropped.append(piece)

                # Re-check daily limit between rolls so a killer who
                # hits the limit mid-fomor stops getting drops.
                if len(killer.successful_drops_history) >= DAILY_DROP_LIMIT:
                    # Remaining pieces stay in wardrobe; they aren't
                    # 'failed' rolls — they were never rolled.
                    break
            else:
                # Roll failed -> piece is lost from the wardrobe per
                # the recursion-miss loss condition
                fomor.return_to_world(piece, now=now,
                                       reason="recursion_miss")
                failed.append(piece)

        # Cooldown the spawn point regardless of whether anything dropped
        self.cooldown_tracker.record_kill(fomor_spawn_id, now=now)

        return DropResult(
            pieces_dropped=dropped,
            pieces_failed_roll=failed,
            pieces_skipped_ineligible=ineligible,
            daily_limit_hit=False,
            fomor_on_cooldown=on_cooldown,
            next_session_rate=_session_rate(killer.session_drop_count),
        )

    @staticmethod
    def notify_session_logout(killer: KillerSnapshot) -> None:
        """Reset the session diminishing-returns counter on logout/login."""
        killer.session_drop_count = 0
