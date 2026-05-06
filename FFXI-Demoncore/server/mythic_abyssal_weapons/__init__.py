"""Mythic abyssal weapons — top-of-ladder forge progression.

The single most valuable item path in the underwater game.
Each weapon is forged through 5 mandatory stages, each
opening a new trait slot. The whole chain costs months of
work and only one mythic per player at a time.

Stages (each adds a TRAIT):
    1  BLUEPRINT_RECOVERY    - find lost blueprint from a
                               wreck (50+ wrecks salvaged)
    2  HUNDRED_WRECKS        - 100 lifetime wrecks
    3  DROWNED_KING_KILL     - prove yourself in T7 raid
    4  MASTER_SYNTHESIS      - HQ proc on a wave-temple
                               recipe (gated by Master craft)
    5  NAME_INSCRIPTION      - choose 1-rune name; locks the
                               weapon to you forever

Each stage adds a TRAIT to the weapon's growing trait list.
The TRAITS are PUBLIC — when you wield it, anyone can
inspect and see your forge story.

Public surface
--------------
    ForgeStage int enum
    MythicTrait dataclass (frozen)
    MythicWeapon dataclass (frozen)
    MythicAbyssalWeapons
        .start_forge(player_id, weapon_kind, now_seconds)
        .complete_stage(player_id, stage, trait, now_seconds)
        .inscribe_name(player_id, rune_name, now_seconds)
        .weapon_for(player_id) -> Optional[MythicWeapon]
        .traits_of(player_id) -> tuple[MythicTrait, ...]
        .stage_of(player_id) -> Optional[ForgeStage]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ForgeStage(int, enum.Enum):
    BLUEPRINT_RECOVERY = 1
    HUNDRED_WRECKS = 2
    DROWNED_KING_KILL = 3
    MASTER_SYNTHESIS = 4
    NAME_INSCRIPTION = 5


@dataclasses.dataclass(frozen=True)
class MythicTrait:
    stage: ForgeStage
    name: str
    description: str
    earned_at_seconds: int


@dataclasses.dataclass(frozen=True)
class MythicWeapon:
    player_id: str
    weapon_kind: str
    inscribed_name: t.Optional[str]
    traits: tuple[MythicTrait, ...]
    started_at_seconds: int


@dataclasses.dataclass
class _ForgeState:
    player_id: str
    weapon_kind: str
    started_at: int
    traits: list[MythicTrait] = dataclasses.field(default_factory=list)
    inscribed_name: t.Optional[str] = None


@dataclasses.dataclass
class MythicAbyssalWeapons:
    _forges: dict[str, _ForgeState] = dataclasses.field(default_factory=dict)

    def start_forge(
        self, *, player_id: str,
        weapon_kind: str,
        now_seconds: int,
    ) -> bool:
        if not player_id or not weapon_kind:
            return False
        if player_id in self._forges:
            return False  # one mythic per player
        self._forges[player_id] = _ForgeState(
            player_id=player_id,
            weapon_kind=weapon_kind,
            started_at=now_seconds,
        )
        return True

    def complete_stage(
        self, *, player_id: str,
        stage: ForgeStage,
        trait_name: str,
        trait_description: str,
        now_seconds: int,
    ) -> bool:
        if stage == ForgeStage.NAME_INSCRIPTION:
            return False  # use inscribe_name instead
        f = self._forges.get(player_id)
        if f is None:
            return False
        # must complete stages in order
        expected_stage = ForgeStage(len(f.traits) + 1)
        if stage != expected_stage:
            return False
        f.traits.append(MythicTrait(
            stage=stage,
            name=trait_name,
            description=trait_description,
            earned_at_seconds=now_seconds,
        ))
        return True

    def inscribe_name(
        self, *, player_id: str,
        rune_name: str,
        now_seconds: int,
    ) -> bool:
        f = self._forges.get(player_id)
        if f is None:
            return False
        # must have completed first 4 stages
        if len(f.traits) != 4:
            return False
        if f.inscribed_name is not None:
            return False
        if not rune_name or len(rune_name) > 16:
            return False
        f.inscribed_name = rune_name
        f.traits.append(MythicTrait(
            stage=ForgeStage.NAME_INSCRIPTION,
            name=f"Inscribed: {rune_name}",
            description="One-rune name forever bound.",
            earned_at_seconds=now_seconds,
        ))
        return True

    def weapon_for(
        self, *, player_id: str,
    ) -> t.Optional[MythicWeapon]:
        f = self._forges.get(player_id)
        if f is None:
            return None
        return MythicWeapon(
            player_id=f.player_id,
            weapon_kind=f.weapon_kind,
            inscribed_name=f.inscribed_name,
            traits=tuple(f.traits),
            started_at_seconds=f.started_at,
        )

    def traits_of(
        self, *, player_id: str,
    ) -> tuple[MythicTrait, ...]:
        f = self._forges.get(player_id)
        return tuple(f.traits) if f else ()

    def stage_of(
        self, *, player_id: str,
    ) -> t.Optional[ForgeStage]:
        f = self._forges.get(player_id)
        if f is None:
            return None
        # next stage to complete
        next_idx = len(f.traits) + 1
        if next_idx > len(ForgeStage):
            return None  # fully complete
        return ForgeStage(next_idx)


__all__ = [
    "ForgeStage", "MythicTrait", "MythicWeapon",
    "MythicAbyssalWeapons",
]
