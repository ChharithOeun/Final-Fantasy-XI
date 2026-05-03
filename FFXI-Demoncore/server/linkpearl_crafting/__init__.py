"""Linkpearl crafting — LS leader produces pearls + sackets.

Each linkshell has a leader (Pearlshell holder). The leader can:
* craft Linkpearls to give to recruits (single-channel earpiece)
* craft Pearlsacks (alternate equipped LS slot, allows joining
  a second LS at once)
* recover Cracked Linkpearls — when a member is kicked, their
  pearl cracks and can be returned to the LS leader for re-issue

Pearl tiers:
    LINKPEARL — standard member earpiece
    PEARLSACK — 2nd-LS slot (canonical retail mechanic)
    PEARLSHELL — leader's master shell, transferrable

Each pearl has a durability counter. Catastrophic events
(member-killed-by-LS-conflict, etc.) chip durability; cracked
pearls drop to 0 durability and need leader re-issue.

Public surface
--------------
    PearlKind enum
    LinkpearlItem dataclass
    LinkpearlCraft
        .leader_can_craft(role, ls_size) -> bool
        .craft_pearl(...) -> Optional[LinkpearlItem]
        .crack(pearl_id) / .recover(pearl_id, leader_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


PEARL_DURABILITY_FRESH = 100
RECOVERED_PEARL_DURABILITY = 50    # cracked-then-recovered penalty
PEARLSACK_MIN_LS_RANK = 2          # member must be rank 2+ to issue
LEADER_ROLE = "leader"


class PearlKind(str, enum.Enum):
    LINKPEARL = "linkpearl"
    PEARLSACK = "pearlsack"
    PEARLSHELL = "pearlshell"


@dataclasses.dataclass
class LinkpearlItem:
    pearl_id: str
    kind: PearlKind
    linkshell_id: str
    issued_to: t.Optional[str] = None
    durability: int = PEARL_DURABILITY_FRESH
    cracked: bool = False


@dataclasses.dataclass(frozen=True)
class CraftResult:
    accepted: bool
    pearl: t.Optional[LinkpearlItem] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CrackResult:
    accepted: bool
    pearl_id: t.Optional[str] = None
    durability_after: int = 0
    cracked: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class LinkpearlCraft:
    """Per-linkshell crafting state. The LS leader operates one
    of these to issue pearls / recover cracked ones."""
    linkshell_id: str
    pearls: dict[str, LinkpearlItem] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def craft_pearl(
        self, *, leader_role: str, kind: PearlKind,
        recipient_id: str, recipient_ls_rank: int = 1,
    ) -> CraftResult:
        if leader_role != LEADER_ROLE:
            return CraftResult(False, reason="only leader can craft")
        if kind == PearlKind.PEARLSHELL:
            return CraftResult(False, reason="pearlshell is leader-only")
        if kind == PearlKind.PEARLSACK and \
                recipient_ls_rank < PEARLSACK_MIN_LS_RANK:
            return CraftResult(
                False, reason="pearlsack requires LS rank 2+",
            )
        pid = f"pearl_{self.linkshell_id}_{self._next_id}"
        self._next_id += 1
        item = LinkpearlItem(
            pearl_id=pid, kind=kind, linkshell_id=self.linkshell_id,
            issued_to=recipient_id,
        )
        self.pearls[pid] = item
        return CraftResult(True, pearl=item)

    def chip_durability(
        self, *, pearl_id: str, amount: int,
    ) -> CrackResult:
        item = self.pearls.get(pearl_id)
        if item is None:
            return CrackResult(False, reason="unknown pearl")
        if item.cracked:
            return CrackResult(False, reason="already cracked")
        item.durability = max(0, item.durability - amount)
        if item.durability == 0:
            item.cracked = True
        return CrackResult(
            True, pearl_id=pearl_id,
            durability_after=item.durability, cracked=item.cracked,
        )

    def crack(self, *, pearl_id: str) -> CrackResult:
        """Force-crack a pearl (e.g. owner kicked from LS)."""
        item = self.pearls.get(pearl_id)
        if item is None:
            return CrackResult(False, reason="unknown pearl")
        item.cracked = True
        item.durability = 0
        return CrackResult(
            True, pearl_id=pearl_id,
            durability_after=0, cracked=True,
        )

    def recover(
        self, *, leader_role: str, pearl_id: str,
    ) -> CraftResult:
        """Leader recovers a cracked pearl, restoring it to half-
        durability and ready for re-issue."""
        if leader_role != LEADER_ROLE:
            return CraftResult(False, reason="only leader can recover")
        item = self.pearls.get(pearl_id)
        if item is None:
            return CraftResult(False, reason="unknown pearl")
        if not item.cracked:
            return CraftResult(False, reason="pearl not cracked")
        item.cracked = False
        item.durability = RECOVERED_PEARL_DURABILITY
        item.issued_to = None
        return CraftResult(True, pearl=item)

    def reissue(
        self, *, leader_role: str, pearl_id: str,
        new_owner_id: str,
    ) -> CraftResult:
        if leader_role != LEADER_ROLE:
            return CraftResult(False, reason="only leader can reissue")
        item = self.pearls.get(pearl_id)
        if item is None:
            return CraftResult(False, reason="unknown pearl")
        if item.cracked:
            return CraftResult(False, reason="pearl is cracked")
        if item.issued_to is not None:
            return CraftResult(False, reason="pearl already issued")
        item.issued_to = new_owner_id
        return CraftResult(True, pearl=item)


__all__ = [
    "PEARL_DURABILITY_FRESH", "RECOVERED_PEARL_DURABILITY",
    "PEARLSACK_MIN_LS_RANK", "LEADER_ROLE",
    "PearlKind", "LinkpearlItem",
    "CraftResult", "CrackResult",
    "LinkpearlCraft",
]
