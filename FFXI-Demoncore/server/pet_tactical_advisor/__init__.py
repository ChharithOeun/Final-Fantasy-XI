"""Pet tactical advisor — what should the pet do RIGHT NOW.

Parallel to combat_tactics for player-summoned pets:
* PUP automatons (Frame + Head config drives behavior)
* SMN avatars (perpetuation + BP availability)
* BST charmed mobs / jugged pets
* GEO luopans (placement + indi/geo bubble state)

Pets in Demoncore are themselves AI-driven, with the canonical
pet_ai_directive command vocabulary as their input space. This
module is the deterministic recommendation system the pet AI
agent consults each tick. Its inputs are richer than mob
combat_tactics because it must consider the MASTER's state
(low HP -> fall back to defend; engaged WS -> assist), the
COMMAND last issued by the master, and any pet-specific
resource (PUP automaton oil, SMN MP perpetuation, BST pet HP).

Recommendations
---------------
PetTacticalIntent has:
* primary_target_id (None = stand by master)
* mode (ASSIST / DEFEND_MASTER / RECOVER / RETREAT_TO_MASTER /
        EXECUTE_COMMAND / SPECIAL)
* should_use_signature (BP / Maneuver / pet 2hr)
* recall_recommended (master should despawn — out of resources)
* notes (for the LLM prompt)

Public surface
--------------
    PetKind enum (PUPPET / AVATAR / BEAST / LUOPAN)
    PetMode enum
    PetState dataclass — current pet status snapshot
    MasterState dataclass — what the master is doing
    PetTacticalIntent dataclass
    PetTacticalAdvisor.recommend(...)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PetKind(str, enum.Enum):
    PUPPET = "puppet"
    AVATAR = "avatar"
    BEAST = "beast"
    LUOPAN = "luopan"


class PetMode(str, enum.Enum):
    ASSIST = "assist"                  # attack master's target
    DEFEND_MASTER = "defend_master"    # tank for master
    RECOVER = "recover"                # heal/regen, hold position
    RETREAT_TO_MASTER = "retreat_to_master"
    EXECUTE_COMMAND = "execute_command"
    SPECIAL = "special"                # pet 2hr / signature


# Thresholds.
PET_LOW_HP = 30
MASTER_LOW_HP = 25
PUP_LOW_OIL = 15
SMN_LOW_MP_PCT = 20
RECALL_PUP_OIL = 5
RECALL_AVATAR_MP_PCT = 5


@dataclasses.dataclass(frozen=True)
class MasterState:
    master_id: str
    hp_pct: int
    mp_pct: int
    engaged_target_id: t.Optional[str] = None
    casting_or_ws: bool = False
    last_command_id: t.Optional[str] = None
    is_in_combat: bool = True


@dataclasses.dataclass(frozen=True)
class PetState:
    pet_id: str
    kind: PetKind
    hp_pct: int
    mp_pct: int = 100
    pup_oil_pct: int = 100              # PUP only
    has_signature_ready: bool = False    # 2hr / overdrive
    engaged_target_id: t.Optional[str] = None
    distance_to_master_tiles: int = 5


@dataclasses.dataclass(frozen=True)
class PetTacticalIntent:
    primary_target_id: t.Optional[str]
    mode: PetMode
    should_use_signature: bool = False
    recall_recommended: bool = False
    notes: str = ""


def _master_in_danger(master: MasterState) -> bool:
    return master.hp_pct < MASTER_LOW_HP


def _pet_low_resources(state: PetState) -> bool:
    if state.kind == PetKind.PUPPET:
        return state.pup_oil_pct < PUP_LOW_OIL
    if state.kind == PetKind.AVATAR:
        return state.mp_pct < SMN_LOW_MP_PCT
    return False


def _should_recall(state: PetState) -> bool:
    if state.kind == PetKind.PUPPET:
        return state.pup_oil_pct < RECALL_PUP_OIL
    if state.kind == PetKind.AVATAR:
        return state.mp_pct < RECALL_AVATAR_MP_PCT
    if state.kind == PetKind.BEAST and state.hp_pct < 5:
        return True
    return False


@dataclasses.dataclass
class PetTacticalAdvisor:
    def recommend(
        self, *, pet: PetState, master: MasterState,
    ) -> PetTacticalIntent:
        # 1) Hard recall — pet is about to die / out of resources
        if _should_recall(pet):
            return PetTacticalIntent(
                primary_target_id=None,
                mode=PetMode.RECOVER,
                recall_recommended=True,
                notes=(
                    "pet about to despawn from resource exhaustion"
                ),
            )
        # 2) Pet itself low HP -> back off, hold by master
        if pet.hp_pct < PET_LOW_HP:
            return PetTacticalIntent(
                primary_target_id=None,
                mode=PetMode.RECOVER,
                notes=(
                    f"pet hp {pet.hp_pct}% — recover near master"
                ),
            )
        # 3) Master in danger -> defend
        if _master_in_danger(master):
            return PetTacticalIntent(
                primary_target_id=master.engaged_target_id,
                mode=PetMode.DEFEND_MASTER,
                notes=(
                    f"master hp {master.hp_pct}% — drawing aggro"
                ),
            )
        # 4) Pet far from master and master in combat -> recall
        if (
            master.is_in_combat
            and pet.distance_to_master_tiles > 30
        ):
            return PetTacticalIntent(
                primary_target_id=None,
                mode=PetMode.RETREAT_TO_MASTER,
                notes=(
                    f"pet too far ({pet.distance_to_master_tiles}t)"
                ),
            )
        # 5) Master casting WS or spell -> save signature for it
        if (
            master.casting_or_ws
            and pet.has_signature_ready
            and not _pet_low_resources(pet)
        ):
            return PetTacticalIntent(
                primary_target_id=master.engaged_target_id,
                mode=PetMode.SPECIAL,
                should_use_signature=True,
                notes="master midcast — fire pet signature now",
            )
        # 6) Default: assist on master's target if engaged
        if master.engaged_target_id is not None:
            return PetTacticalIntent(
                primary_target_id=master.engaged_target_id,
                mode=PetMode.ASSIST,
                notes="assisting master",
            )
        # 7) No target — execute last command if any
        if master.last_command_id is not None:
            return PetTacticalIntent(
                primary_target_id=None,
                mode=PetMode.EXECUTE_COMMAND,
                notes=(
                    f"executing last command "
                    f"{master.last_command_id}"
                ),
            )
        # 8) Stand by master
        return PetTacticalIntent(
            primary_target_id=None,
            mode=PetMode.RETREAT_TO_MASTER,
            notes="no orders — hold by master",
        )


__all__ = [
    "PetKind", "PetMode",
    "PET_LOW_HP", "MASTER_LOW_HP",
    "PUP_LOW_OIL", "SMN_LOW_MP_PCT",
    "RECALL_PUP_OIL", "RECALL_AVATAR_MP_PCT",
    "MasterState", "PetState", "PetTacticalIntent",
    "PetTacticalAdvisor",
]
