"""Chocobo egg lifecycle — laying through hatching, color
maintenance, and rainbow R/EX handling.

An egg is laid via the breeder NPC (see chocobo_breed_matrix
for the cross-breed flow). It then INCUBATES at the NPC for 90
real-earth days. During that window the OWNING BREEDER may:

  - maintain_color   - keep the current color alive (consumes
                       resources; failing to maintain risks the
                       color decaying back to YELLOW base)
  - change_color     - attempt to shift to a different color via
                       a NPC quest with rare resources
                       (success rolled against bloodline traits)

At hatch, the chick's color = the egg's color at the moment of
hatching. RAINBOW eggs are R/EX (account-bound) — they cannot
be traded and re-roll the full hatch cycle when the rainbow
chocobo dies.

A breeder may keep AT MOST one mount OR one egg at a time.

Public surface
--------------
    EggState enum        LAID / INCUBATING / HATCHED / SPOILED
    Egg dataclass
    EggLifecycle
        .lay(breeder_id, color, bloodline_traits, is_rainbow,
             now_seconds)
        .maintain_color(breeder_id, now_seconds, resources_paid)
        .change_color(breeder_id, target_color, now_seconds,
                      resources_paid, success_roll_pct)
        .hatch(breeder_id, now_seconds)
        .check(breeder_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.chocobo_colors import ChocoboColor


_HATCH_SECONDS = 90 * 86_400              # 90 real-earth days
_MAINTAIN_INTERVAL = 7 * 86_400           # weekly maintenance check
_MAINTAIN_GRACE = 3 * 86_400              # 3 days late before decay


class EggState(str, enum.Enum):
    LAID = "laid"
    INCUBATING = "incubating"
    HATCHED = "hatched"
    SPOILED = "spoiled"


@dataclasses.dataclass
class Egg:
    breeder_id: str
    color: ChocoboColor
    bloodline_traits: tuple[str, ...]
    is_rainbow: bool
    state: EggState
    laid_at: int
    hatch_due_at: int
    last_maintained_at: int


@dataclasses.dataclass(frozen=True)
class LayResult:
    accepted: bool
    color: t.Optional[ChocoboColor] = None
    hatch_due_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class MaintainResult:
    accepted: bool
    color_after: t.Optional[ChocoboColor] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ChangeColorResult:
    accepted: bool
    color_after: t.Optional[ChocoboColor] = None
    succeeded: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class HatchResult:
    accepted: bool
    chick_color: t.Optional[ChocoboColor] = None
    is_rainbow: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class EggSnapshot:
    state: EggState
    color: t.Optional[ChocoboColor] = None
    seconds_until_hatch: int = 0
    is_rainbow: bool = False


@dataclasses.dataclass
class EggLifecycle:
    _eggs: dict[str, Egg] = dataclasses.field(default_factory=dict)

    def lay(
        self, *, breeder_id: str,
        color: ChocoboColor,
        bloodline_traits: tuple[str, ...],
        is_rainbow: bool,
        now_seconds: int,
    ) -> LayResult:
        if breeder_id in self._eggs:
            existing = self._eggs[breeder_id]
            if existing.state in (
                EggState.LAID, EggState.INCUBATING,
            ):
                return LayResult(
                    False, reason="breeder already holds an egg",
                )
        # Rainbow eggs cannot be cross-bred — they only re-spawn
        # from a dead rainbow. lay() is still allowed (the caller
        # is responsible for context); we just flag the egg.
        e = Egg(
            breeder_id=breeder_id,
            color=color,
            bloodline_traits=tuple(bloodline_traits),
            is_rainbow=is_rainbow,
            state=EggState.INCUBATING,
            laid_at=now_seconds,
            hatch_due_at=now_seconds + _HATCH_SECONDS,
            last_maintained_at=now_seconds,
        )
        self._eggs[breeder_id] = e
        return LayResult(
            accepted=True,
            color=color,
            hatch_due_at=e.hatch_due_at,
        )

    def _resolve_decay(
        self, e: Egg, now_seconds: int,
    ) -> None:
        """If the egg has gone too long without maintenance, decay
        the color back to YELLOW (the unmaintained base). Runs
        once per check; does nothing if maintenance is current."""
        if e.state != EggState.INCUBATING:
            return
        elapsed = now_seconds - e.last_maintained_at
        if elapsed > _MAINTAIN_INTERVAL + _MAINTAIN_GRACE:
            if e.color != ChocoboColor.YELLOW:
                e.color = ChocoboColor.YELLOW

    def maintain_color(
        self, *, breeder_id: str,
        now_seconds: int,
        resources_paid: bool,
    ) -> MaintainResult:
        e = self._eggs.get(breeder_id)
        if e is None:
            return MaintainResult(
                False, reason="no egg",
            )
        if e.state != EggState.INCUBATING:
            return MaintainResult(
                False, color_after=e.color,
                reason="egg not incubating",
            )
        if not resources_paid:
            return MaintainResult(
                False, color_after=e.color,
                reason="resources not paid",
            )
        e.last_maintained_at = now_seconds
        return MaintainResult(
            accepted=True, color_after=e.color,
        )

    def change_color(
        self, *, breeder_id: str,
        target_color: ChocoboColor,
        now_seconds: int,
        resources_paid: bool,
        success_roll_pct: int,
    ) -> ChangeColorResult:
        e = self._eggs.get(breeder_id)
        if e is None:
            return ChangeColorResult(
                False, reason="no egg",
            )
        if e.state != EggState.INCUBATING:
            return ChangeColorResult(
                False, color_after=e.color,
                reason="egg not incubating",
            )
        if not resources_paid:
            return ChangeColorResult(
                False, color_after=e.color,
                reason="resources not paid",
            )
        if not (0 <= success_roll_pct <= 100):
            return ChangeColorResult(
                False, color_after=e.color,
                reason="invalid roll",
            )
        # 70% base success rate; rainbow eggs are immune to
        # color change (their color is a separate spec)
        if e.is_rainbow:
            return ChangeColorResult(
                False, color_after=e.color,
                reason="rainbow egg cannot be color-shifted",
            )
        succeeded = success_roll_pct < 70
        if succeeded:
            e.color = target_color
            e.last_maintained_at = now_seconds
        return ChangeColorResult(
            accepted=True,
            color_after=e.color,
            succeeded=succeeded,
        )

    def hatch(
        self, *, breeder_id: str, now_seconds: int,
    ) -> HatchResult:
        e = self._eggs.get(breeder_id)
        if e is None:
            return HatchResult(False, reason="no egg")
        if e.state != EggState.INCUBATING:
            return HatchResult(False, reason="egg not incubating")
        if now_seconds < e.hatch_due_at:
            return HatchResult(
                False, reason="not yet ready to hatch",
            )
        self._resolve_decay(e, now_seconds)
        e.state = EggState.HATCHED
        return HatchResult(
            accepted=True,
            chick_color=e.color,
            is_rainbow=e.is_rainbow,
        )

    def check(
        self, *, breeder_id: str, now_seconds: int,
    ) -> EggSnapshot:
        e = self._eggs.get(breeder_id)
        if e is None:
            return EggSnapshot(state=EggState.SPOILED)
        self._resolve_decay(e, now_seconds)
        seconds_until = max(0, e.hatch_due_at - now_seconds)
        return EggSnapshot(
            state=e.state,
            color=e.color,
            seconds_until_hatch=seconds_until,
            is_rainbow=e.is_rainbow,
        )

    def total_eggs(self) -> int:
        return len(self._eggs)


__all__ = [
    "EggState", "Egg",
    "LayResult", "MaintainResult",
    "ChangeColorResult", "HatchResult", "EggSnapshot",
    "EggLifecycle",
]
