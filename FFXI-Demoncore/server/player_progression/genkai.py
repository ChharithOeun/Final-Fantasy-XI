"""Genkai limit-break tests — 5 forced-solo rite-of-passage fights.

Per PLAYER_PROGRESSION.md: 'Each Genkai is a forced solo encounter.
No party allowed. This is the pure test of the player's skill, with
no carry from group play. Players who can't solo Maat at 70 don't
progress.'

  Genkai 1 (lvl 50 -> 55): Maat. Tests SC reading + intervention
                             timing + visible-health stage reading.
  Genkai 2 (55 -> 60): Konschtat NM. Tests weight-cycling + AOE dodge.
  Genkai 3 (60 -> 65): Pashhow NM. Tests 3x ailment-MB stack mechanic.
  Genkai 4 (65 -> 70): Tahrongi NM. Tests Tier-2 SCs + audible coord.
  Genkai 5 (70 -> 75): Maat rematch. Tests EVERYTHING; harder.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class GenkaiTest:
    """One Genkai limit-break test."""
    genkai_level: int                 # 1..5
    job_level_required: int           # current level cap to attempt
    next_level_cap: int               # cap unlocked on success
    test_zone: str
    test_npc: str
    tests: tuple[str, ...]            # named skill domains exercised
    is_solo_only: bool = True
    boss_mood: t.Optional[str] = None  # 'gruff' for Maat rematch
    notes: str = ""


GENKAI_TESTS: dict[int, GenkaiTest] = {
    1: GenkaiTest(
        genkai_level=1,
        job_level_required=50, next_level_cap=55,
        test_zone="horlais_peak", test_npc="maat",
        tests=("skillchain_reading", "intervention_timing",
                 "visible_health_stage_reading"),
        notes="The classic Genkai 1 — Maat's first test",
    ),
    2: GenkaiTest(
        genkai_level=2,
        job_level_required=55, next_level_cap=60,
        test_zone="konschtat_highlands", test_npc="konschtat_nm",
        tests=("weight_cycling", "aoe_telegraph_dodging"),
    ),
    3: GenkaiTest(
        genkai_level=3,
        job_level_required=60, next_level_cap=65,
        test_zone="pashhow_marshlands", test_npc="pashhow_nm",
        tests=("3x_ailment_mb_stack",),
        notes="Tests the apex CC pressure mechanic",
    ),
    4: GenkaiTest(
        genkai_level=4,
        job_level_required=65, next_level_cap=70,
        test_zone="tahrongi_canyon", test_npc="tahrongi_nm",
        tests=("tier_2_skillchains", "audible_coordination"),
    ),
    5: GenkaiTest(
        genkai_level=5,
        job_level_required=70, next_level_cap=75,
        test_zone="balgas_dais", test_npc="maat",
        tests=("skillchain_reading", "intervention_timing",
                 "weight_cycling", "aoe_telegraph_dodging",
                 "3x_ailment_mb_stack", "tier_2_skillchains",
                 "audible_coordination"),
        boss_mood="gruff",
        notes=("Maat remembers the first fight. Mood is gruff. "
                 "Tests EVERYTHING the player should have learned."),
    ),
}


@dataclasses.dataclass
class GenkaiAttempt:
    """One attempt record for the orchestrator log."""
    genkai_level: int
    actor_id: str
    attempted_at: float
    party_size_at_attempt: int        # caller fills this for solo check
    succeeded: t.Optional[bool] = None
    duration_seconds: t.Optional[float] = None


class GenkaiTestManager:
    """Owns the per-character Genkai progression. The combat pipeline
    notifies this manager when a player enters / passes / fails a
    Genkai battlefield."""

    def __init__(self) -> None:
        self._passed: dict[str, set[int]] = {}      # actor_id -> {1, 2, ...}

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    def can_attempt(self,
                     *,
                     actor_id: str,
                     job_level: int,
                     genkai_level: int) -> tuple[bool, str]:
        """Whether this player can attempt this Genkai. Returns
        (eligible, reason). Reason is empty on True."""
        test = GENKAI_TESTS.get(genkai_level)
        if test is None:
            return False, f"unknown genkai level {genkai_level}"
        if job_level < test.job_level_required:
            return False, (f"job level {test.job_level_required} required; "
                              f"have {job_level}")
        # Sequential: must have passed all previous Genkais
        passed = self._passed.get(actor_id, set())
        for prior in range(1, genkai_level):
            if prior not in passed:
                return False, f"must pass Genkai {prior} first"
        if genkai_level in passed:
            return False, f"Genkai {genkai_level} already passed"
        return True, ""

    def is_party_blocked(self,
                          *,
                          genkai_level: int,
                          party_size: int) -> bool:
        """Solo-only enforcement: party_size > 1 blocks the attempt
        for solo-only Genkais."""
        test = GENKAI_TESTS.get(genkai_level)
        if test is None:
            return False
        if test.is_solo_only and party_size > 1:
            return True
        return False

    # ------------------------------------------------------------------
    # Attempt flow
    # ------------------------------------------------------------------

    def attempt(self,
                  *,
                  actor_id: str,
                  job_level: int,
                  genkai_level: int,
                  party_size: int,
                  now: float) -> tuple[bool, str, t.Optional[GenkaiAttempt]]:
        """Try to start a Genkai attempt. Returns (allowed, reason, attempt)."""
        eligible, reason = self.can_attempt(
            actor_id=actor_id, job_level=job_level,
            genkai_level=genkai_level,
        )
        if not eligible:
            return False, reason, None
        if self.is_party_blocked(genkai_level=genkai_level,
                                    party_size=party_size):
            return False, "Genkai is solo-only; disband party first", None
        attempt = GenkaiAttempt(
            genkai_level=genkai_level, actor_id=actor_id,
            attempted_at=now, party_size_at_attempt=party_size,
        )
        return True, "", attempt

    def notify_passed(self,
                        *,
                        actor_id: str,
                        genkai_level: int) -> int:
        """Mark this Genkai passed. Returns the new level cap unlocked."""
        test = GENKAI_TESTS.get(genkai_level)
        if test is None:
            return 0
        self._passed.setdefault(actor_id, set()).add(genkai_level)
        return test.next_level_cap

    def notify_failed(self, attempt: GenkaiAttempt,
                        *,
                        now: float) -> None:
        """Stamp the failure onto the attempt record."""
        attempt.succeeded = False
        attempt.duration_seconds = now - attempt.attempted_at

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def passed_set(self, actor_id: str) -> set[int]:
        return set(self._passed.get(actor_id, set()))

    def current_level_cap(self,
                            *,
                            actor_id: str,
                            base_cap: int = 50) -> int:
        """The player's current level cap given the Genkais they've
        passed. base_cap is 50 (FFXI canonical pre-Genkai cap)."""
        passed = self._passed.get(actor_id, set())
        cap = base_cap
        for level in sorted(GENKAI_TESTS.keys()):
            if level in passed:
                cap = GENKAI_TESTS[level].next_level_cap
        return cap
