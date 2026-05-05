"""Cult redemption quest — costly path back to the surface.

A HOLLOWED player isn't permanently lost. Sirenhall's
TIDE_KEEPERS run a redemption rite — long, expensive, and
not always successful. This module models the quest chain.

Quest stages (must complete in order):
  PETITIONED      - the player asks Sirenhall to consider them
  TRIBUTE_PAID    - large seapearl tribute paid (cost gate)
  ABYSS_VIGIL     - 7 Vana'diel days of solitude in DROWNED_VOID
                    without combat
  CONFESSION_TWO  - face the cult priest who recruited them
                    (player kills them OR cult priest spares them
                    via siren_song)
  PURIFICATION    - final rite at SILMARIL_SIRENHALL; this is
                    where corruption_taint is cleansed wholesale
                    (cleanse the full taint via this source)

Failure modes:
  * Failing ABYSS_VIGIL (combat during it) resets to TRIBUTE_PAID
    and the player owes another tribute.
  * Skipping CONFESSION_TWO doesn't terminate the quest — the
    cult priest stays alive and the brand persists.

On completion: dark_abilities revoked, brand cleared,
player can re-walk the cult path later (the cult will
remember).

Public surface
--------------
    RedemptionStage enum
    RedemptionRecord dataclass
    CultRedemptionQuest
        .petition(player_id, hollowed, now_seconds)
        .pay_tribute(player_id, seapearls_paid, now_seconds)
        .complete_vigil(player_id, combat_during, now_seconds)
        .face_priest(player_id, priest_killed, now_seconds)
        .purify(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RedemptionStage(str, enum.Enum):
    NOT_STARTED = "not_started"
    PETITIONED = "petitioned"
    TRIBUTE_PAID = "tribute_paid"
    ABYSS_VIGIL = "abyss_vigil"
    CONFESSION_TWO = "confession_two"
    PURIFIED = "purified"


SEAPEARL_TRIBUTE_REQUIRED = 50
VIGIL_DURATION_SECONDS = 7 * 24 * 3_600


@dataclasses.dataclass
class RedemptionRecord:
    player_id: str
    stage: RedemptionStage = RedemptionStage.NOT_STARTED
    petitioned_at: int = 0
    tribute_paid_at: t.Optional[int] = None
    vigil_started_at: t.Optional[int] = None
    confession_at: t.Optional[int] = None
    purified_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class StepResult:
    accepted: bool
    new_stage: t.Optional[RedemptionStage] = None
    pearls_consumed: int = 0
    taint_cleansed: int = 0
    abilities_revoked: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CultRedemptionQuest:
    _records: dict[str, RedemptionRecord] = dataclasses.field(
        default_factory=dict,
    )

    def status(self, *, player_id: str) -> t.Optional[RedemptionRecord]:
        return self._records.get(player_id)

    def petition(
        self, *, player_id: str,
        hollowed: bool,
        now_seconds: int,
    ) -> StepResult:
        if not player_id:
            return StepResult(False, reason="bad player")
        if not hollowed:
            return StepResult(False, reason="not hollowed")
        existing = self._records.get(player_id)
        if existing is not None and existing.stage not in (
            RedemptionStage.NOT_STARTED, RedemptionStage.PURIFIED,
        ):
            return StepResult(False, reason="already in quest")
        self._records[player_id] = RedemptionRecord(
            player_id=player_id,
            stage=RedemptionStage.PETITIONED,
            petitioned_at=now_seconds,
        )
        return StepResult(
            accepted=True, new_stage=RedemptionStage.PETITIONED,
        )

    def pay_tribute(
        self, *, player_id: str,
        seapearls_paid: int,
        now_seconds: int,
    ) -> StepResult:
        rec = self._records.get(player_id)
        if rec is None or rec.stage != RedemptionStage.PETITIONED:
            return StepResult(False, reason="not petitioned")
        if seapearls_paid < SEAPEARL_TRIBUTE_REQUIRED:
            return StepResult(
                False, reason="insufficient tribute",
            )
        rec.stage = RedemptionStage.TRIBUTE_PAID
        rec.tribute_paid_at = now_seconds
        return StepResult(
            accepted=True,
            new_stage=RedemptionStage.TRIBUTE_PAID,
            pearls_consumed=SEAPEARL_TRIBUTE_REQUIRED,
        )

    def begin_vigil(
        self, *, player_id: str, now_seconds: int,
    ) -> StepResult:
        rec = self._records.get(player_id)
        if rec is None or rec.stage != RedemptionStage.TRIBUTE_PAID:
            return StepResult(False, reason="must pay tribute first")
        rec.stage = RedemptionStage.ABYSS_VIGIL
        rec.vigil_started_at = now_seconds
        return StepResult(
            accepted=True, new_stage=RedemptionStage.ABYSS_VIGIL,
        )

    def complete_vigil(
        self, *, player_id: str,
        combat_during: bool,
        now_seconds: int,
    ) -> StepResult:
        rec = self._records.get(player_id)
        if rec is None or rec.stage != RedemptionStage.ABYSS_VIGIL:
            return StepResult(False, reason="not in vigil")
        if rec.vigil_started_at is None:
            return StepResult(False, reason="vigil not started")
        if (now_seconds - rec.vigil_started_at) < VIGIL_DURATION_SECONDS:
            return StepResult(False, reason="vigil too short")
        if combat_during:
            # vigil failed — reset to TRIBUTE_PAID; need new tribute
            rec.stage = RedemptionStage.PETITIONED
            rec.tribute_paid_at = None
            rec.vigil_started_at = None
            return StepResult(
                accepted=True,
                new_stage=RedemptionStage.PETITIONED,
                reason="vigil broken; tribute required again",
            )
        rec.stage = RedemptionStage.CONFESSION_TWO
        return StepResult(
            accepted=True, new_stage=RedemptionStage.CONFESSION_TWO,
        )

    def face_priest(
        self, *, player_id: str,
        priest_killed: bool,
        now_seconds: int,
    ) -> StepResult:
        rec = self._records.get(player_id)
        if rec is None or rec.stage != RedemptionStage.CONFESSION_TWO:
            return StepResult(False, reason="not at confession")
        # whether or not the priest died, advance — the cult
        # remembers regardless
        rec.confession_at = now_seconds
        return StepResult(
            accepted=True,
            new_stage=RedemptionStage.CONFESSION_TWO,
        )

    def purify(
        self, *, player_id: str, now_seconds: int,
    ) -> StepResult:
        rec = self._records.get(player_id)
        if rec is None or rec.stage != RedemptionStage.CONFESSION_TWO:
            return StepResult(False, reason="confession required")
        if rec.confession_at is None:
            return StepResult(False, reason="must face priest")
        rec.stage = RedemptionStage.PURIFIED
        rec.purified_at = now_seconds
        return StepResult(
            accepted=True,
            new_stage=RedemptionStage.PURIFIED,
            taint_cleansed=100,
            abilities_revoked=True,
        )


__all__ = [
    "RedemptionStage", "RedemptionRecord", "StepResult",
    "CultRedemptionQuest",
    "SEAPEARL_TRIBUTE_REQUIRED", "VIGIL_DURATION_SECONDS",
]
