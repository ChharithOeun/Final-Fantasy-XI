"""KO timeout XP loss — escalating penalty for being left dead.

When a player is KO'd and not revived, an internal timer starts.
The longer they sit unrevived, the bigger the XP loss percentage
applied when they finally home-point or accept rezz.

Curve (canonical-ish, escalates fast then plateaus):
    0  - 30s   :  0%   (free reset window — split-second deaths
                         don't punish)
    30 - 60s   :  2%
    1m - 2m    :  5%
    2m - 5m    : 10%
    5m - 10m   : 15%
    10m - 15m  : 20%
    15m - 30m  : 25%
    30m+       : 30%   (cap)

Encourages parties to revive promptly and discourages lazy
home-point shortcuts. Pure-function lookup, no state.

Public surface
--------------
    XP_LOSS_CAP_PCT
    GRACE_SECONDS
    xp_loss_pct_for_seconds(seconds_ko) -> int   (0-30)
    xp_loss_for_level(seconds_ko, base_xp) -> int    (absolute XP)
"""
from __future__ import annotations

import dataclasses


XP_LOSS_CAP_PCT = 30       # hard cap
GRACE_SECONDS = 30         # 0% loss inside this window


# Curve breakpoints. Each entry: (max_seconds, loss_pct) — the
# loss pct applied if the timer is at-or-below max_seconds.
_CURVE: tuple[tuple[int, int], ...] = (
    (30,    0),     # free
    (60,    2),
    (120,   5),
    (300,   10),
    (600,   15),
    (900,   20),
    (1800,  25),
    # > 30m falls through to cap
)


def xp_loss_pct_for_seconds(seconds_ko: int) -> int:
    """Look up the XP-loss percentage for a given KO duration."""
    if seconds_ko <= 0:
        return 0
    for max_secs, pct in _CURVE:
        if seconds_ko <= max_secs:
            return pct
    return XP_LOSS_CAP_PCT


def xp_loss_for_level(*, seconds_ko: int, base_xp: int) -> int:
    """Convert KO duration to absolute XP loss given the player's
    current-level XP pool."""
    if base_xp <= 0:
        return 0
    pct = xp_loss_pct_for_seconds(seconds_ko)
    return base_xp * pct // 100


@dataclasses.dataclass(frozen=True)
class KoLossPreview:
    seconds_ko: int
    loss_pct: int
    loss_xp: int
    inside_grace: bool


def preview_loss(*, seconds_ko: int, base_xp: int) -> KoLossPreview:
    pct = xp_loss_pct_for_seconds(seconds_ko)
    return KoLossPreview(
        seconds_ko=seconds_ko, loss_pct=pct,
        loss_xp=base_xp * pct // 100,
        inside_grace=seconds_ko <= GRACE_SECONDS,
    )


__all__ = [
    "XP_LOSS_CAP_PCT", "GRACE_SECONDS",
    "xp_loss_pct_for_seconds", "xp_loss_for_level",
    "KoLossPreview", "preview_loss",
]
