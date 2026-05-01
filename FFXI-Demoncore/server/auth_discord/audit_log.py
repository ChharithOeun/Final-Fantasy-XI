"""JSONL audit log per AUTH_DISCORD.md.

'Every chharbot moderation action writes a JSONL audit line to
~/.chharbot/discord-mod.log. A /why <user> command in any channel
returns the user's full moderation history.'
"""
from __future__ import annotations

import dataclasses
import json
import typing as t

from .moderation import ModAction, ModerationDecision, Trigger


@dataclasses.dataclass(frozen=True)
class AuditEntry:
    """One JSONL line in discord-mod.log."""
    audit_id: str
    at_time: float
    trigger: Trigger
    action: ModAction
    target_discord_id: t.Optional[str]
    rationale: str
    overridden: bool = False
    override_by: t.Optional[str] = None     # owner discord_id

    def to_jsonl(self) -> str:
        return json.dumps({
            "audit_id": self.audit_id,
            "at": self.at_time,
            "trigger": self.trigger.value,
            "action": self.action.value,
            "target": self.target_discord_id,
            "rationale": self.rationale,
            "overridden": self.overridden,
            "override_by": self.override_by,
        })


class AuditLog:
    """In-memory implementation. Persistence stub — caller wires
    JSONL append to ~/.chharbot/discord-mod.log."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._next_id = 1

    def record(self,
                  *,
                  decision: ModerationDecision,
                  at_time: float,
                  ) -> AuditEntry:
        audit_id = f"audit_{self._next_id:08d}"
        self._next_id += 1
        entry = AuditEntry(
            audit_id=audit_id, at_time=at_time,
            trigger=decision.trigger, action=decision.action,
            target_discord_id=decision.target_discord_id,
            rationale=decision.rationale,
        )
        self._entries.append(entry)
        return entry

    def mark_overridden(self,
                            audit_id: str,
                            *,
                            override_by_discord_id: str,
                            ) -> bool:
        for i, e in enumerate(self._entries):
            if e.audit_id == audit_id:
                self._entries[i] = dataclasses.replace(
                    e, overridden=True,
                    override_by=override_by_discord_id,
                )
                return True
        return False

    def history_for(self, target_discord_id: str) -> list[AuditEntry]:
        """The /why command surfaces this list."""
        return [e for e in self._entries
                  if e.target_discord_id == target_discord_id]

    def __len__(self) -> int:
        return len(self._entries)

    def to_jsonl(self) -> str:
        """Render the whole log as JSONL. Tests assert per-line shape."""
        return "\n".join(e.to_jsonl() for e in self._entries)
