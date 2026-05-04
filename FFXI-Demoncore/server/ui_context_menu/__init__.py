"""UI context menu — right-click action menu on player names.

Right-click on a player's name (in chat) or on their character
in the world produces a popup with these actions:

  TELL          send a /tell
  REPLY         /tell back to the last sender
  CHECK         examine — gear, level, jobs, fame; with an
                  ADD_FRIEND button if not already a friend
  BROWSE_WARES  open their bazaar (with world-tax applied)
  BLOCK         add to blacklist
  REPORT        flag for moderation review

Block prunes future actions: a blocked player's right-click
shows only UNBLOCK + REPORT. World-tax on bazaar applies
regardless of where the bazaar is opened — selling out in the
wilds doesn't let you escape the tax man.

Public surface
--------------
    ContextActionKind enum
    ActionAvailability dataclass
    ContextMenu dataclass
    ContextActionResult dataclass
    UIContextMenu
        .build_menu(viewer_id, target_id, has_last_tell,
                    target_has_bazaar, friends_already)
        .invoke(viewer_id, target_id, action, ...)
        .block / .unblock / .report
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# World tax applied to ALL bazaar transactions, no matter
# where they happen.
DEFAULT_BAZAAR_TAX_PCT = 7


class ContextActionKind(str, enum.Enum):
    TELL = "tell"
    REPLY = "reply"
    CHECK = "check"
    ADD_FRIEND = "add_friend"
    BROWSE_WARES = "browse_wares"
    BLOCK = "block"
    UNBLOCK = "unblock"
    REPORT = "report"


@dataclasses.dataclass(frozen=True)
class ActionAvailability:
    kind: ContextActionKind
    enabled: bool
    label: str = ""
    note: str = ""


@dataclasses.dataclass(frozen=True)
class ContextMenu:
    viewer_id: str
    target_id: str
    actions: tuple[ActionAvailability, ...]
    target_blocked: bool


@dataclasses.dataclass(frozen=True)
class BazaarBrowseResult:
    accepted: bool
    target_id: str
    tax_pct: int
    note: str = ""


@dataclasses.dataclass(frozen=True)
class ActionInvocationResult:
    accepted: bool
    action: ContextActionKind
    bazaar_result: t.Optional[BazaarBrowseResult] = None
    note: str = ""


@dataclasses.dataclass
class UIContextMenu:
    bazaar_tax_pct: int = DEFAULT_BAZAAR_TAX_PCT
    # viewer -> set of blocked target_ids
    _blocked: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # accumulator of submitted reports; (viewer, target) -> count
    _reports: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict,
    )

    def is_blocked(
        self, *, viewer_id: str, target_id: str,
    ) -> bool:
        return target_id in self._blocked.get(viewer_id, set())

    def block(
        self, *, viewer_id: str, target_id: str,
    ) -> bool:
        if viewer_id == target_id:
            return False
        s = self._blocked.setdefault(viewer_id, set())
        if target_id in s:
            return False
        s.add(target_id)
        return True

    def unblock(
        self, *, viewer_id: str, target_id: str,
    ) -> bool:
        s = self._blocked.get(viewer_id)
        if s is None or target_id not in s:
            return False
        s.discard(target_id)
        return True

    def report(
        self, *, viewer_id: str, target_id: str,
    ) -> int:
        if viewer_id == target_id:
            return 0
        key = (viewer_id, target_id)
        self._reports[key] = self._reports.get(key, 0) + 1
        return self._reports[key]

    def report_count(
        self, *, viewer_id: str, target_id: str,
    ) -> int:
        return self._reports.get((viewer_id, target_id), 0)

    def build_menu(
        self, *, viewer_id: str, target_id: str,
        has_last_tell: bool = False,
        target_has_bazaar: bool = False,
        friends_already: bool = False,
    ) -> ContextMenu:
        blocked = self.is_blocked(
            viewer_id=viewer_id, target_id=target_id,
        )
        actions: list[ActionAvailability] = []
        if blocked:
            # Pruned menu when target is blocked
            actions.append(ActionAvailability(
                kind=ContextActionKind.UNBLOCK,
                enabled=True, label="Unblock",
            ))
            actions.append(ActionAvailability(
                kind=ContextActionKind.REPORT,
                enabled=True, label="Report",
            ))
            return ContextMenu(
                viewer_id=viewer_id, target_id=target_id,
                actions=tuple(actions),
                target_blocked=True,
            )

        actions.append(ActionAvailability(
            kind=ContextActionKind.TELL,
            enabled=True, label="Send /tell",
        ))
        actions.append(ActionAvailability(
            kind=ContextActionKind.REPLY,
            enabled=has_last_tell,
            label="Reply",
            note="" if has_last_tell else (
                "no recent tell from this player"
            ),
        ))
        # CHECK with optional ADD_FRIEND submenu flag
        actions.append(ActionAvailability(
            kind=ContextActionKind.CHECK,
            enabled=True,
            label="Check (examine)",
            note=(
                "" if friends_already
                else "tap to add to friend list"
            ),
        ))
        actions.append(ActionAvailability(
            kind=ContextActionKind.ADD_FRIEND,
            enabled=not friends_already,
            label="Add Friend",
            note=(
                "already on your friend list"
                if friends_already else ""
            ),
        ))
        actions.append(ActionAvailability(
            kind=ContextActionKind.BROWSE_WARES,
            enabled=target_has_bazaar,
            label="Browse Wares",
            note=(
                f"world tax {self.bazaar_tax_pct}% applies"
                if target_has_bazaar
                else "no bazaar open"
            ),
        ))
        actions.append(ActionAvailability(
            kind=ContextActionKind.BLOCK,
            enabled=True, label="Block",
        ))
        actions.append(ActionAvailability(
            kind=ContextActionKind.REPORT,
            enabled=True, label="Report",
        ))
        return ContextMenu(
            viewer_id=viewer_id, target_id=target_id,
            actions=tuple(actions),
            target_blocked=False,
        )

    def invoke(
        self, *, viewer_id: str, target_id: str,
        action: ContextActionKind,
        target_has_bazaar: bool = False,
    ) -> ActionInvocationResult:
        if viewer_id == target_id and action != (
            ContextActionKind.CHECK
        ):
            return ActionInvocationResult(
                False, action=action,
                note="cannot self-invoke that action",
            )
        if action == ContextActionKind.BROWSE_WARES:
            if not target_has_bazaar:
                return ActionInvocationResult(
                    False, action=action,
                    note="no bazaar open",
                )
            if self.is_blocked(
                viewer_id=viewer_id, target_id=target_id,
            ):
                return ActionInvocationResult(
                    False, action=action,
                    note="target blocked",
                )
            return ActionInvocationResult(
                accepted=True, action=action,
                bazaar_result=BazaarBrowseResult(
                    accepted=True, target_id=target_id,
                    tax_pct=self.bazaar_tax_pct,
                ),
            )
        if action == ContextActionKind.BLOCK:
            ok = self.block(
                viewer_id=viewer_id, target_id=target_id,
            )
            return ActionInvocationResult(
                accepted=ok, action=action,
                note="" if ok else "already blocked",
            )
        if action == ContextActionKind.UNBLOCK:
            ok = self.unblock(
                viewer_id=viewer_id, target_id=target_id,
            )
            return ActionInvocationResult(
                accepted=ok, action=action,
                note="" if ok else "not blocked",
            )
        if action == ContextActionKind.REPORT:
            count = self.report(
                viewer_id=viewer_id, target_id=target_id,
            )
            return ActionInvocationResult(
                accepted=count > 0, action=action,
                note=f"report {count}",
            )
        # TELL / REPLY / CHECK / ADD_FRIEND are pass-through —
        # the server-side handler for those lives elsewhere.
        # We just acknowledge.
        return ActionInvocationResult(
            accepted=True, action=action,
        )

    def total_block_targets(
        self, *, viewer_id: str,
    ) -> int:
        return len(self._blocked.get(viewer_id, set()))


__all__ = [
    "DEFAULT_BAZAAR_TAX_PCT",
    "ContextActionKind",
    "ActionAvailability", "ContextMenu",
    "BazaarBrowseResult", "ActionInvocationResult",
    "UIContextMenu",
]
