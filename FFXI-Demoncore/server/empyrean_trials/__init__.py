"""Empyrean weapon trial chain.

Each Empyrean weapon (one per WS-having job) progresses through
a fixed stage ladder, requiring drops from increasingly tough
Abyssea NMs. Stages:

    BASE          — start with the Mythril-tier base weapon
    LV75          — first upgrade, T1 Abyssea NMs
    LV80          — second, T2 Abyssea NMs
    LV85          — third, T3 Abyssea NMs
    LV90          — fourth, T4 NMs
    LV99          — fifth, requires Riftworn-pop NMs
    AFTERGLOW     — final tier, glow effect + +20 ilvl
                    upgrade

Composes on top of trial_of_magians for the trial-progression
state machine; this module owns the per-stage drop-target
specification.

Public surface
--------------
    EmpyreanWeapon enum
    EmpyreanStage enum
    EmpyreanStageReq dataclass
    EMPYREAN_TRIALS / EMPY_BY_WEAPON
    next_stage_for(weapon, current_stage)
    drops_required_for(weapon, stage) -> tuple[(item_id, qty), ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EmpyreanWeapon(str, enum.Enum):
    UKONVASARA = "ukonvasara"        # WAR (great axe)
    VERETHRAGNA = "verethragna"      # MNK (h2h)
    YAGRUSH = "yagrush"              # WHM (club)
    LANIAKEA = "laniakea"             # BLM (staff -- "Laevateinn")
    VESPER = "vesper"                 # RDM (sword -- "Almace")
    TWASHTAR = "twashtar"             # THF (dagger)
    ARMAGEDDON = "armageddon"        # COR (gun)
    KEISER = "keiser"                 # PUP (h2h)
    MASAMUNE = "masamune"             # SAM (great katana)


class EmpyreanStage(str, enum.Enum):
    BASE = "base"
    LV75 = "lv75"
    LV80 = "lv80"
    LV85 = "lv85"
    LV90 = "lv90"
    LV99 = "lv99"
    AFTERGLOW = "afterglow"


_STAGE_ORDER: tuple[EmpyreanStage, ...] = (
    EmpyreanStage.BASE,
    EmpyreanStage.LV75,
    EmpyreanStage.LV80,
    EmpyreanStage.LV85,
    EmpyreanStage.LV90,
    EmpyreanStage.LV99,
    EmpyreanStage.AFTERGLOW,
)


def next_stage_for(*, current_stage: EmpyreanStage,
                    ) -> t.Optional[EmpyreanStage]:
    idx = _STAGE_ORDER.index(current_stage)
    if idx + 1 >= len(_STAGE_ORDER):
        return None
    return _STAGE_ORDER[idx + 1]


@dataclasses.dataclass(frozen=True)
class StageRequirement:
    stage: EmpyreanStage
    drop_targets: tuple[tuple[str, int], ...]   # (item_id, quantity)
    label: str = ""


# Per-weapon stage drop targets. Real retail has 50+ specific
# NMs per weapon — we author one representative target per
# stage for the seed slice (ukonvasara fully, others use
# placeholder targets to validate the engine).
_BASE_TARGETS = (("mythril_ingot", 4), ("oxblood", 1))
_LV75_TARGETS = (("abyssea_t1_drop", 25),)
_LV80_TARGETS = (("abyssea_t2_drop", 50),)
_LV85_TARGETS = (("abyssea_t3_drop", 75),)
_LV90_TARGETS = (("abyssea_t4_drop", 100),)
_LV99_TARGETS = (("riftworn_voidwrought_essence", 25),)
_AFTERGLOW_TARGETS = (("eternal_essence", 100),)


def _stages_for(weapon: EmpyreanWeapon) -> tuple[StageRequirement, ...]:
    return (
        StageRequirement(EmpyreanStage.BASE, _BASE_TARGETS,
                          f"Forge base {weapon.value}"),
        StageRequirement(EmpyreanStage.LV75, _LV75_TARGETS,
                          f"Stage I — {weapon.value} +1"),
        StageRequirement(EmpyreanStage.LV80, _LV80_TARGETS,
                          f"Stage II — {weapon.value} +2"),
        StageRequirement(EmpyreanStage.LV85, _LV85_TARGETS,
                          f"Stage III — {weapon.value} +3"),
        StageRequirement(EmpyreanStage.LV90, _LV90_TARGETS,
                          f"Stage IV — {weapon.value} +4"),
        StageRequirement(EmpyreanStage.LV99, _LV99_TARGETS,
                          f"Stage V — {weapon.value} 99"),
        StageRequirement(EmpyreanStage.AFTERGLOW, _AFTERGLOW_TARGETS,
                          f"Afterglow — {weapon.value}"),
    )


EMPY_BY_WEAPON: dict[EmpyreanWeapon, tuple[StageRequirement, ...]] = {
    w: _stages_for(w) for w in EmpyreanWeapon
}


def drops_required_for(
    *, weapon: EmpyreanWeapon, stage: EmpyreanStage,
) -> tuple[tuple[str, int], ...]:
    for r in EMPY_BY_WEAPON[weapon]:
        if r.stage == stage:
            return r.drop_targets
    return ()


@dataclasses.dataclass
class PlayerEmpyreanProgress:
    player_id: str
    weapon: EmpyreanWeapon
    current_stage: EmpyreanStage = EmpyreanStage.BASE
    drops_collected: dict[str, int] = dataclasses.field(default_factory=dict)

    def add_drop(self, *, item_id: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        self.drops_collected[item_id] = (
            self.drops_collected.get(item_id, 0) + quantity
        )
        return True

    def stage_requirements_met(self) -> bool:
        for item_id, qty_needed in drops_required_for(
            weapon=self.weapon, stage=self.current_stage,
        ):
            if self.drops_collected.get(item_id, 0) < qty_needed:
                return False
        return True

    def advance_stage(self) -> bool:
        if not self.stage_requirements_met():
            return False
        nxt = next_stage_for(current_stage=self.current_stage)
        if nxt is None:
            return False
        # Consume stage materials
        for item_id, qty in drops_required_for(
            weapon=self.weapon, stage=self.current_stage,
        ):
            self.drops_collected[item_id] -= qty
        self.current_stage = nxt
        return True

    @property
    def is_afterglow(self) -> bool:
        return self.current_stage == EmpyreanStage.AFTERGLOW


__all__ = [
    "EmpyreanWeapon", "EmpyreanStage",
    "StageRequirement", "EMPY_BY_WEAPON",
    "next_stage_for", "drops_required_for",
    "PlayerEmpyreanProgress",
]
