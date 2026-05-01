"""Field of Valor — training pages, regimens, and tally rewards.

A FoV book in each zone offers training pages: kill N members of a
specific mob family within the page's window for a XP+gil+tabs reward.
Pages are repeatable; players are capped at a daily regimen tally to
prevent infinite grinding.

Public surface
--------------
    FoVPage immutable spec
    FOV_CATALOG sample pages
    PlayerFoVTracker per-player active page + daily tally
        .start_page(page_id, now_tick)
        .record_kill(family_id) -> bool (advances active page)
        .claim_completed(now_tick) -> ClaimResult
        .daily_reset()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Daily cap on regimen completions. Match retail FFXI's "20 regimens
# per RL day" without the time-of-day mechanics.
DAILY_TALLY_CAP = 20


class FoVTier(str, enum.Enum):
    NEWBIE = "newbie"
    MID = "mid"
    HIGH = "high"


@dataclasses.dataclass(frozen=True)
class FoVPage:
    page_id: str
    label: str
    zone_id: str
    target_family: str
    target_count: int
    tier: FoVTier
    xp_reward: int
    gil_reward: int
    tabs_reward: int = 100        # FoV tabs currency


# Sample catalog
FOV_CATALOG: tuple[FoVPage, ...] = (
    FoVPage("south_gusta_1", "South Gustaberg, Page 1",
            zone_id="south_gustaberg", target_family="bee",
            target_count=3, tier=FoVTier.NEWBIE,
            xp_reward=300, gil_reward=300, tabs_reward=80),
    FoVPage("south_gusta_2", "South Gustaberg, Page 2",
            zone_id="south_gustaberg", target_family="orc",
            target_count=3, tier=FoVTier.NEWBIE,
            xp_reward=400, gil_reward=400, tabs_reward=80),
    FoVPage("east_ronfaure_1", "East Ronfaure, Page 1",
            zone_id="east_ronfaure", target_family="goblin",
            target_count=3, tier=FoVTier.NEWBIE,
            xp_reward=300, gil_reward=300, tabs_reward=80),
    FoVPage("crawlers_nest_1", "Crawlers' Nest, Page 1",
            zone_id="crawlers_nest", target_family="bug",
            target_count=5, tier=FoVTier.MID,
            xp_reward=900, gil_reward=600, tabs_reward=120),
    FoVPage("beadeaux_1", "Beadeaux, Page 1",
            zone_id="beadeaux", target_family="quadav",
            target_count=5, tier=FoVTier.HIGH,
            xp_reward=1500, gil_reward=900, tabs_reward=160),
)

PAGE_BY_ID: dict[str, FoVPage] = {p.page_id: p for p in FOV_CATALOG}


def pages_in_zone(zone_id: str) -> tuple[FoVPage, ...]:
    return tuple(p for p in FOV_CATALOG if p.zone_id == zone_id)


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    page_id: str
    xp_awarded: int = 0
    gil_awarded: int = 0
    tabs_awarded: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _ActivePage:
    page_id: str
    started_tick: int
    progress: int = 0
    completed_at_tick: t.Optional[int] = None


@dataclasses.dataclass
class PlayerFoVTracker:
    player_id: str
    daily_completions: int = 0
    total_tabs: int = 0
    _active: t.Optional[_ActivePage] = None

    def start_page(self, *, page_id: str, now_tick: int) -> bool:
        if self._active is not None and \
                self._active.completed_at_tick is None:
            return False     # already running
        if page_id not in PAGE_BY_ID:
            return False
        if self.daily_completions >= DAILY_TALLY_CAP:
            return False
        self._active = _ActivePage(
            page_id=page_id, started_tick=now_tick,
        )
        return True

    @property
    def active_page_id(self) -> t.Optional[str]:
        if self._active is None or \
                self._active.completed_at_tick is not None:
            return None
        return self._active.page_id

    def record_kill(self, *, family: str) -> bool:
        """A kill matching the active page's target family advances
        progress. Returns True if progress incremented."""
        if self._active is None or \
                self._active.completed_at_tick is not None:
            return False
        page = PAGE_BY_ID[self._active.page_id]
        if page.target_family != family:
            return False
        if self._active.progress >= page.target_count:
            return False     # already at cap
        self._active.progress += 1
        return True

    def is_ready(self) -> bool:
        if self._active is None or \
                self._active.completed_at_tick is not None:
            return False
        page = PAGE_BY_ID[self._active.page_id]
        return self._active.progress >= page.target_count

    def claim_completed(self, *, now_tick: int) -> ClaimResult:
        if self._active is None:
            return ClaimResult(False, "", reason="no active page")
        if not self.is_ready():
            return ClaimResult(
                False, self._active.page_id, reason="not ready",
            )
        page = PAGE_BY_ID[self._active.page_id]
        self._active.completed_at_tick = now_tick
        self.daily_completions += 1
        self.total_tabs += page.tabs_reward
        result = ClaimResult(
            accepted=True, page_id=page.page_id,
            xp_awarded=page.xp_reward,
            gil_awarded=page.gil_reward,
            tabs_awarded=page.tabs_reward,
        )
        # Clear active so a new page can be started.
        self._active = None
        return result

    def daily_reset(self) -> None:
        self.daily_completions = 0


__all__ = [
    "DAILY_TALLY_CAP",
    "FoVTier", "FoVPage",
    "FOV_CATALOG", "PAGE_BY_ID",
    "pages_in_zone",
    "ClaimResult", "PlayerFoVTracker",
]
