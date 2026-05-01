"""/pol command — party stage summary.

Per VISUAL_HEALTH_SYSTEM.md the /pol command provides:
    'A free, vague summary of the party: how many people are at
     each stage. "Party: 3 pristine, 1 wounded, 1 broken." No
     names, no numbers. Useful in chaotic raids.'

We surface this as a server-side reducer that the LSB/orchestrator
calls when a party member presses /pol.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .damage_stages import DamageStage


# Stage rendering order — the doc's example string lists them
# pristine-first. Stages with zero count are omitted.
_STAGE_RENDER_ORDER: tuple[DamageStage, ...] = (
    DamageStage.PRISTINE,
    DamageStage.SCUFFED,
    DamageStage.BLOODIED,
    DamageStage.WOUNDED,
    DamageStage.GRIEVOUS,
    DamageStage.BROKEN,
    DamageStage.DEAD,
)


@dataclasses.dataclass(frozen=True)
class PartyStageSummary:
    """One /pol return value."""
    counts: dict[DamageStage, int]
    party_size: int

    def render(self) -> str:
        """Doc-example string: 'Party: 3 pristine, 1 wounded, 1 broken'."""
        parts: list[str] = []
        for stage in _STAGE_RENDER_ORDER:
            n = self.counts.get(stage, 0)
            if n <= 0:
                continue
            parts.append(f"{n} {stage.value}")
        if not parts:
            return "Party: empty"
        return "Party: " + ", ".join(parts)


def summarize_party(stages: t.Iterable[DamageStage]) -> PartyStageSummary:
    """Reduce a sequence of party-member stages into a render."""
    counts: dict[DamageStage, int] = {}
    n = 0
    for s in stages:
        counts[s] = counts.get(s, 0) + 1
        n += 1
    return PartyStageSummary(counts=counts, party_size=n)
