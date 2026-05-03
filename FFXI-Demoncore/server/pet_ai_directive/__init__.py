"""Pet AI directive — command modes for PUP / SMN / BST / GEO pets.

Six canonical command states control how a pet decides what to do:

    PASSIVE   — pet doesn't engage anything; follows owner.
    HEEL      — return to and stay at owner's side; ignores aggro.
    SIC       — attack the owner's current target with normal AI.
    FIGHT     — attack owner's target AND counter-aggro
                (defends owner if owner takes hits).
    RELEASE   — pet despawns and the owner regains pet slot.
    READY     — PUP-specific: pet uses Ready (manual) abilities
                only when owner queues them.

Public surface
--------------
    PetCommand enum
    PetClass enum (PUP / SMN / BST / GEO)
    PetDirective dataclass
    valid_for(command, pet_class) -> bool
    PetController
        .set_command(command) -> bool
        .pet_should_engage(target_taken_aggro: bool, ...) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PetCommand(str, enum.Enum):
    PASSIVE = "passive"
    HEEL = "heel"
    SIC = "sic"
    FIGHT = "fight"
    RELEASE = "release"
    READY = "ready"            # PUP only


class PetClass(str, enum.Enum):
    PUPPET = "puppet"          # PUP automaton
    AVATAR = "avatar"          # SMN avatar
    JUG_PET = "jug_pet"        # BST jug
    LUOPAN = "luopan"          # GEO pet bubble (limited)


# Which commands are valid for each pet class
_VALID_COMMANDS: dict[PetClass, frozenset[PetCommand]] = {
    PetClass.PUPPET: frozenset({
        PetCommand.PASSIVE, PetCommand.HEEL,
        PetCommand.SIC, PetCommand.FIGHT,
        PetCommand.RELEASE, PetCommand.READY,
    }),
    PetClass.AVATAR: frozenset({
        PetCommand.PASSIVE, PetCommand.HEEL,
        PetCommand.SIC, PetCommand.FIGHT,
        PetCommand.RELEASE,
    }),
    PetClass.JUG_PET: frozenset({
        PetCommand.PASSIVE, PetCommand.HEEL,
        PetCommand.SIC, PetCommand.FIGHT,
        PetCommand.RELEASE,
    }),
    PetClass.LUOPAN: frozenset({
        PetCommand.PASSIVE, PetCommand.RELEASE,
    }),   # luopans are stationary; only passive or recall
}


def valid_for(*, command: PetCommand, pet_class: PetClass) -> bool:
    return command in _VALID_COMMANDS.get(pet_class, frozenset())


@dataclasses.dataclass(frozen=True)
class CommandResult:
    accepted: bool
    new_command: t.Optional[PetCommand] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PetDirective:
    """Active command state for a single pet."""
    pet_id: str
    pet_class: PetClass
    owner_id: str
    command: PetCommand = PetCommand.HEEL


@dataclasses.dataclass
class PetController:
    pet: PetDirective

    def set_command(self, *, command: PetCommand) -> CommandResult:
        if not valid_for(command=command, pet_class=self.pet.pet_class):
            return CommandResult(
                False, reason=f"{command.value} not valid for "
                                  f"{self.pet.pet_class.value}",
            )
        self.pet.command = command
        return CommandResult(True, new_command=command)

    def pet_should_engage(
        self, *, owner_target_id: t.Optional[str],
        owner_in_combat: bool,
        target_taken_aggro: bool = False,
    ) -> bool:
        """Decide whether the pet should engage based on its
        current command + game state."""
        cmd = self.pet.command
        if cmd in (PetCommand.RELEASE, PetCommand.PASSIVE,
                   PetCommand.HEEL):
            return False
        if cmd == PetCommand.READY:
            # PUP "Ready" — only fires on owner-queued abilities;
            # ambient engagement is off.
            return False
        if cmd == PetCommand.SIC:
            return owner_target_id is not None
        # FIGHT: attack target if assigned; also defend owner
        if cmd == PetCommand.FIGHT:
            return (
                owner_target_id is not None
                or (owner_in_combat and target_taken_aggro)
            )
        return False

    def is_attached(self) -> bool:
        return self.pet.command != PetCommand.RELEASE


__all__ = [
    "PetCommand", "PetClass",
    "valid_for", "CommandResult",
    "PetDirective", "PetController",
]
