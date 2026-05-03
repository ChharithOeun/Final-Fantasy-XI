"""Minimap clickthrough — central click event dispatcher.

The renderer hands every minimap click to this module, which
inspects the dot's kind and routes the click:

  MOB_HOSTILE / MOB_NEUTRAL / MOB_FRIENDLY
      -> minimap_difficulty_check.check_mob

  PARTY_MEMBER / OTHER_PLAYER / NPC
      -> minimap_player_profile.snapshot_for

  SELF
      -> blocked (you don't open a profile of yourself this way)

The dispatcher composes the snapshot from minimap_engine,
filters per the entity's DotKind, and packages a single
ClickResult that the HUD renders. Long clicks (hold) can be
distinguished from short clicks via the press_kind flag.

Public surface
--------------
    PressKind enum
    ClickResult dataclass
    MinimapClickthrough
        .__init__(engine, difficulty_checker, profile_registry)
        .handle_click(viewer_id, target_entity_id, press_kind,
                      viewer_level, enfeebling_skill)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.minimap_engine import (
    DotKind, MinimapEngine,
)
from server.minimap_difficulty_check import (
    DifficultyCheck, MinimapDifficultyChecker,
)
from server.minimap_player_profile import (
    MinimapPlayerProfileRegistry, ProfileSnapshot,
)


class PressKind(str, enum.Enum):
    SHORT = "short"     # tap — open card
    LONG = "long"       # hold — open extended menu
    DOUBLE = "double"   # double-click — focus camera


class ClickRouteKind(str, enum.Enum):
    DIFFICULTY_CHECK = "difficulty_check"
    PROFILE_SNAPSHOT = "profile_snapshot"
    NPC_INTERACTION = "npc_interaction"
    SELF_BLOCKED = "self_blocked"
    UNKNOWN_TARGET = "unknown_target"
    NOT_VISIBLE = "not_visible"
    NOT_CLICKABLE = "not_clickable"


@dataclasses.dataclass(frozen=True)
class ClickResult:
    accepted: bool
    route: ClickRouteKind
    press_kind: PressKind
    target_entity_id: str
    difficulty_check: t.Optional[DifficultyCheck] = None
    profile_snapshot: t.Optional[ProfileSnapshot] = None
    npc_id: t.Optional[str] = None
    note: str = ""


@dataclasses.dataclass
class MinimapClickthrough:
    engine: MinimapEngine
    difficulty_checker: MinimapDifficultyChecker
    profile_registry: MinimapPlayerProfileRegistry

    def handle_click(
        self, *, viewer_id: str,
        target_entity_id: str,
        press_kind: PressKind = PressKind.SHORT,
        viewer_level: int = 1,
        enfeebling_skill: int = 0,
    ) -> ClickResult:
        # Step 1: ensure the target dot is on the viewer's
        # current snapshot — i.e. they can actually see it.
        snap = self.engine.snapshot_for(viewer_id=viewer_id)
        if snap is None:
            return ClickResult(
                accepted=False,
                route=ClickRouteKind.UNKNOWN_TARGET,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                note="viewer not registered",
            )
        dot = next(
            (
                d for d in snap.dots
                if d.entity_id == target_entity_id
            ),
            None,
        )
        if dot is None:
            return ClickResult(
                accepted=False,
                route=ClickRouteKind.NOT_VISIBLE,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                note="target not in viewer's snapshot",
            )

        # Step 2: route by dot kind
        if dot.kind == DotKind.SELF:
            return ClickResult(
                accepted=False,
                route=ClickRouteKind.SELF_BLOCKED,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                note="cannot open self profile via minimap",
            )

        if not dot.clickable:
            return ClickResult(
                accepted=False,
                route=ClickRouteKind.NOT_CLICKABLE,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
            )

        if dot.kind in (
            DotKind.MOB_HOSTILE,
            DotKind.MOB_NEUTRAL,
            DotKind.MOB_FRIENDLY,
        ):
            check = self.difficulty_checker.check_mob(
                mob_id=target_entity_id,
                viewer_level=viewer_level,
                enfeebling_skill=enfeebling_skill,
            )
            if check is None:
                return ClickResult(
                    accepted=False,
                    route=ClickRouteKind.UNKNOWN_TARGET,
                    press_kind=press_kind,
                    target_entity_id=target_entity_id,
                    note="mob not registered with checker",
                )
            return ClickResult(
                accepted=True,
                route=ClickRouteKind.DIFFICULTY_CHECK,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                difficulty_check=check,
            )

        if dot.kind in (
            DotKind.PARTY_MEMBER,
            DotKind.OTHER_PLAYER,
        ):
            snap_card = self.profile_registry.snapshot_for(
                viewer_id=viewer_id,
                target_id=target_entity_id,
            )
            if snap_card is None:
                return ClickResult(
                    accepted=False,
                    route=ClickRouteKind.UNKNOWN_TARGET,
                    press_kind=press_kind,
                    target_entity_id=target_entity_id,
                    note="player has no profile registered",
                )
            return ClickResult(
                accepted=True,
                route=ClickRouteKind.PROFILE_SNAPSHOT,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                profile_snapshot=snap_card,
            )

        if dot.kind == DotKind.NPC:
            return ClickResult(
                accepted=True,
                route=ClickRouteKind.NPC_INTERACTION,
                press_kind=press_kind,
                target_entity_id=target_entity_id,
                npc_id=target_entity_id,
            )

        # Defensive default
        return ClickResult(
            accepted=False,
            route=ClickRouteKind.NOT_CLICKABLE,
            press_kind=press_kind,
            target_entity_id=target_entity_id,
        )


__all__ = [
    "PressKind", "ClickRouteKind", "ClickResult",
    "MinimapClickthrough",
]
