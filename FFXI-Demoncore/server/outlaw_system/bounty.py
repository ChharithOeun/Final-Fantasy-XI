"""Outlaw flag + bounty arithmetic + cleanse paths.

Single source of truth for whether someone is an outlaw and how much
gil their head is worth.

Same-race kill detection collapses civilized races (hume/elvaan/taru/
mithra/galka) into a single FactionRace.CIVILIZED bucket — the doc
says they count as one race for outlaw purposes. Goblins, orcs,
yagudo, quadav, sahagin etc. are each their own race.

Bounty math (from PVP_GLOBAL_OUTLAWS.md):
    bounty_per_kill = 1000 × victim_level × (1 + same_race_kills_in_24h × 0.25)

Cleanse paths:
    - Get killed by a bounty hunter (full bounty paid; standard
      permadeath loop applies — outlaw fomors are a thing)
    - Pay off bounty at registrar (2× bounty in gil + long quest)
    - Pardon quest per nation (real-time weeks)
    - Monastic seclusion (log off 30 real days; bounty wiped)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

BOUNTY_BASE_PER_LEVEL = 1000              # 1000 gil × victim_level
BOUNTY_ESCALATION_PER_24H_KILL = 0.25     # +25% per prior same-race kill in 24h
BOUNTY_PAYOFF_MULTIPLIER = 2.0            # registrar charges 2× bounty to clear
MONASTIC_SECLUSION_SECONDS = 30 * 86400   # log off 30 real days
NATION_WIPE_THRESHOLD = 5                 # 5 NPC kills in same nation/day = guards harder
REJOINDER_KILL_THRESHOLD = 3              # killed same victim 3+ times in window
REJOINDER_WINDOW_SECONDS = 4 * 3600       # 4 hours
REJOINDER_TRACKER_SECONDS = 30 * 60       # victim's tracker buff: 30 min
KILL_COUNT_WINDOW_SECONDS = 24 * 3600     # 24h rolling window for escalation premium

OUTLAW_SAFE_HAVENS = frozenset({"norg", "selbina", "mhaura"})
GATED_NATION_CITIES = frozenset({"bastok", "sandoria", "windurst", "jeuno",
                                  "ahturhgan", "whitegate"})


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------

class FactionRace(str, enum.Enum):
    """Race buckets for the same-race outlaw rule.

    Civilized races (the five humanoid playable races + civilian NPCs)
    collapse into CIVILIZED — that's the rule from the design doc.
    """
    CIVILIZED = "civilized"
    GOBLIN = "goblin"
    ORC = "orc"
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    SAHAGIN = "sahagin"
    TONBERRY = "tonberry"
    SHADOW = "shadow"           # shadowy creatures
    DEMON = "demon"
    BEAST = "beast"             # wild fauna (often considered same-race per family)
    OUTLAW = "outlaw"            # outlaw-faction members; outlaw vs outlaw is cross-faction


class OutlawStatus(str, enum.Enum):
    CITIZEN = "citizen"
    FLAGGED = "flagged"
    PARDONED = "pardoned"


# ----------------------------------------------------------------------
# Snapshot + result
# ----------------------------------------------------------------------

@dataclasses.dataclass
class BountySnapshot:
    """Per-actor bounty + outlaw state. Persisted by the caller."""
    actor_id: str
    race: FactionRace = FactionRace.CIVILIZED
    home_nation: str = "bastok"
    status: OutlawStatus = OutlawStatus.CITIZEN
    bounty_value: int = 0
    last_kill_at: t.Optional[float] = None

    # Rolling history for arithmetic. Each entry is a kill timestamp.
    # Pruned by _prune_history when older than KILL_COUNT_WINDOW_SECONDS.
    same_race_kill_history: list[float] = dataclasses.field(default_factory=list)

    # Per-victim history for the rejoinder (anti-spawn-camp) mechanic.
    # victim_id -> list of kill timestamps.
    kills_per_victim: dict[str, list[float]] = dataclasses.field(default_factory=dict)

    # Per-nation NPC kill history for the anti-nation-wipe mechanic.
    # nation -> list of NPC kill timestamps.
    npc_kills_per_nation: dict[str, list[float]] = dataclasses.field(
        default_factory=dict)

    # Long-running cleanse state
    pardon_quest_completed: bool = False
    monastic_seclusion_started_at: t.Optional[float] = None


@dataclasses.dataclass
class KillResult:
    """The outcome of a notify_kill call."""
    is_same_race: bool
    became_outlaw_now: bool
    bounty_minted: int           # 0 for cross-race
    new_total_bounty: int
    rejoinder_applied: bool      # this kill triggered the spawn-camp escalator
    nation_wipe_aggro_triggered: bool   # this kill pushed the NPC-killer past threshold
    victim_tracker_active: bool  # victim should get the 30-min map-tracker buff


# ----------------------------------------------------------------------
# Tracker
# ----------------------------------------------------------------------

class BountyTracker:
    """Operates on a BountySnapshot in place. Construct with the snapshot,
    call notify_kill / pay_off_bounty / complete_pardon_quest /
    monastic_seclusion as events happen, and use the read-helpers to
    drive aggro / vendor / quest gates."""

    def __init__(self, snapshot: BountySnapshot) -> None:
        self.snapshot = snapshot

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def notify_kill(self,
                     *,
                     victim_id: str,
                     victim_race: FactionRace,
                     victim_level: int,
                     victim_is_npc: bool = False,
                     victim_nation: t.Optional[str] = None,
                     now: float = 0) -> KillResult:
        """Process a kill and update outlaw + bounty state. Returns
        the result with all derived flags."""
        is_same_race = self._same_race(self.snapshot.race, victim_race)

        # Cross-race kill: legitimate XP, no outlaw consequences.
        if not is_same_race:
            return KillResult(
                is_same_race=False,
                became_outlaw_now=False,
                bounty_minted=0,
                new_total_bounty=self.snapshot.bounty_value,
                rejoinder_applied=False,
                nation_wipe_aggro_triggered=False,
                victim_tracker_active=False,
            )

        # Same-race kill. Outlaw flagging + bounty math.
        was_citizen_before = (self.snapshot.status == OutlawStatus.CITIZEN
                               or self.snapshot.status == OutlawStatus.PARDONED)
        if was_citizen_before:
            self.snapshot.status = OutlawStatus.FLAGGED

        # Prune the rolling 24h history before counting
        self._prune_history(self.snapshot.same_race_kill_history,
                            now=now,
                            window_seconds=KILL_COUNT_WINDOW_SECONDS)
        prior_24h_kills = len(self.snapshot.same_race_kill_history)

        # Per-victim history (rejoinder)
        victim_history = self.snapshot.kills_per_victim.setdefault(victim_id, [])
        self._prune_history(victim_history, now=now,
                            window_seconds=REJOINDER_WINDOW_SECONDS)
        rejoinder_applied = len(victim_history) >= REJOINDER_KILL_THRESHOLD

        # Bounty math
        escalation = 1.0 + prior_24h_kills * BOUNTY_ESCALATION_PER_24H_KILL
        if rejoinder_applied:
            escalation *= 2.0
        bounty = int(BOUNTY_BASE_PER_LEVEL * victim_level * escalation)
        self.snapshot.bounty_value += bounty

        # Record kill
        self.snapshot.same_race_kill_history.append(now)
        victim_history.append(now)
        self.snapshot.last_kill_at = now

        # Anti-nation-wipe: only counts NPC kills in a specific nation
        nation_wipe_triggered = False
        if victim_is_npc and victim_nation is not None:
            nation_history = self.snapshot.npc_kills_per_nation.setdefault(
                victim_nation, [])
            self._prune_history(nation_history, now=now,
                                 window_seconds=KILL_COUNT_WINDOW_SECONDS)
            nation_history.append(now)
            if len(nation_history) >= NATION_WIPE_THRESHOLD:
                nation_wipe_triggered = True

        return KillResult(
            is_same_race=True,
            became_outlaw_now=was_citizen_before,
            bounty_minted=bounty,
            new_total_bounty=self.snapshot.bounty_value,
            rejoinder_applied=rejoinder_applied,
            nation_wipe_aggro_triggered=nation_wipe_triggered,
            # Victim's tracker buff fires on rejoinder threshold
            victim_tracker_active=rejoinder_applied,
        )

    def pay_off_bounty(self, gil_paid: int) -> bool:
        """Pay 2× current bounty at the regional registrar to clear.
        Returns True if cleared, False if underpaid."""
        cost = int(self.snapshot.bounty_value * BOUNTY_PAYOFF_MULTIPLIER)
        if gil_paid < cost:
            return False
        self.snapshot.bounty_value = 0
        self.snapshot.status = OutlawStatus.PARDONED
        return True

    def complete_pardon_quest(self) -> bool:
        """The pardon questline ran to completion. Bounty wiped, status
        becomes PARDONED. Returns True if the cleanse succeeded."""
        self.snapshot.bounty_value = 0
        self.snapshot.status = OutlawStatus.PARDONED
        self.snapshot.pardon_quest_completed = True
        return True

    def begin_monastic_seclusion(self, now: float) -> None:
        """Player has logged out and we mark the seclusion start. Call
        check_monastic_seclusion at login to see if the timer cleared."""
        self.snapshot.monastic_seclusion_started_at = now

    def check_monastic_seclusion(self, now: float) -> bool:
        """If the player has been logged off for >= 30 real days, wipe
        the bounty. Returns True if the seclusion cleansed."""
        started = self.snapshot.monastic_seclusion_started_at
        if started is None:
            return False
        if (now - started) < MONASTIC_SECLUSION_SECONDS:
            return False
        self.snapshot.bounty_value = 0
        self.snapshot.status = OutlawStatus.PARDONED
        self.snapshot.monastic_seclusion_started_at = None
        return True

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    def is_outlaw(self) -> bool:
        return self.snapshot.status == OutlawStatus.FLAGGED

    def is_safe_in(self, zone: str) -> bool:
        """Is the outlaw safe from guard aggro in this zone?"""
        z = zone.lower()
        if z in OUTLAW_SAFE_HAVENS:
            return True
        # Open-world zones: not safe per se (open-season aggro from
        # everyone), but no nation-guard aggro
        if z not in GATED_NATION_CITIES:
            return True
        return False

    def payoff_cost(self) -> int:
        """How much gil the registrar charges to clear the slate."""
        return int(self.snapshot.bounty_value * BOUNTY_PAYOFF_MULTIPLIER)

    def is_on_bounty_board(self, threshold: int = 50_000) -> bool:
        """Bounty board lists outlaws above a threshold (default 50k)."""
        return (self.snapshot.status == OutlawStatus.FLAGGED
                and self.snapshot.bounty_value >= threshold)

    def kills_in_24h(self, now: float) -> int:
        """How many same-race kills in the last 24 hours."""
        self._prune_history(self.snapshot.same_race_kill_history,
                            now=now,
                            window_seconds=KILL_COUNT_WINDOW_SECONDS)
        return len(self.snapshot.same_race_kill_history)

    def victim_tracker_remaining(self, victim_id: str, now: float) -> float:
        """Time remaining on the victim's map-tracker buff after a
        rejoinder kill."""
        history = self.snapshot.kills_per_victim.get(victim_id, [])
        if not history:
            return 0.0
        last = max(history)
        elapsed = now - last
        if elapsed >= REJOINDER_TRACKER_SECONDS:
            return 0.0
        return REJOINDER_TRACKER_SECONDS - elapsed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _same_race(a: FactionRace, b: FactionRace) -> bool:
        """Same-race check. The OUTLAW faction is treated as a separate
        race — outlaw vs outlaw is cross-faction (the most legal PvP
        available in the game per the doc)."""
        if a == FactionRace.OUTLAW or b == FactionRace.OUTLAW:
            return False
        return a == b

    @staticmethod
    def _prune_history(history: list[float], *, now: float,
                       window_seconds: float) -> None:
        """Remove timestamps older than the window. Mutates in place."""
        cutoff = now - window_seconds
        # Walk from the front; history is roughly chronological.
        while history and history[0] < cutoff:
            history.pop(0)
