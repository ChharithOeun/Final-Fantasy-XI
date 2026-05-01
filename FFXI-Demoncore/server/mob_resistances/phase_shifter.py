"""Boss-grade affinity hiding + per-phase shifting.

Per MOB_RESISTANCES.md "Boss critic LLM and affinity hiding":
- A boss can suppress its affinity glow during the pristine phase
  (forcing the party to commit to a chain element before they fully
  read the affinity).
- A boss can shift affinity mid-fight: Maat opens dark-aligned,
  shifts to light at wounded (his MNK chi-flow), can flip to
  elemental-NONE during Hundred Fists (denying the 3x bonus).

This module is a deterministic phase machine: given current HP%
plus optional state flags (Hundred Fists active, etc.) it returns
the affinity that's currently in effect AND whether it's hidden.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .affinity import MobAffinity


@dataclasses.dataclass
class BossAffinityPhase:
    """One phase in a boss's affinity script.

    name      - debug label ("pristine", "wounded", "hundred_fists")
    affinity  - the MobAffinity in effect during this phase
    is_hidden - if True, players don't see the affinity glow
    hp_threshold - phase activates at HP% <= this (descending order)
    state_flag - optional named flag (e.g. "hundred_fists") that
                  must be present in the `flags` set to activate
    """
    name: str
    affinity: MobAffinity
    is_hidden: bool = False
    hp_threshold: float = 100.0
    state_flag: t.Optional[str] = None


class BossPhaseShifter:
    """Resolves the current phase for a boss-grade encounter."""

    def __init__(self, phases: list[BossAffinityPhase]) -> None:
        if not phases:
            raise ValueError("at least one phase required")
        self.phases = phases

    def current_phase(self,
                       *,
                       hp_pct: float,
                       flags: t.Optional[set[str]] = None,
                       ) -> BossAffinityPhase:
        """Pick the phase that applies right now.

        Resolution order:
        1. Phases gated by an active state_flag take precedence
           (e.g. Hundred Fists overrides whatever HP-driven phase
           would otherwise apply).
        2. Otherwise, the lowest hp_threshold the boss has dropped
           past is the active phase (descending HP).
        """
        flags = flags or set()

        # 1) State-flagged phases that match an active flag
        for phase in self.phases:
            if phase.state_flag is not None and phase.state_flag in flags:
                return phase

        # 2) HP-threshold resolution: among phases with no state_flag,
        # pick the one with the highest threshold the HP has fallen
        # at-or-below.
        candidates = [p for p in self.phases
                       if p.state_flag is None and hp_pct <= p.hp_threshold]
        if not candidates:
            # Defensive: HP > all thresholds (shouldn't happen if
            # 100% threshold exists). Fall back to first phase.
            return self.phases[0]

        # The smallest matching threshold is the most-recently-entered phase
        return min(candidates, key=lambda p: p.hp_threshold)

    def visible_affinity(self,
                          *,
                          hp_pct: float,
                          flags: t.Optional[set[str]] = None,
                          ) -> t.Optional[MobAffinity]:
        """The affinity that defenders can SEE. Hidden phases return
        None even though the underlying math still uses the real one."""
        phase = self.current_phase(hp_pct=hp_pct, flags=flags)
        if phase.is_hidden:
            return None
        return phase.affinity

    def effective_affinity(self,
                            *,
                            hp_pct: float,
                            flags: t.Optional[set[str]] = None,
                            ) -> MobAffinity:
        """The affinity the math actually uses for damage_multiplier."""
        return self.current_phase(hp_pct=hp_pct, flags=flags).affinity
