"""Kraken cult recruitment — Deep Faithful approaches the player.

The DEEP_FAITHFUL faction in mermaid_diplomacy_council are
the kraken-cultists. They watch for players whose actions
hint at darker leanings and APPROACH them with offers. An
offer becomes a recruitment SESSION — a series of escalating
asks. Accept the asks and corruption_taint accumulates;
refuse and the cult walks away (but remembers).

Approach criteria (any one suffices):
  * defeated_kraken at least once (carries the loot)
  * killed at least 5 SUNKEN_CROWN pirates
  * any siren-tribute paid as outlaw (was paying anyway)
  * NPC kill in DROWNED_VOID
The recruiter sets a HOOK kind based on which trigger fired.

Session stages:
  PROPOSED   - offer extended, awaiting accept/refuse
  ACCEPTED   - player has agreed to first request
  ESCALATED  - second tier; harder ask
  PLEDGED    - final ask; if accepted -> drowned_pact_ritual
  REFUSED    - any refusal terminates the session

Public surface
--------------
    HookKind enum
    SessionStage enum
    SessionRecord dataclass
    KrakenCultRecruitment
        .approach(player_id, hook, now_seconds)
        .accept_step(player_id, now_seconds)
        .refuse(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HookKind(str, enum.Enum):
    KRAKEN_FELLED = "kraken_felled"
    SUNKEN_CROWN_KILLER = "sunken_crown_killer"
    OUTLAW_TRIBUTARY = "outlaw_tributary"
    VOID_KILLER = "void_killer"


class SessionStage(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    ESCALATED = "escalated"
    PLEDGED = "pledged"
    REFUSED = "refused"


# corruption gained at each stage advance
_CORRUPTION_DELTA: dict[SessionStage, int] = {
    SessionStage.ACCEPTED: 5,
    SessionStage.ESCALATED: 15,
    SessionStage.PLEDGED: 30,
}

# stage progression
_NEXT_STAGE: dict[SessionStage, SessionStage] = {
    SessionStage.PROPOSED: SessionStage.ACCEPTED,
    SessionStage.ACCEPTED: SessionStage.ESCALATED,
    SessionStage.ESCALATED: SessionStage.PLEDGED,
}


@dataclasses.dataclass
class SessionRecord:
    player_id: str
    hook: HookKind
    stage: SessionStage = SessionStage.PROPOSED
    proposed_at: int = 0
    last_advanced_at: int = 0
    refused_at: t.Optional[int] = None
    cult_remembers: bool = False    # set on refusal


@dataclasses.dataclass(frozen=True)
class StepResult:
    accepted: bool
    new_stage: t.Optional[SessionStage] = None
    corruption_gained: int = 0
    pledge_unlocks_ritual: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class KrakenCultRecruitment:
    _sessions: dict[str, SessionRecord] = dataclasses.field(
        default_factory=dict,
    )

    def approach(
        self, *, player_id: str,
        hook: HookKind,
        now_seconds: int,
    ) -> StepResult:
        if not player_id:
            return StepResult(False, reason="bad player")
        if hook not in HookKind:
            return StepResult(False, reason="unknown hook")
        existing = self._sessions.get(player_id)
        if existing is not None and existing.stage not in (
            SessionStage.REFUSED,
            SessionStage.PLEDGED,
        ):
            return StepResult(False, reason="session in progress")
        self._sessions[player_id] = SessionRecord(
            player_id=player_id,
            hook=hook,
            stage=SessionStage.PROPOSED,
            proposed_at=now_seconds,
            last_advanced_at=now_seconds,
        )
        return StepResult(
            accepted=True, new_stage=SessionStage.PROPOSED,
        )

    def accept_step(
        self, *, player_id: str, now_seconds: int,
    ) -> StepResult:
        rec = self._sessions.get(player_id)
        if rec is None:
            return StepResult(False, reason="no session")
        if rec.stage in (
            SessionStage.REFUSED, SessionStage.PLEDGED,
        ):
            return StepResult(False, reason="session over")
        next_stage = _NEXT_STAGE[rec.stage]
        rec.stage = next_stage
        rec.last_advanced_at = now_seconds
        gain = _CORRUPTION_DELTA[next_stage]
        return StepResult(
            accepted=True,
            new_stage=next_stage,
            corruption_gained=gain,
            pledge_unlocks_ritual=(next_stage == SessionStage.PLEDGED),
        )

    def refuse(
        self, *, player_id: str, now_seconds: int,
    ) -> StepResult:
        rec = self._sessions.get(player_id)
        if rec is None:
            return StepResult(False, reason="no session")
        if rec.stage == SessionStage.REFUSED:
            return StepResult(False, reason="already refused")
        if rec.stage == SessionStage.PLEDGED:
            return StepResult(
                False, reason="cannot refuse after pledge",
            )
        rec.stage = SessionStage.REFUSED
        rec.refused_at = now_seconds
        rec.cult_remembers = True
        return StepResult(
            accepted=True, new_stage=SessionStage.REFUSED,
        )

    def session(
        self, *, player_id: str,
    ) -> t.Optional[SessionRecord]:
        return self._sessions.get(player_id)


__all__ = [
    "HookKind", "SessionStage",
    "SessionRecord", "StepResult",
    "KrakenCultRecruitment",
]
