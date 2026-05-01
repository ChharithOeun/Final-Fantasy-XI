"""Creation step state machine — 7 steps, commit on Begin.

Per CHARACTER_CREATION.md control order:
    1. Nation -> 2. Race -> 3. Sub/face/hair/eyes/skin -> 4. Gear
    -> 5. Voice -> 6. Name -> 7. Begin

Re-roll any step before Begin; nothing commits until Begin.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .nations_races import Nation, Race


class CreationStep(int, enum.Enum):
    NATION = 1
    RACE = 2
    APPEARANCE = 3
    GEAR = 4
    VOICE = 5
    NAME = 6
    BEGIN = 7


CREATION_STEP_ORDER: tuple[CreationStep, ...] = tuple(CreationStep)


@dataclasses.dataclass
class CharacterDraft:
    """The in-progress character. Fields are filled as the player
    advances through steps; commit is the Begin button."""
    nation: t.Optional[Nation] = None
    race: t.Optional[Race] = None
    sub_race: t.Optional[str] = None
    face_id: t.Optional[str] = None
    hair_id: t.Optional[str] = None
    eyes_id: t.Optional[str] = None
    skin_id: t.Optional[str] = None
    gear_set: t.Optional[str] = None
    voice_anchor_id: t.Optional[str] = None
    voice_bank_id: t.Optional[str] = None     # set when custom voice
    name: t.Optional[str] = None

    def step_complete(self, step: CreationStep) -> bool:
        if step == CreationStep.NATION:
            return self.nation is not None
        if step == CreationStep.RACE:
            return self.race is not None
        if step == CreationStep.APPEARANCE:
            return all(x is not None for x in
                          (self.face_id, self.hair_id,
                            self.eyes_id, self.skin_id))
        if step == CreationStep.GEAR:
            return self.gear_set is not None
        if step == CreationStep.VOICE:
            return (self.voice_anchor_id is not None
                      or self.voice_bank_id is not None)
        if step == CreationStep.NAME:
            return self.name is not None and len(self.name.strip()) > 0
        if step == CreationStep.BEGIN:
            return all(self.step_complete(s) for s in CREATION_STEP_ORDER
                          if s != CreationStep.BEGIN)
        return False


@dataclasses.dataclass
class CreationSession:
    """Per-account creation flow."""
    account_id: str
    is_veteran: bool = False
    current_step: CreationStep = CreationStep.NATION
    draft: CharacterDraft = dataclasses.field(default_factory=CharacterDraft)
    committed: bool = False

    # ------------------------------------------------------------------
    # Step advance
    # ------------------------------------------------------------------

    def advance(self) -> CreationStep:
        """Advance to the next step if the current one is complete.

        Returns the new current_step. No-op if not complete.
        """
        if self.committed:
            return self.current_step
        if not self.draft.step_complete(self.current_step):
            return self.current_step
        idx = CREATION_STEP_ORDER.index(self.current_step)
        if idx + 1 < len(CREATION_STEP_ORDER):
            self.current_step = CREATION_STEP_ORDER[idx + 1]
        return self.current_step

    def go_back(self) -> CreationStep:
        if self.committed:
            return self.current_step
        idx = CREATION_STEP_ORDER.index(self.current_step)
        if idx > 0:
            self.current_step = CREATION_STEP_ORDER[idx - 1]
        return self.current_step

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def can_commit(self) -> tuple[bool, str]:
        """Begin button gate."""
        for step in CREATION_STEP_ORDER:
            if step == CreationStep.BEGIN:
                continue
            if not self.draft.step_complete(step):
                return False, f"step {step.name} not complete"
        return True, ""

    def commit(self) -> bool:
        ok, _ = self.can_commit()
        if not ok:
            return False
        self.committed = True
        self.current_step = CreationStep.BEGIN
        return True

    # ------------------------------------------------------------------
    # Re-roll helpers (free until Begin)
    # ------------------------------------------------------------------

    def reroll_step(self, step: CreationStep) -> None:
        """Doc: 'Re-roll every step freely; nothing commits until Begin'."""
        if self.committed:
            return
        if step == CreationStep.NATION:
            self.draft.nation = None
        elif step == CreationStep.RACE:
            self.draft.race = None
        elif step == CreationStep.APPEARANCE:
            self.draft.face_id = None
            self.draft.hair_id = None
            self.draft.eyes_id = None
            self.draft.skin_id = None
        elif step == CreationStep.GEAR:
            self.draft.gear_set = None
        elif step == CreationStep.VOICE:
            self.draft.voice_anchor_id = None
            self.draft.voice_bank_id = None
        elif step == CreationStep.NAME:
            self.draft.name = None
