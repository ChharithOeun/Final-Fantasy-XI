"""Nation propaganda — official narrative about a defector.

Once an officer defects, the nation they left has a
choice: officially BRAND them a traitor, present them
as a TRAGIC EXILE seduced by enemies, claim they were
KIDNAPPED, or simply scrub them from public memory
(SUPPRESSED). The choice matters for how NPCs talk
about them, what posters appear in town, and whether
their family suffers harsher consequences.

A propaganda LINE has:
    line_id, nation_id, subject_npc, narrative,
    public_text, posted_day, retired_day, intensity

Narratives:
    TRAITOR        official enemy of the state
    TRAGIC_EXILE   sympathetic story; family
                   protected
    KIDNAPPED      "they were taken against their
                   will"
    SUPPRESSED     officially deny they existed
    HERO_RECLAIMED rare; a defector returns home and
                   the narrative pivots

Intensity 1..5: scales how loudly the propaganda
campaign is pushed (poster count, town crier
frequency).

Public surface
--------------
    Narrative enum
    PropagandaLine dataclass (frozen)
    NationPropagandaSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Narrative(str, enum.Enum):
    TRAITOR = "traitor"
    TRAGIC_EXILE = "tragic_exile"
    KIDNAPPED = "kidnapped"
    SUPPRESSED = "suppressed"
    HERO_RECLAIMED = "hero_reclaimed"


@dataclasses.dataclass(frozen=True)
class PropagandaLine:
    line_id: str
    nation_id: str
    subject_npc: str
    narrative: Narrative
    public_text: str
    intensity: int
    posted_day: int
    retired_day: t.Optional[int]


@dataclasses.dataclass
class NationPropagandaSystem:
    _lines: dict[str, PropagandaLine] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def post_line(
        self, *, nation_id: str,
        subject_npc: str, narrative: Narrative,
        public_text: str, intensity: int,
        posted_day: int,
    ) -> t.Optional[str]:
        if not nation_id or not subject_npc:
            return None
        if not public_text:
            return None
        if intensity < 1 or intensity > 5:
            return None
        if posted_day < 0:
            return None
        # Block parallel ACTIVE narrative for same
        # subject in same nation
        for ln in self._lines.values():
            if (ln.nation_id == nation_id
                    and ln.subject_npc == subject_npc
                    and ln.retired_day is None):
                return None
        lid = f"prop_{self._next_id}"
        self._next_id += 1
        self._lines[lid] = PropagandaLine(
            line_id=lid, nation_id=nation_id,
            subject_npc=subject_npc,
            narrative=narrative,
            public_text=public_text,
            intensity=intensity,
            posted_day=posted_day,
            retired_day=None,
        )
        return lid

    def retire_line(
        self, *, line_id: str, now_day: int,
    ) -> bool:
        if line_id not in self._lines:
            return False
        ln = self._lines[line_id]
        if ln.retired_day is not None:
            return False
        if now_day < ln.posted_day:
            return False
        self._lines[line_id] = dataclasses.replace(
            ln, retired_day=now_day,
        )
        return True

    def pivot_narrative(
        self, *, nation_id: str,
        subject_npc: str,
        new_narrative: Narrative,
        new_text: str, new_intensity: int,
        now_day: int,
    ) -> t.Optional[str]:
        """Retire the active narrative for this NPC
        in this nation and post a new one. Useful
        when a defector returns (TRAITOR -> HERO_
        RECLAIMED) or the regime softens its stance.
        """
        active = self.active_narrative(
            nation_id=nation_id,
            subject_npc=subject_npc,
        )
        if active is None:
            return None
        self.retire_line(
            line_id=active.line_id, now_day=now_day,
        )
        return self.post_line(
            nation_id=nation_id,
            subject_npc=subject_npc,
            narrative=new_narrative,
            public_text=new_text,
            intensity=new_intensity,
            posted_day=now_day,
        )

    def boost_intensity(
        self, *, line_id: str, delta: int,
    ) -> bool:
        if line_id not in self._lines:
            return False
        ln = self._lines[line_id]
        if ln.retired_day is not None:
            return False
        new_int = max(1, min(5, ln.intensity + delta))
        if new_int == ln.intensity:
            return False
        self._lines[line_id] = dataclasses.replace(
            ln, intensity=new_int,
        )
        return True

    def active_narrative(
        self, *, nation_id: str,
        subject_npc: str,
    ) -> t.Optional[PropagandaLine]:
        for ln in self._lines.values():
            if (ln.nation_id == nation_id
                    and ln.subject_npc == subject_npc
                    and ln.retired_day is None):
                return ln
        return None

    def history_for(
        self, *, nation_id: str,
        subject_npc: str,
    ) -> list[PropagandaLine]:
        return sorted(
            (ln for ln in self._lines.values()
             if (ln.nation_id == nation_id
                 and ln.subject_npc == subject_npc)),
            key=lambda ln: ln.posted_day,
        )

    def lines_in_nation(
        self, *, nation_id: str,
    ) -> list[PropagandaLine]:
        return [
            ln for ln in self._lines.values()
            if ln.nation_id == nation_id
        ]

    def line(
        self, *, line_id: str,
    ) -> t.Optional[PropagandaLine]:
        return self._lines.get(line_id)


__all__ = [
    "Narrative", "PropagandaLine",
    "NationPropagandaSystem",
]
