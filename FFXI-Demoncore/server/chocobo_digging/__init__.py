"""Chocobo digging — minigame with global cooldown + fatigue.

Mount a rented chocobo, feed it Gysahl Greens, and dig at a zone.
Each dig consumes one green and rolls against a per-zone item table.
Fatigue tracks across digs; over-digging triggers a chocobo refusal
that locks the player out for a cooldown period.

Public surface
--------------
    DiggingZone catalog (zones with dig tables)
    PlayerDigState
        .feed_green() - consume green, advance fatigue
        .dig(zone_id, rng_pool) -> DigResult
        .reset_fatigue(now_tick) - call when daily reset
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


# Fatigue thresholds
FATIGUE_REFUSAL_THRESHOLD = 100   # at 100, chocobo refuses to dig
FATIGUE_LOCKOUT_SECONDS = 6 * 3600  # 6 hr lockout after refusal


@dataclasses.dataclass(frozen=True)
class DigEntry:
    item_id: str
    weight: int


@dataclasses.dataclass(frozen=True)
class DiggingZone:
    zone_id: str
    label: str
    bury_chance: float          # chance dig finds nothing
    yields: tuple[DigEntry, ...]


# Sample catalog (canonical FFXI dig zones)
DIG_ZONES: tuple[DiggingZone, ...] = (
    DiggingZone(
        zone_id="east_ronfaure", label="East Ronfaure",
        bury_chance=0.30,
        yields=(
            DigEntry("la_theine_cabbage", weight=40),
            DigEntry("popoto", weight=30),
            DigEntry("flint_stone", weight=20),
            DigEntry("ash_log", weight=8),
            DigEntry("rusty_subligar", weight=2),
        ),
    ),
    DiggingZone(
        zone_id="south_gustaberg", label="South Gustaberg",
        bury_chance=0.30,
        yields=(
            DigEntry("flint_stone", weight=40),
            DigEntry("zinc_ore", weight=25),
            DigEntry("copper_ore", weight=20),
            DigEntry("iron_ore", weight=10),
            DigEntry("gold_ore", weight=5),
        ),
    ),
    DiggingZone(
        zone_id="east_sarutabaruta", label="East Sarutabaruta",
        bury_chance=0.30,
        yields=(
            DigEntry("popoto", weight=35),
            DigEntry("saruta_orange", weight=30),
            DigEntry("flint_stone", weight=20),
            DigEntry("walnut_log", weight=10),
            DigEntry("phoenix_feather", weight=5),
        ),
    ),
    DiggingZone(
        zone_id="western_altepa_desert",
        label="Western Altepa Desert",
        bury_chance=0.40,
        yields=(
            DigEntry("flint_stone", weight=30),
            DigEntry("ancient_papyrus", weight=20),
            DigEntry("luminian_tile", weight=15),
            DigEntry("dragon_bone", weight=5),
        ),
    ),
)

ZONE_BY_ID: dict[str, DiggingZone] = {z.zone_id: z for z in DIG_ZONES}


@dataclasses.dataclass(frozen=True)
class DigResult:
    accepted: bool
    item_id: t.Optional[str] = None
    fatigue_after: int = 0
    refusal_triggered: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerDigState:
    player_id: str
    fatigue: int = 0
    refused_until_tick: int = 0
    greens_in_pouch: int = 0

    def add_greens(self, *, count: int) -> None:
        if count < 0:
            raise ValueError("count must be >= 0")
        self.greens_in_pouch += count

    def reset_fatigue(self) -> None:
        """Call on daily reset."""
        self.fatigue = 0
        self.refused_until_tick = 0

    def dig(
        self, *,
        zone_id: str,
        now_tick: int,
        rng_pool: RngPool,
        stream_name: str = STREAM_ENCOUNTER_GEN,
    ) -> DigResult:
        if now_tick < self.refused_until_tick:
            return DigResult(
                False, fatigue_after=self.fatigue,
                reason="chocobo refusing to dig",
            )
        if self.greens_in_pouch <= 0:
            return DigResult(
                False, fatigue_after=self.fatigue,
                reason="no Gysahl Greens",
            )
        zone = ZONE_BY_ID.get(zone_id)
        if zone is None:
            return DigResult(
                False, fatigue_after=self.fatigue,
                reason="unknown zone",
            )

        # Consume one green
        self.greens_in_pouch -= 1
        self.fatigue += 5

        # Refusal check
        if self.fatigue >= FATIGUE_REFUSAL_THRESHOLD:
            self.refused_until_tick = (
                now_tick + FATIGUE_LOCKOUT_SECONDS
            )
            return DigResult(
                accepted=True, item_id=None,
                fatigue_after=self.fatigue,
                refusal_triggered=True,
                reason="chocobo exhausted",
            )

        # Dig roll
        rng = rng_pool.stream(stream_name)
        if rng.random() < zone.bury_chance:
            return DigResult(
                accepted=True, item_id=None,
                fatigue_after=self.fatigue,
            )
        total = sum(y.weight for y in zone.yields)
        roll = rng.uniform(0, total)
        cum = 0.0
        chosen = zone.yields[0].item_id
        for y in zone.yields:
            cum += y.weight
            if roll <= cum:
                chosen = y.item_id
                break
        return DigResult(
            accepted=True, item_id=chosen,
            fatigue_after=self.fatigue,
        )


__all__ = [
    "FATIGUE_REFUSAL_THRESHOLD", "FATIGUE_LOCKOUT_SECONDS",
    "DigEntry", "DiggingZone",
    "DIG_ZONES", "ZONE_BY_ID",
    "DigResult", "PlayerDigState",
]
