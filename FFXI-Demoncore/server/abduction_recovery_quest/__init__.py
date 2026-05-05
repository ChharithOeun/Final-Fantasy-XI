"""Abduction recovery quest — rescue captives from pirate fleets.

Each CAPTIVE intent emitted by fomor_crew_spawn becomes a
RESCUABLE TARGET. Players (or parties) can ACCEPT a recovery
quest, locate the captive in the abductor's primary zone,
defeat the guarding pirates, and EXTRACT the captive back
to a safe haven (typically a town or a friendly underwater
city).

Quest stages:
  POSTED   - quest is visible on the recovery board
  ACCEPTED - a player/party has taken it; captive locked to that
             party for the duration
  ENGAGED  - rescuers have engaged the holding fleet
  EXTRACTED - captive returned to safe haven (success)
  EXPIRED  - too much time elapsed; captive transitions to a
             permanent fomor variant (drop into fomor_crew_spawn
             as a FOMOR_MOB intent)

Per-captive rules:
  * Only one party can hold a captive's recovery at a time.
  * If the holders fail to extract within EXPIRY_SECONDS of
    accept time, the quest expires and captive_lost() is True.
  * Successful extract awards bounty_gil + faction reputation
    delta to the rescue holder.

Public surface
--------------
    QuestStage enum
    RecoveryProfile dataclass
    RecoveryRecord dataclass
    AbductionRecoveryQuest
        .post(captive_spawn_id, abductor_zone_id, bounty_gil,
              now_seconds)
        .accept(captive_spawn_id, party_id, now_seconds)
        .engage(captive_spawn_id, now_seconds)
        .extract(captive_spawn_id, now_seconds)
        .tick_expiry(now_seconds)  -> tuple of expired captive ids
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class QuestStage(str, enum.Enum):
    POSTED = "posted"
    ACCEPTED = "accepted"
    ENGAGED = "engaged"
    EXTRACTED = "extracted"
    EXPIRED = "expired"


# 6h to extract before captive is permanently lost
EXPIRY_SECONDS = 6 * 3_600


@dataclasses.dataclass
class RecoveryRecord:
    captive_spawn_id: str
    abductor_zone_id: str
    bounty_gil: int
    posted_at: int
    stage: QuestStage = QuestStage.POSTED
    held_by_party: t.Optional[str] = None
    accepted_at: t.Optional[int] = None
    engaged_at: t.Optional[int] = None
    extracted_at: t.Optional[int] = None
    expired_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class RecoveryResult:
    accepted: bool
    captive_spawn_id: str
    new_stage: t.Optional[QuestStage] = None
    awarded_gil: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AbductionRecoveryQuest:
    _records: dict[str, RecoveryRecord] = dataclasses.field(
        default_factory=dict,
    )

    def post(
        self, *, captive_spawn_id: str,
        abductor_zone_id: str,
        bounty_gil: int,
        now_seconds: int,
    ) -> RecoveryResult:
        if not captive_spawn_id or not abductor_zone_id:
            return RecoveryResult(False, captive_spawn_id, reason="bad ids")
        if bounty_gil < 0:
            return RecoveryResult(
                False, captive_spawn_id, reason="bad bounty",
            )
        if captive_spawn_id in self._records:
            return RecoveryResult(
                False, captive_spawn_id, reason="already posted",
            )
        self._records[captive_spawn_id] = RecoveryRecord(
            captive_spawn_id=captive_spawn_id,
            abductor_zone_id=abductor_zone_id,
            bounty_gil=bounty_gil,
            posted_at=now_seconds,
        )
        return RecoveryResult(
            True, captive_spawn_id, new_stage=QuestStage.POSTED,
        )

    def accept(
        self, *, captive_spawn_id: str,
        party_id: str,
        now_seconds: int,
    ) -> RecoveryResult:
        rec = self._records.get(captive_spawn_id)
        if rec is None:
            return RecoveryResult(
                False, captive_spawn_id, reason="not posted",
            )
        if rec.stage != QuestStage.POSTED:
            return RecoveryResult(
                False, captive_spawn_id, reason="wrong stage",
            )
        if not party_id:
            return RecoveryResult(
                False, captive_spawn_id, reason="bad party",
            )
        rec.stage = QuestStage.ACCEPTED
        rec.held_by_party = party_id
        rec.accepted_at = now_seconds
        return RecoveryResult(
            True, captive_spawn_id, new_stage=QuestStage.ACCEPTED,
        )

    def engage(
        self, *, captive_spawn_id: str,
        now_seconds: int,
    ) -> RecoveryResult:
        rec = self._records.get(captive_spawn_id)
        if rec is None:
            return RecoveryResult(
                False, captive_spawn_id, reason="not posted",
            )
        if rec.stage != QuestStage.ACCEPTED:
            return RecoveryResult(
                False, captive_spawn_id, reason="wrong stage",
            )
        rec.stage = QuestStage.ENGAGED
        rec.engaged_at = now_seconds
        return RecoveryResult(
            True, captive_spawn_id, new_stage=QuestStage.ENGAGED,
        )

    def extract(
        self, *, captive_spawn_id: str,
        now_seconds: int,
    ) -> RecoveryResult:
        rec = self._records.get(captive_spawn_id)
        if rec is None:
            return RecoveryResult(
                False, captive_spawn_id, reason="not posted",
            )
        if rec.stage != QuestStage.ENGAGED:
            return RecoveryResult(
                False, captive_spawn_id, reason="must engage first",
            )
        rec.stage = QuestStage.EXTRACTED
        rec.extracted_at = now_seconds
        return RecoveryResult(
            True, captive_spawn_id,
            new_stage=QuestStage.EXTRACTED,
            awarded_gil=rec.bounty_gil,
        )

    def tick_expiry(
        self, *, now_seconds: int,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for rec in self._records.values():
            if rec.stage in (QuestStage.EXTRACTED, QuestStage.EXPIRED):
                continue
            anchor = rec.accepted_at or rec.posted_at
            if now_seconds - anchor >= EXPIRY_SECONDS:
                rec.stage = QuestStage.EXPIRED
                rec.expired_at = now_seconds
                expired.append(rec.captive_spawn_id)
        return tuple(expired)

    def status(
        self, *, captive_spawn_id: str,
    ) -> t.Optional[RecoveryRecord]:
        return self._records.get(captive_spawn_id)

    def open_quests(self) -> tuple[RecoveryRecord, ...]:
        return tuple(
            r for r in self._records.values()
            if r.stage in (
                QuestStage.POSTED, QuestStage.ACCEPTED,
                QuestStage.ENGAGED,
            )
        )


__all__ = [
    "QuestStage", "RecoveryRecord", "RecoveryResult",
    "AbductionRecoveryQuest", "EXPIRY_SECONDS",
]
