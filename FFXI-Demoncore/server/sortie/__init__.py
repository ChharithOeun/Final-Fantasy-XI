"""Sortie — Adoulin endgame instance.

Entry-gated by Inspector Gilles in Western Adoulin. Two
60-minute sub-instances per Vana'diel day, with three
currency drops:

* WILTZITE — primary, traded for Su5 augment slips
* FAULPIE — secondary, traded for cosmetic / glamour pieces
* MULCIBAR — rare, traded for Aminon-tier weapons

Layout: 6 themed chambers + 2 boss chambers (Aminon, Spectral
Sandworm). Drops gate behind kill-on-floor objectives.

Public surface
--------------
    SortieFloor enum (8 floors)
    SortieBoss enum
    SortieEntry dataclass
    PlayerSortieProgress (per-day, resets each Vana'diel day)
        .can_enter(today) -> bool
        .award_currency(...) / .spend_*
        .floor_complete(floor)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


SORTIES_PER_VANA_DAY = 3
SORTIE_TIMER_SECONDS = 60 * 60       # 1 hour each


class SortieFloor(str, enum.Enum):
    F1_GLITTERWHEEL = "f1_glitterwheel"
    F2_HEXBLADE = "f2_hexblade"
    F3_PRISMARIA = "f3_prismaria"
    F4_AURUMVALE = "f4_aurumvale"
    F5_ROOK_HOLLOW = "f5_rook_hollow"
    F6_LANTERN_GROVE = "f6_lantern_grove"
    BOSS_AMINON = "boss_aminon"
    BOSS_SANDWORM = "boss_sandworm"


@dataclasses.dataclass(frozen=True)
class FloorEntry:
    floor: SortieFloor
    label: str
    is_boss: bool
    wiltzite_award: int
    faulpie_award: int
    mulcibar_award: int


# Drop weights: regular floors give Wiltzite + Faulpie; bosses
# give bigger Wiltzite + a chance at Mulcibar.
SORTIE_FLOORS: tuple[FloorEntry, ...] = (
    FloorEntry(SortieFloor.F1_GLITTERWHEEL, "Glitterwheel Hall",
                False, wiltzite_award=200, faulpie_award=50,
                mulcibar_award=0),
    FloorEntry(SortieFloor.F2_HEXBLADE, "Hexblade Hollow",
                False, wiltzite_award=200, faulpie_award=50,
                mulcibar_award=0),
    FloorEntry(SortieFloor.F3_PRISMARIA, "Prismaria Vault",
                False, wiltzite_award=300, faulpie_award=80,
                mulcibar_award=0),
    FloorEntry(SortieFloor.F4_AURUMVALE, "Aurumvale Antechamber",
                False, wiltzite_award=300, faulpie_award=80,
                mulcibar_award=0),
    FloorEntry(SortieFloor.F5_ROOK_HOLLOW, "Rook Hollow",
                False, wiltzite_award=400, faulpie_award=120,
                mulcibar_award=0),
    FloorEntry(SortieFloor.F6_LANTERN_GROVE, "Lantern Grove",
                False, wiltzite_award=400, faulpie_award=120,
                mulcibar_award=0),
    FloorEntry(SortieFloor.BOSS_AMINON, "Aminon's Sanctum",
                True, wiltzite_award=1500, faulpie_award=400,
                mulcibar_award=1),
    FloorEntry(SortieFloor.BOSS_SANDWORM, "Spectral Sandworm Pit",
                True, wiltzite_award=1500, faulpie_award=400,
                mulcibar_award=1),
)


FLOOR_BY_ID: dict[SortieFloor, FloorEntry] = {
    e.floor: e for e in SORTIE_FLOORS
}


def floor_entry(floor: SortieFloor) -> t.Optional[FloorEntry]:
    return FLOOR_BY_ID.get(floor)


@dataclasses.dataclass
class PlayerSortieProgress:
    """Per-Vana'diel-day Sortie state. Resets when last_run_day
    differs from current day."""
    player_id: str
    last_run_day: int = -1
    runs_today: int = 0
    wiltzite: int = 0
    faulpie: int = 0
    mulcibar: int = 0
    floors_cleared_today: list[SortieFloor] = dataclasses.field(
        default_factory=list,
    )

    def can_enter(self, *, current_vana_day: int) -> bool:
        if self.last_run_day != current_vana_day:
            return True   # rolled over to fresh day
        return self.runs_today < SORTIES_PER_VANA_DAY

    def begin_run(self, *, current_vana_day: int) -> bool:
        if self.last_run_day != current_vana_day:
            # Day rolled — reset
            self.last_run_day = current_vana_day
            self.runs_today = 0
            self.floors_cleared_today.clear()
        if self.runs_today >= SORTIES_PER_VANA_DAY:
            return False
        self.runs_today += 1
        return True

    def floor_complete(self, *, floor: SortieFloor) -> bool:
        entry = FLOOR_BY_ID.get(floor)
        if entry is None:
            return False
        if floor in self.floors_cleared_today:
            return False  # one currency-payout per floor per run
        self.floors_cleared_today.append(floor)
        self.wiltzite += entry.wiltzite_award
        self.faulpie += entry.faulpie_award
        self.mulcibar += entry.mulcibar_award
        return True

    def spend_wiltzite(self, *, amount: int) -> bool:
        if amount <= 0 or self.wiltzite < amount:
            return False
        self.wiltzite -= amount
        return True

    def spend_faulpie(self, *, amount: int) -> bool:
        if amount <= 0 or self.faulpie < amount:
            return False
        self.faulpie -= amount
        return True

    def spend_mulcibar(self, *, amount: int) -> bool:
        if amount <= 0 or self.mulcibar < amount:
            return False
        self.mulcibar -= amount
        return True


__all__ = [
    "SORTIES_PER_VANA_DAY", "SORTIE_TIMER_SECONDS",
    "SortieFloor", "FloorEntry",
    "SORTIE_FLOORS", "FLOOR_BY_ID", "floor_entry",
    "PlayerSortieProgress",
]
