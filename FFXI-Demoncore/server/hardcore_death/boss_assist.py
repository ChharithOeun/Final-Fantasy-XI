"""Boss-fight fomor assist — call N adds when a boss aggros.

Per HARDCORE_DEATH.md:
    'When an LSB-flagged boss / NM fight starts, eligible fomors
    (level-banded, in-zone or adjacent) can be summoned as adds.
    Caps: max 6 fomors per boss fight, max 1 alliance worth at
    end-game.'
"""
from __future__ import annotations

import dataclasses
import typing as t

from .fomor_pool import FomorEntry, FomorPool, FomorState


# Doc: 'max 6 fomors per boss fight, max 1 alliance worth at end-game'.
MAX_FOMORS_PER_BOSS_FIGHT: int = 6
MAX_FOMORS_END_GAME: int = 18    # alliance = 3 parties of 6


@dataclasses.dataclass(frozen=True)
class AssistRequest:
    """LSB calls into boss_assist with this when a boss aggros."""
    boss_id: str
    boss_zone_id: str
    boss_level: int
    adjacent_zone_ids: tuple[str, ...]
    is_end_game_tier: bool


@dataclasses.dataclass(frozen=True)
class AssistResult:
    """The fomors selected to assist + the reason for any cap."""
    fomors_assigned: tuple[FomorEntry, ...]
    request: AssistRequest
    cap_used: int
    reason: str


def select_assists(*,
                       request: AssistRequest,
                       pool: FomorPool,
                       level_band_tolerance: int = 5,
                       ) -> AssistResult:
    """Pick eligible fomors per the doc rules.

    Eligibility:
        - state is ACTIVE (night-cycle and not despawned)
        - in the boss zone OR an adjacent zone
        - level within +/- level_band_tolerance of the boss
    """
    cap = (MAX_FOMORS_END_GAME if request.is_end_game_tier
              else MAX_FOMORS_PER_BOSS_FIGHT)
    valid_zones = {request.boss_zone_id, *request.adjacent_zone_ids}

    eligible: list[FomorEntry] = []
    for f in pool.all_fomors():
        if f.state != FomorState.ACTIVE:
            continue
        if f.current_zone_id not in valid_zones:
            continue
        f_level = f.snapshot.main_level
        if abs(f_level - request.boss_level) > level_band_tolerance:
            continue
        eligible.append(f)

    # Per the doc, cap is max — pick the closest-level ones first
    # so the boss fight gets the most matched difficulty.
    eligible.sort(
        key=lambda f: abs(f.snapshot.main_level - request.boss_level)
    )
    selected = tuple(eligible[:cap])

    reason = ""
    if len(eligible) > cap:
        reason = (f"capped at {cap}; "
                    f"{len(eligible) - cap} eligible fomors deferred")
    elif not selected:
        reason = "no eligible fomors found"
    else:
        reason = f"selected {len(selected)} of {len(eligible)} eligible"

    return AssistResult(
        fomors_assigned=selected,
        request=request,
        cap_used=cap,
        reason=reason,
    )
