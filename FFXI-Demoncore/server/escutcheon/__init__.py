"""Escutcheon — multi-stage PLD/RUN shield trial chain.

Each PLD/RUN can pursue an Empyrean shield via a directed
chain of trial tasks: kill X mobs of family Y, gather Z
materials, clear instance N, etc. Stages must be completed in
order. Final stage produces the shield.

Public surface
--------------
    StageKind enum (KILL_FAMILY / GATHER / CLEAR_INSTANCE / TRADE)
    EscutcheonStage / ESCUTCHEON_CHAIN
    PlayerEscutcheon
        .progress(stage_id, payload) -> ProgressResult
        .stage_complete(stage_id) -> bool
        .is_complete property
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StageKind(str, enum.Enum):
    KILL_FAMILY = "kill_family"
    GATHER = "gather"
    CLEAR_INSTANCE = "clear_instance"
    TRADE = "trade"


@dataclasses.dataclass(frozen=True)
class EscutcheonStage:
    stage_id: str
    label: str
    kind: StageKind
    target_id: str          # mob_family / item_id / instance_id
    quantity: int = 1


# Sample chain — modeled on canonical Aegis Escutcheon trial.
ESCUTCHEON_CHAIN: tuple[EscutcheonStage, ...] = (
    EscutcheonStage(
        "stage_1_kill_orcs",
        "Slay Orc Warlords (50)",
        StageKind.KILL_FAMILY, "orc", quantity=50,
    ),
    EscutcheonStage(
        "stage_2_gather_iron",
        "Gather Iron Ingots (20)",
        StageKind.GATHER, "iron_ingot", quantity=20,
    ),
    EscutcheonStage(
        "stage_3_clear_dragon_lair",
        "Clear Dragon's Aery instance",
        StageKind.CLEAR_INSTANCE, "dragon_aery_bcnm",
    ),
    EscutcheonStage(
        "stage_4_kill_undead",
        "Slay Undead (100)",
        StageKind.KILL_FAMILY, "undead", quantity=100,
    ),
    EscutcheonStage(
        "stage_5_trade_seal",
        "Trade Knight's Seal to Curilla",
        StageKind.TRADE, "knights_seal", quantity=1,
    ),
    EscutcheonStage(
        "stage_6_clear_throne_room",
        "Clear Throne Room BCNM",
        StageKind.CLEAR_INSTANCE, "throne_room_bcnm",
    ),
)


@dataclasses.dataclass(frozen=True)
class ProgressResult:
    accepted: bool
    stage_id: t.Optional[str] = None
    progress: int = 0
    quantity: int = 0
    completed: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerEscutcheon:
    player_id: str
    current_stage_index: int = 0
    progress_into_stage: int = 0
    completed_stage_ids: list[str] = dataclasses.field(
        default_factory=list,
    )

    @property
    def current_stage(self) -> t.Optional[EscutcheonStage]:
        if self.current_stage_index >= len(ESCUTCHEON_CHAIN):
            return None
        return ESCUTCHEON_CHAIN[self.current_stage_index]

    @property
    def is_complete(self) -> bool:
        return self.current_stage_index >= len(ESCUTCHEON_CHAIN)

    def stage_complete(self, *, stage_id: str) -> bool:
        return stage_id in self.completed_stage_ids

    # ------------------------------------------------------------------
    # Tally an event toward the active stage
    # ------------------------------------------------------------------
    def progress(self, *, kind: StageKind, target_id: str,
                  amount: int = 1) -> ProgressResult:
        if self.is_complete:
            return ProgressResult(False, reason="all stages complete")
        stage = self.current_stage
        assert stage is not None
        if kind != stage.kind or target_id != stage.target_id:
            return ProgressResult(
                False, reason="event doesn't match current stage",
                stage_id=stage.stage_id,
            )
        self.progress_into_stage = min(
            stage.quantity, self.progress_into_stage + amount,
        )
        completed = self.progress_into_stage >= stage.quantity
        if completed:
            self.completed_stage_ids.append(stage.stage_id)
            self.current_stage_index += 1
            self.progress_into_stage = 0
        return ProgressResult(
            accepted=True,
            stage_id=stage.stage_id,
            progress=self.progress_into_stage if not completed
                       else stage.quantity,
            quantity=stage.quantity,
            completed=completed,
        )


__all__ = [
    "StageKind", "EscutcheonStage", "ESCUTCHEON_CHAIN",
    "ProgressResult", "PlayerEscutcheon",
]
