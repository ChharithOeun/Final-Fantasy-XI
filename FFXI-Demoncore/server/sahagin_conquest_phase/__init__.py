"""Sahagin Conquest Phase — 3-alliance zone assault before the Royal Palace.

The Royal Palace fight is gated by a 2-hour conquest. The
raid (up to 64 players, mandatory 3 alliances of 18 each
plus up to 10 floater/raid-lead slots) gets randomly
assigned to 3 of N possible conquest zones. Each alliance
completes Phase 1 in their zone (1 hour timer), then
Phase 2 in the same zone (another hour). EVERY alliance
must finish BOTH phases of their zone or the whole raid
loses — no carrying, no skipping.

Zone assignment is randomized at raid start (deterministic
from a seed, but never predictable in advance). The 3
alliances cannot trade zones once randomized.

Public surface
--------------
    AllianceSlot int enum  (ALPHA, BRAVO, CHARLIE)
    Phase int enum  (PHASE_1, PHASE_2)
    ConquestStatus enum
    AllianceAssignment dataclass (frozen)
    SahaginConquestPhase
        .register_raid(raid_id, candidate_zones, now_seconds)
        .sign_alliance(raid_id, slot, member_ids)
        .randomize_assignments(raid_id, seed)
        .start_phase(raid_id, slot, phase, now_seconds)
        .complete_phase(raid_id, slot, phase, now_seconds)
        .fail_phase(raid_id, slot, reason, now_seconds)
        .status_of(raid_id) -> ConquestStatus
        .assignment_for(raid_id, slot)
            -> Optional[AllianceAssignment]
        .all_phases_complete(raid_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


class AllianceSlot(int, enum.Enum):
    ALPHA = 0
    BRAVO = 1
    CHARLIE = 2


class Phase(int, enum.Enum):
    PHASE_1 = 1
    PHASE_2 = 2


class ConquestStatus(str, enum.Enum):
    OPEN = "open"                # raid registered, signing
    SIGNED = "signed"            # all 3 alliances signed
    ASSIGNED = "assigned"        # zones randomized
    IN_PROGRESS = "in_progress"  # at least one phase started
    COMPLETE = "complete"        # all 3 finished both phases
    FAILED = "failed"            # any alliance failed any phase


ALLIANCE_SIZE = 18
TOTAL_ALLIANCES = 3
PHASE_DURATION_SECONDS = 60 * 60   # 1 hour per phase
TOTAL_DURATION_SECONDS = (
    PHASE_DURATION_SECONDS * 2  # 2 hours total conquest
)
# leadership/scout slots beyond 3x18 = 54 floor
MAX_LEADERSHIP_SLOTS = 10
MAX_RAID_PLAYERS = ALLIANCE_SIZE * TOTAL_ALLIANCES + MAX_LEADERSHIP_SLOTS


@dataclasses.dataclass(frozen=True)
class AllianceAssignment:
    slot: AllianceSlot
    zone_id: str
    phase_1_started: t.Optional[int]
    phase_1_completed: t.Optional[int]
    phase_2_started: t.Optional[int]
    phase_2_completed: t.Optional[int]
    failed: bool
    fail_reason: t.Optional[str]


@dataclasses.dataclass
class _AllianceState:
    slot: AllianceSlot
    member_ids: list[str] = dataclasses.field(default_factory=list)
    zone_id: t.Optional[str] = None
    phase_1_started: t.Optional[int] = None
    phase_1_completed: t.Optional[int] = None
    phase_2_started: t.Optional[int] = None
    phase_2_completed: t.Optional[int] = None
    failed: bool = False
    fail_reason: t.Optional[str] = None


@dataclasses.dataclass
class _RaidState:
    raid_id: str
    candidate_zones: list[str]
    started_at: int
    alliances: dict[AllianceSlot, _AllianceState] = dataclasses.field(
        default_factory=dict,
    )
    status: ConquestStatus = ConquestStatus.OPEN


@dataclasses.dataclass
class SahaginConquestPhase:
    _raids: dict[str, _RaidState] = dataclasses.field(default_factory=dict)

    def register_raid(
        self, *, raid_id: str,
        candidate_zones: t.Iterable[str],
        now_seconds: int,
    ) -> bool:
        if not raid_id or raid_id in self._raids:
            return False
        zones = list(candidate_zones)
        if len(zones) < TOTAL_ALLIANCES:
            return False  # need at least 3 candidate zones
        if len(set(zones)) != len(zones):
            return False  # no duplicates
        self._raids[raid_id] = _RaidState(
            raid_id=raid_id,
            candidate_zones=zones,
            started_at=now_seconds,
        )
        return True

    def sign_alliance(
        self, *, raid_id: str,
        slot: AllianceSlot,
        member_ids: t.Iterable[str],
    ) -> bool:
        r = self._raids.get(raid_id)
        if r is None or r.status != ConquestStatus.OPEN:
            return False
        if slot in r.alliances:
            return False
        members = list(member_ids)
        if len(members) != ALLIANCE_SIZE:
            return False
        if len(set(members)) != len(members):
            return False
        # cross-alliance dup check
        all_members = {
            m for a in r.alliances.values() for m in a.member_ids
        }
        if any(m in all_members for m in members):
            return False
        r.alliances[slot] = _AllianceState(
            slot=slot, member_ids=members,
        )
        if len(r.alliances) == TOTAL_ALLIANCES:
            r.status = ConquestStatus.SIGNED
        return True

    def randomize_assignments(
        self, *, raid_id: str, seed: int,
    ) -> bool:
        r = self._raids.get(raid_id)
        if r is None or r.status != ConquestStatus.SIGNED:
            return False
        rng = random.Random(seed)
        zones = list(r.candidate_zones)
        rng.shuffle(zones)
        # take the first 3 shuffled zones, assign in order
        for i, slot in enumerate([
            AllianceSlot.ALPHA, AllianceSlot.BRAVO, AllianceSlot.CHARLIE,
        ]):
            r.alliances[slot].zone_id = zones[i]
        r.status = ConquestStatus.ASSIGNED
        return True

    def start_phase(
        self, *, raid_id: str,
        slot: AllianceSlot,
        phase: Phase,
        now_seconds: int,
    ) -> bool:
        r = self._raids.get(raid_id)
        if r is None or r.status not in (
            ConquestStatus.ASSIGNED, ConquestStatus.IN_PROGRESS,
        ):
            return False
        a = r.alliances.get(slot)
        if a is None or a.failed:
            return False
        if phase == Phase.PHASE_1:
            if a.phase_1_started is not None:
                return False
            a.phase_1_started = now_seconds
        else:  # PHASE_2
            if a.phase_1_completed is None:
                return False  # must finish 1 first
            if a.phase_2_started is not None:
                return False
            a.phase_2_started = now_seconds
        r.status = ConquestStatus.IN_PROGRESS
        return True

    def complete_phase(
        self, *, raid_id: str,
        slot: AllianceSlot,
        phase: Phase,
        now_seconds: int,
    ) -> bool:
        r = self._raids.get(raid_id)
        if r is None or r.status not in (
            ConquestStatus.IN_PROGRESS,
        ):
            return False
        a = r.alliances.get(slot)
        if a is None or a.failed:
            return False
        if phase == Phase.PHASE_1:
            if a.phase_1_started is None or a.phase_1_completed is not None:
                return False
            elapsed = now_seconds - a.phase_1_started
            if elapsed > PHASE_DURATION_SECONDS:
                return self.fail_phase(
                    raid_id=raid_id, slot=slot,
                    reason="phase 1 timer expired",
                    now_seconds=now_seconds,
                )
            a.phase_1_completed = now_seconds
        else:  # PHASE_2
            if a.phase_2_started is None or a.phase_2_completed is not None:
                return False
            elapsed = now_seconds - a.phase_2_started
            if elapsed > PHASE_DURATION_SECONDS:
                return self.fail_phase(
                    raid_id=raid_id, slot=slot,
                    reason="phase 2 timer expired",
                    now_seconds=now_seconds,
                )
            a.phase_2_completed = now_seconds
        # check if all 3 alliances cleared everything
        if self.all_phases_complete(raid_id=raid_id):
            r.status = ConquestStatus.COMPLETE
        return True

    def fail_phase(
        self, *, raid_id: str,
        slot: AllianceSlot,
        reason: str,
        now_seconds: int,
    ) -> bool:
        r = self._raids.get(raid_id)
        if r is None:
            return False
        a = r.alliances.get(slot)
        if a is None or a.failed:
            return False
        a.failed = True
        a.fail_reason = reason
        # one alliance fails = whole raid fails
        r.status = ConquestStatus.FAILED
        return True

    def status_of(self, *, raid_id: str) -> t.Optional[ConquestStatus]:
        r = self._raids.get(raid_id)
        return r.status if r else None

    def assignment_for(
        self, *, raid_id: str, slot: AllianceSlot,
    ) -> t.Optional[AllianceAssignment]:
        r = self._raids.get(raid_id)
        if r is None:
            return None
        a = r.alliances.get(slot)
        if a is None or a.zone_id is None:
            return None
        return AllianceAssignment(
            slot=slot,
            zone_id=a.zone_id,
            phase_1_started=a.phase_1_started,
            phase_1_completed=a.phase_1_completed,
            phase_2_started=a.phase_2_started,
            phase_2_completed=a.phase_2_completed,
            failed=a.failed,
            fail_reason=a.fail_reason,
        )

    def all_phases_complete(self, *, raid_id: str) -> bool:
        r = self._raids.get(raid_id)
        if r is None:
            return False
        if len(r.alliances) != TOTAL_ALLIANCES:
            return False
        return all(
            (
                not a.failed
                and a.phase_1_completed is not None
                and a.phase_2_completed is not None
            )
            for a in r.alliances.values()
        )


__all__ = [
    "AllianceSlot", "Phase", "ConquestStatus",
    "AllianceAssignment", "SahaginConquestPhase",
    "ALLIANCE_SIZE", "TOTAL_ALLIANCES",
    "PHASE_DURATION_SECONDS", "TOTAL_DURATION_SECONDS",
    "MAX_LEADERSHIP_SLOTS", "MAX_RAID_PLAYERS",
]
