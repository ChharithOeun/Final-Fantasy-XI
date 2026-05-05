"""Kraken world boss — the abyss devil the DROWNED_PRINCES serve.

The Kraken is the apex of the underwater expansion: a HNM
that rises from the abyss_trench on a slow weekly cycle and
calls the DROWNED_PRINCES fleet to its surface raid. Sirens
warn of its approach (the REQUIEM tier of siren_lure marks
its arrival window). Sea lanes adjacent to the trench go
DANGEROUS automatically when it's surfaced.

Kraken cycle:
  DORMANT       - sleeping at the bottom (default)
  STIRRING      - 1h before surface; sirens sing requiems
  SURFACED      - 30 min window of full HNM combat
  RETREATING    - sinks back, dropping loot in its wake
  RECOVERING    - 7 days of dormant before next stir

Phase HP gates:
  PHASE_1 SUBMERGED      100% -> 75%   - tentacle sweeps
  PHASE_2 INK_CLOUD      75%  -> 40%   - blinds raid; spawns
                                          INKLINGS minions
  PHASE_3 ENRAGE_DEEP    40%  -> 10%   - dives + drags one
                                          random raider down
  PHASE_4 BLEEDING_GOD   10%  -> 0     - calls DROWNED_PRINCES
                                          fleet to its surface

Public surface
--------------
    KrakenStage enum
    KrakenPhase enum
    KrakenWorldBoss
        .observe(now_seconds) -> KrakenStage
        .schedule_next_stir(seed_seconds, weeks_offset)
        .resolve_phase(hp_remaining_pct) -> KrakenPhase
        .apply_damage(dmg, now_seconds) -> CombatTick
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class KrakenStage(str, enum.Enum):
    DORMANT = "dormant"
    STIRRING = "stirring"
    SURFACED = "surfaced"
    RETREATING = "retreating"
    RECOVERING = "recovering"


class KrakenPhase(str, enum.Enum):
    SUBMERGED = "submerged"
    INK_CLOUD = "ink_cloud"
    ENRAGE_DEEP = "enrage_deep"
    BLEEDING_GOD = "bleeding_god"


# stage durations (seconds)
_STIR_LEAD_SECONDS = 3_600           # 1h warning
_SURFACED_WINDOW_SECONDS = 30 * 60   # 30 min combat
_RETREATING_SECONDS = 5 * 60         # 5 min retreat
_RECOVERY_SECONDS = 7 * 24 * 3_600   # 7 days

# phase HP thresholds (%)
_PHASE_GATES: tuple[tuple[int, KrakenPhase], ...] = (
    (75, KrakenPhase.SUBMERGED),     # >=75 SUBMERGED
    (40, KrakenPhase.INK_CLOUD),     # 40..74 INK_CLOUD
    (10, KrakenPhase.ENRAGE_DEEP),   # 10..39 ENRAGE_DEEP
    # <10 BLEEDING_GOD
)

DEFAULT_HP_MAX = 1_000_000


@dataclasses.dataclass(frozen=True)
class CombatTick:
    accepted: bool
    hp_remaining: int = 0
    hp_pct: int = 0
    phase: t.Optional[KrakenPhase] = None
    defeated: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class KrakenWorldBoss:
    next_stir_at_seconds: int = 0
    hp_max: int = DEFAULT_HP_MAX
    hp_remaining: int = DEFAULT_HP_MAX
    scheduled: bool = False

    def schedule_next_stir(
        self, *, seed_seconds: int, weeks_offset: int = 0,
    ) -> None:
        if weeks_offset < 0:
            weeks_offset = 0
        self.next_stir_at_seconds = (
            seed_seconds + weeks_offset * _RECOVERY_SECONDS
        )
        self.scheduled = True
        # reset HP on every fresh schedule
        self.hp_remaining = self.hp_max

    def observe(self, *, now_seconds: int) -> KrakenStage:
        if not self.scheduled:
            return KrakenStage.DORMANT
        offset = now_seconds - self.next_stir_at_seconds
        if offset < 0:
            return KrakenStage.DORMANT
        # offset relative to the start of the stir
        if offset < _STIR_LEAD_SECONDS:
            return KrakenStage.STIRRING
        in_surfaced = offset - _STIR_LEAD_SECONDS
        if in_surfaced < _SURFACED_WINDOW_SECONDS:
            if self.hp_remaining <= 0:
                return KrakenStage.RETREATING
            return KrakenStage.SURFACED
        in_retreat = in_surfaced - _SURFACED_WINDOW_SECONDS
        if in_retreat < _RETREATING_SECONDS:
            return KrakenStage.RETREATING
        return KrakenStage.RECOVERING

    @staticmethod
    def resolve_phase(*, hp_remaining_pct: int) -> KrakenPhase:
        if hp_remaining_pct >= 75:
            return KrakenPhase.SUBMERGED
        if hp_remaining_pct >= 40:
            return KrakenPhase.INK_CLOUD
        if hp_remaining_pct >= 10:
            return KrakenPhase.ENRAGE_DEEP
        return KrakenPhase.BLEEDING_GOD

    def apply_damage(
        self, *, dmg: int, now_seconds: int,
    ) -> CombatTick:
        if dmg < 0:
            return CombatTick(False, reason="bad damage")
        stage = self.observe(now_seconds=now_seconds)
        if stage != KrakenStage.SURFACED:
            return CombatTick(False, reason="not surfaced")
        self.hp_remaining = max(0, self.hp_remaining - dmg)
        pct = (
            (self.hp_remaining * 100) // self.hp_max
            if self.hp_max > 0 else 0
        )
        phase = self.resolve_phase(hp_remaining_pct=pct)
        return CombatTick(
            accepted=True,
            hp_remaining=self.hp_remaining,
            hp_pct=pct,
            phase=phase,
            defeated=(self.hp_remaining == 0),
        )

    def is_defeated(self) -> bool:
        return self.hp_remaining == 0


__all__ = [
    "KrakenStage", "KrakenPhase",
    "CombatTick", "KrakenWorldBoss",
    "DEFAULT_HP_MAX",
]
