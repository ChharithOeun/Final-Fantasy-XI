"""Grounds of Valor — indoor/dungeon training tomes.

Companion system to field_of_valor (which sits in outdoor zones).
GoV tomes live at dungeon entrances and offer regimen pages
keyed to the dungeon's mob roster. Pages give a target list +
time limit + tab/cruor reward bundle.

Tomes vs FoV manuals — key differences:
* GoV regimens are PER-DUNGEON (FoV is per-zone)
* GoV pages reward Tabs AND Cruor (FoV: Tabs only)
* GoV has a "page select" so you can tune to your party's level
* Daily-once bonus first regimen, then 50% on repeats

Public surface
--------------
    GroundsTome enum (sample dungeons)
    RegimenPage dataclass
    PAGE_CATALOG / pages_for(tome)
    PlayerGroundsLog
        .start_page(tome, page_id, now) -> bool
        .record_kill(mob_id, count) -> None
        .complete_page() -> ClaimResult
        .claim_daily_bonus(now) / .has_claimed_daily_bonus_today
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


VANA_DAY_SECONDS = 24 * 60 * 60       # for daily bonus reset


class GroundsTome(str, enum.Enum):
    KING_RANPERRES_TOMB = "king_ranperres_tomb"
    GUSGEN_MINES = "gusgen_mines"
    GARLAIGE_CITADEL = "garlaige_citadel"
    CRAWLERS_NEST = "crawlers_nest"
    CASTLE_OZTROJA = "castle_oztroja"


@dataclasses.dataclass(frozen=True)
class RegimenPage:
    page_id: str
    tome: GroundsTome
    label: str
    target_kills: tuple[tuple[str, int], ...]   # (mob_id, count)
    timer_seconds: int
    tabs_reward: int
    cruor_reward: int


# Sample regimens — 2 pages per tome × 5 tomes = 10
def _p(tome: GroundsTome, idx: int, label: str,
        kills: tuple[tuple[str, int], ...], tabs: int, cruor: int,
        timer: int = 30 * 60) -> RegimenPage:
    return RegimenPage(
        page_id=f"{tome.value}_page_{idx}",
        tome=tome, label=label,
        target_kills=kills, timer_seconds=timer,
        tabs_reward=tabs, cruor_reward=cruor,
    )


PAGE_CATALOG: tuple[RegimenPage, ...] = (
    _p(GroundsTome.KING_RANPERRES_TOMB, 1,
        "Tomb Crawl: Skeleton Sweep",
        kills=(("skeleton_warrior", 5), ("ghoul", 3)),
        tabs=15, cruor=200),
    _p(GroundsTome.KING_RANPERRES_TOMB, 2,
        "Royal Resting Place",
        kills=(("ghost", 5), ("hover_tomb_crystal", 1)),
        tabs=25, cruor=400),
    _p(GroundsTome.GUSGEN_MINES, 1,
        "Mine Cleanup",
        kills=(("goblin_pickpocket", 6), ("hellbat", 4)),
        tabs=15, cruor=200),
    _p(GroundsTome.GUSGEN_MINES, 2,
        "Deep Dark Passage",
        kills=(("ghost_lantern", 3), ("magic_pot", 1)),
        tabs=25, cruor=400),
    _p(GroundsTome.GARLAIGE_CITADEL, 1,
        "Citadel Defenders",
        kills=(("imp", 4), ("antican_lieutenant", 4)),
        tabs=20, cruor=300),
    _p(GroundsTome.GARLAIGE_CITADEL, 2,
        "Steam Fissure Foray",
        kills=(("steam_cleaner", 3), ("hellbat_doctor", 2)),
        tabs=30, cruor=500),
    _p(GroundsTome.CRAWLERS_NEST, 1,
        "Nest Pruning",
        kills=(("crawler", 6), ("attercop", 4)),
        tabs=20, cruor=300),
    _p(GroundsTome.CRAWLERS_NEST, 2,
        "Hive Heart",
        kills=(("queen_crawler", 1), ("doom_caterpillar", 3)),
        tabs=35, cruor=550),
    _p(GroundsTome.CASTLE_OZTROJA, 1,
        "Yagudo Patrols",
        kills=(("yagudo_initiate", 5), ("yagudo_acolyte", 5)),
        tabs=25, cruor=400),
    _p(GroundsTome.CASTLE_OZTROJA, 2,
        "Jail Block Subjugation",
        kills=(("yagudo_priest", 3), ("yagudo_assassin", 2)),
        tabs=40, cruor=600),
)


PAGE_BY_ID: dict[str, RegimenPage] = {p.page_id: p for p in PAGE_CATALOG}


def pages_for(tome: GroundsTome) -> tuple[RegimenPage, ...]:
    return tuple(p for p in PAGE_CATALOG if p.tome == tome)


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    tabs_awarded: int = 0
    cruor_awarded: int = 0
    daily_bonus_applied: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerGroundsLog:
    player_id: str
    active_page: t.Optional[RegimenPage] = None
    started_at_seconds: float = 0.0
    kill_progress: dict[str, int] = dataclasses.field(default_factory=dict)
    last_daily_bonus_at_seconds: float = -1.0

    def start_page(
        self, *, page_id: str, now_seconds: float,
    ) -> bool:
        page = PAGE_BY_ID.get(page_id)
        if page is None:
            return False
        if self.active_page is not None:
            return False
        self.active_page = page
        self.started_at_seconds = now_seconds
        self.kill_progress.clear()
        return True

    def record_kill(self, *, mob_id: str, count: int = 1) -> bool:
        if self.active_page is None or count <= 0:
            return False
        self.kill_progress[mob_id] = (
            self.kill_progress.get(mob_id, 0) + count
        )
        return True

    def page_complete(self) -> bool:
        if self.active_page is None:
            return False
        for mob_id, target in self.active_page.target_kills:
            if self.kill_progress.get(mob_id, 0) < target:
                return False
        return True

    def has_claimed_daily_bonus_today(
        self, *, now_seconds: float,
    ) -> bool:
        if self.last_daily_bonus_at_seconds < 0:
            return False
        return (
            now_seconds - self.last_daily_bonus_at_seconds
        ) < VANA_DAY_SECONDS

    def complete_page(
        self, *, now_seconds: float,
    ) -> ClaimResult:
        if self.active_page is None:
            return ClaimResult(False, reason="no active page")
        if not self.page_complete():
            return ClaimResult(False, reason="page targets not met")
        page = self.active_page
        elapsed = now_seconds - self.started_at_seconds
        if elapsed > page.timer_seconds:
            self.active_page = None
            self.kill_progress.clear()
            return ClaimResult(False, reason="page timed out")
        # Apply daily bonus if available
        bonus = not self.has_claimed_daily_bonus_today(
            now_seconds=now_seconds,
        )
        mult = 100 if bonus else 50
        tabs = page.tabs_reward * mult // 100
        cruor = page.cruor_reward * mult // 100
        if bonus:
            self.last_daily_bonus_at_seconds = now_seconds
        # Reset
        self.active_page = None
        self.kill_progress.clear()
        return ClaimResult(
            accepted=True, tabs_awarded=tabs, cruor_awarded=cruor,
            daily_bonus_applied=bonus,
        )


__all__ = [
    "VANA_DAY_SECONDS",
    "GroundsTome", "RegimenPage", "ClaimResult",
    "PAGE_CATALOG", "PAGE_BY_ID",
    "pages_for", "PlayerGroundsLog",
]
