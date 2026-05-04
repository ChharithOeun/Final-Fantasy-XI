"""Boss phase telegraph — UI hint for phase + adaptation reveal.

When a boss enters a new phase (HP threshold crossed) or applies
an adaptation from boss_adaptation, the player needs a CLEAR
visual cue. This module produces TELEGRAPH events:

  PHASE_SHIFT       boss crossed an HP gate
  ADAPTATION_REVEAL boss is now resisting/dodging your prior pattern
  WS_WINDUP         boss is winding up a heavy weaponskill
  ENRAGE_INCOMING   timer below threshold; renderer pulses red
  ADD_SUMMON        boss summoned minions
  WEAKPOINT_OPEN    short window of vulnerability

Each telegraph carries a SEVERITY (LOW/MED/HIGH/EXTREME) that
the renderer translates to color + animation intensity.
Telegraphs auto-expire by lifetime.

Public surface
--------------
    TelegraphKind enum
    TelegraphSeverity enum
    BossTelegraph dataclass
    BossPhaseTelegraph
        .post_telegraph(boss_id, kind, severity, ...)
        .active_for_boss(boss_id)
        .ack(viewer_id, telegraph_id)
        .visible_to(viewer_id, boss_id)
        .tick(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default per-severity duration.
_SEVERITY_DURATION = {
    "low": 4.0,
    "med": 6.0,
    "high": 9.0,
    "extreme": 14.0,
}


class TelegraphKind(str, enum.Enum):
    PHASE_SHIFT = "phase_shift"
    ADAPTATION_REVEAL = "adaptation_reveal"
    WS_WINDUP = "ws_windup"
    ENRAGE_INCOMING = "enrage_incoming"
    ADD_SUMMON = "add_summon"
    WEAKPOINT_OPEN = "weakpoint_open"


class TelegraphSeverity(str, enum.Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    EXTREME = "extreme"


_SEVERITY_COLOR: dict[TelegraphSeverity, str] = {
    TelegraphSeverity.LOW: "white",
    TelegraphSeverity.MED: "yellow",
    TelegraphSeverity.HIGH: "orange",
    TelegraphSeverity.EXTREME: "red",
}


@dataclasses.dataclass(frozen=True)
class BossTelegraph:
    telegraph_id: str
    boss_id: str
    kind: TelegraphKind
    severity: TelegraphSeverity
    color: str
    title: str
    detail: str
    posted_at_seconds: float
    expires_at_seconds: float


@dataclasses.dataclass
class BossPhaseTelegraph:
    _telegraphs: dict[str, BossTelegraph] = dataclasses.field(
        default_factory=dict,
    )
    # viewer -> set of acked telegraph_ids
    _acked: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)
    _next_id: int = 0

    def post_telegraph(
        self, *, boss_id: str,
        kind: TelegraphKind,
        severity: TelegraphSeverity = TelegraphSeverity.MED,
        title: str = "",
        detail: str = "",
        now_seconds: float = 0.0,
        duration_seconds: t.Optional[float] = None,
    ) -> t.Optional[BossTelegraph]:
        if not boss_id:
            return None
        tid = f"telegraph_{self._next_id}"
        self._next_id += 1
        if duration_seconds is None:
            duration_seconds = _SEVERITY_DURATION[
                severity.value
            ]
        if not title:
            title = kind.value.replace("_", " ").title()
        tel = BossTelegraph(
            telegraph_id=tid, boss_id=boss_id,
            kind=kind, severity=severity,
            color=_SEVERITY_COLOR[severity],
            title=title, detail=detail,
            posted_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + duration_seconds
            ),
        )
        self._telegraphs[tid] = tel
        return tel

    def get(self, telegraph_id: str) -> t.Optional[BossTelegraph]:
        return self._telegraphs.get(telegraph_id)

    def active_for_boss(
        self, boss_id: str,
    ) -> tuple[BossTelegraph, ...]:
        return tuple(
            t_ for t_ in self._telegraphs.values()
            if t_.boss_id == boss_id
        )

    def ack(
        self, *, viewer_id: str, telegraph_id: str,
    ) -> bool:
        if telegraph_id not in self._telegraphs:
            return False
        self._acked.setdefault(
            viewer_id, set(),
        ).add(telegraph_id)
        return True

    def visible_to(
        self, *, viewer_id: str, boss_id: str,
    ) -> tuple[BossTelegraph, ...]:
        acked = self._acked.get(viewer_id, set())
        out: list[BossTelegraph] = []
        for t_ in self._telegraphs.values():
            if t_.boss_id != boss_id:
                continue
            if t_.telegraph_id in acked:
                continue
            out.append(t_)
        # Sort by severity (extreme first), then most recent
        order = list(TelegraphSeverity)
        out.sort(
            key=lambda x: (
                order.index(x.severity),
                -x.posted_at_seconds,
            ),
            reverse=False,
        )
        # Reverse so extreme appears first
        out.sort(
            key=lambda x: (
                -order.index(x.severity),
                -x.posted_at_seconds,
            ),
        )
        return tuple(out)

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for tid, t_ in list(self._telegraphs.items()):
            if now_seconds >= t_.expires_at_seconds:
                del self._telegraphs[tid]
                expired.append(tid)
        # Garbage collect ack entries
        for vid in list(self._acked.keys()):
            self._acked[vid] -= set(expired)
        return tuple(expired)

    def total_active(self) -> int:
        return len(self._telegraphs)


__all__ = [
    "TelegraphKind", "TelegraphSeverity",
    "BossTelegraph",
    "BossPhaseTelegraph",
]
