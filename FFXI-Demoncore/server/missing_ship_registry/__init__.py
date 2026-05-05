"""Missing ship registry — the ledger that closes the surface
mystery of "ships that never came back".

Combines three upstream signals:

  - airship_ferry encounters that ended with the ship NOT
    arriving (crash / pirate boarding / silence)
  - sea_pirate_factions encounters whose outcome was
    SHIP_LOST or PIRATES_BOARD with abducted=True
  - siren_lure DIVERT/SHIPWRECK events

Each report becomes a WreckRecord pinned to an underwater
ZONE (typically WRECKAGE_GRAVEYARD) and a CAUSE. The wreck
can then be SALVAGED by underwater divers (jobs from
underwater_jobs) for cargo + crew search hooks.

A wreck has a STATE (FRESH / PICKED_OVER / STRIPPED). Each
salvage attempt yields cargo proportional to remaining state
and degrades the state. Crew search results feed the
abduction loop — abducted crew may surface as fomor variants
elsewhere in the world (chocobo_fomor_transition cousin).

Public surface
--------------
    WreckCause enum     PIRATE_BOARD / SIREN_DIVERT /
                        SIREN_SHIPWRECK / STORM / UNKNOWN
    WreckState enum     FRESH / PICKED_OVER / STRIPPED
    WreckRecord dataclass
    SalvageResult dataclass
    MissingShipRegistry
        .file_loss(ship_id, zone_id, cause, crew_lost,
                   cargo_value, now_seconds)
        .open_wrecks(zone_id)
        .salvage(ship_id, diver_skill, now_seconds)
        .resolve_crew_fate(ship_id) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WreckCause(str, enum.Enum):
    PIRATE_BOARD = "pirate_board"
    SIREN_DIVERT = "siren_divert"
    SIREN_SHIPWRECK = "siren_shipwreck"
    STORM = "storm"
    UNKNOWN = "unknown"


class WreckState(str, enum.Enum):
    FRESH = "fresh"
    PICKED_OVER = "picked_over"
    STRIPPED = "stripped"


@dataclasses.dataclass
class WreckRecord:
    ship_id: str
    zone_id: str
    cause: WreckCause
    crew_lost: int
    cargo_remaining: int
    state: WreckState
    filed_at: int
    last_salvaged_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class SalvageResult:
    accepted: bool
    ship_id: str
    cargo_recovered: int = 0
    new_state: WreckState = WreckState.FRESH
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MissingShipRegistry:
    _wrecks: dict[str, WreckRecord] = dataclasses.field(default_factory=dict)
    # crew_fate keyed on ship_id; values describe each crew member outcome
    _crew_fate: dict[str, tuple[str, ...]] = dataclasses.field(
        default_factory=dict,
    )

    def file_loss(
        self, *, ship_id: str,
        zone_id: str,
        cause: WreckCause,
        crew_lost: int,
        cargo_value: int,
        now_seconds: int,
    ) -> bool:
        if not ship_id or not zone_id:
            return False
        if ship_id in self._wrecks:
            return False
        if crew_lost < 0 or cargo_value < 0:
            return False
        self._wrecks[ship_id] = WreckRecord(
            ship_id=ship_id,
            zone_id=zone_id,
            cause=cause,
            crew_lost=crew_lost,
            cargo_remaining=cargo_value,
            state=WreckState.FRESH,
            filed_at=now_seconds,
        )
        # plot the crew fate at file time so resolve_crew_fate
        # is deterministic across calls
        self._crew_fate[ship_id] = self._plot_crew_fate(
            cause=cause, crew_lost=crew_lost,
        )
        return True

    @staticmethod
    def _plot_crew_fate(
        *, cause: WreckCause, crew_lost: int,
    ) -> tuple[str, ...]:
        # canonical mapping. PIRATE_BOARD => abducted, sirens =>
        # sometimes drowned-then-fomor, storm => drowned.
        if crew_lost <= 0:
            return ()
        if cause == WreckCause.PIRATE_BOARD:
            return tuple("abducted" for _ in range(crew_lost))
        if cause == WreckCause.SIREN_SHIPWRECK:
            return tuple("drowned_to_fomor" for _ in range(crew_lost))
        if cause == WreckCause.SIREN_DIVERT:
            # mixed: half abducted by pirates downstream,
            # half drowned-to-fomor
            half = crew_lost // 2
            return (
                tuple("abducted" for _ in range(half))
                + tuple(
                    "drowned_to_fomor" for _ in range(crew_lost - half)
                )
            )
        if cause == WreckCause.STORM:
            return tuple("drowned" for _ in range(crew_lost))
        return tuple("missing" for _ in range(crew_lost))

    def open_wrecks(
        self, *, zone_id: str,
    ) -> tuple[WreckRecord, ...]:
        return tuple(
            w for w in self._wrecks.values()
            if w.zone_id == zone_id
            and w.state != WreckState.STRIPPED
        )

    def total_open(self) -> int:
        return sum(
            1 for w in self._wrecks.values()
            if w.state != WreckState.STRIPPED
        )

    def salvage(
        self, *, ship_id: str,
        diver_skill: int,
        now_seconds: int,
    ) -> SalvageResult:
        wreck = self._wrecks.get(ship_id)
        if wreck is None:
            return SalvageResult(
                False, ship_id, reason="unknown wreck",
            )
        if wreck.state == WreckState.STRIPPED:
            return SalvageResult(
                False, ship_id, reason="already stripped",
            )
        if diver_skill <= 0:
            return SalvageResult(
                False, ship_id, reason="invalid skill",
            )
        # cargo recovered: skill-capped fraction of remaining
        recover = min(wreck.cargo_remaining, diver_skill)
        wreck.cargo_remaining -= recover
        wreck.last_salvaged_at = now_seconds
        if wreck.cargo_remaining <= 0:
            wreck.state = WreckState.STRIPPED
        elif wreck.state == WreckState.FRESH:
            wreck.state = WreckState.PICKED_OVER
        return SalvageResult(
            accepted=True,
            ship_id=ship_id,
            cargo_recovered=recover,
            new_state=wreck.state,
        )

    def resolve_crew_fate(
        self, *, ship_id: str,
    ) -> tuple[str, ...]:
        return self._crew_fate.get(ship_id, ())


__all__ = [
    "WreckCause", "WreckState",
    "WreckRecord", "SalvageResult",
    "MissingShipRegistry",
]
