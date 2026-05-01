"""XP chain — combat XP bonus engine.

Why this module exists
----------------------
FFXI's classic XP chain mechanic: kill a mob within the chain
window after the previous kill, the chain count increments, and
the bonus multiplier ramps up — then plateaus, then decays. This
is the pulse of the post-combat numbers and one of the things
players keep coming back for: a clean chain 5 in a tight party
generates that exhilarating XP fountain.

Demoncore extends classic FFXI in a few small ways:
  - chain windows scale gently with party size (a full alliance
    fight wraps up a kill faster, so the window is shorter)
  - level-sync caps still apply: a level-30 sync target reduces
    XP to the synced cap, not the killer's natural level
  - Empress Band / Dedication Ring buffs stack additively with
    chain — they're separate mechanics, not folded in

Public surface
--------------
    chain_bonus_multiplier(chain_count) -> float
    is_chain_alive(*, last_kill_tick, now_tick, party_size) -> bool
    next_chain_count(*, prev_chain, last_kill_tick, now_tick,
                     party_size) -> int
    LevelSync                     dataclass for sync caps
    XpBuff                        Empress / Dedication / etc.
    XpAward                       computed reward for one kill
    compute_xp_award(...)         the main composition entry point
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# -- chain bonus tiers ------------------------------------------------

# (count_lower, multiplier). Count >= count_lower -> use that mult.
# Sorted descending; first match wins.
_CHAIN_BONUS_TABLE: tuple[tuple[int, float], ...] = (
    (5, 1.75),
    (4, 1.60),
    (3, 1.40),
    (2, 1.20),
    (1, 1.00),
    (0, 1.00),
)


def chain_bonus_multiplier(chain_count: int) -> float:
    """Return the XP multiplier for a given chain count.

    Chain 0 / 1 = 1.00x baseline. Chain 5+ caps at 1.75x.
    """
    if chain_count < 0:
        raise ValueError(f"chain_count {chain_count} must be >= 0")
    for floor_count, mult in _CHAIN_BONUS_TABLE:
        if chain_count >= floor_count:
            return mult
    return 1.00


def chain_window_seconds(*, party_size: int) -> int:
    """How long the chain window stays open after a kill.

    Solo: 60s. Party of 6: 30s. Alliance (>6): 20s. The numbers
    aren't retail-precise — they're a representative ramp where
    bigger groups have shorter windows because they kill faster
    and need less time to set up the next pull."""
    if party_size <= 1:
        return 60
    if party_size <= 6:
        return 30
    return 20


def is_chain_alive(
    *,
    last_kill_tick: int,
    now_tick: int,
    party_size: int,
) -> bool:
    """Is the chain still alive?

    A chain is alive if the time since the last kill is less than
    the chain window.
    """
    if last_kill_tick is None:
        return False
    elapsed = now_tick - last_kill_tick
    return 0 <= elapsed < chain_window_seconds(party_size=party_size)


def next_chain_count(
    *,
    prev_chain: int,
    last_kill_tick: t.Optional[int],
    now_tick: int,
    party_size: int,
) -> int:
    """Compute the new chain count after a fresh kill.

    If the chain is alive (within window), increment. Otherwise
    reset to 1 (the new kill itself starts a fresh chain).
    """
    if last_kill_tick is None:
        return 1
    if is_chain_alive(
        last_kill_tick=last_kill_tick,
        now_tick=now_tick,
        party_size=party_size,
    ):
        return prev_chain + 1
    return 1


# -- level sync -------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class LevelSync:
    """An active level-sync state for one player.

    `cap_level` is the synced level. `natural_level` is the player's
    real level. XP earned synced is capped against the synced cap,
    not the natural level — this is how retail FFXI prevented power-
    leveling exploits.
    """
    cap_level: int
    natural_level: int

    def is_active(self) -> bool:
        return self.cap_level < self.natural_level


# -- XP buffs ---------------------------------------------------------

class BuffSource(str, enum.Enum):
    """Origin of a non-chain XP buff. The set of canonical FFXI
    XP buffs that stack with chain."""
    EMPRESS_BAND = "empress_band"          # +50% XP, charged item
    DEDICATION_RING = "dedication_ring"    # +50% XP, banked uses
    ANNIVERSARY_RING = "anniversary_ring"  # +50% XP, retail anniversary
    PROMOTION_BUFF = "promotion_buff"      # server-promoted bonus
    NATION_PROMO = "nation_promo"          # nation conquest bonus


@dataclasses.dataclass(frozen=True)
class XpBuff:
    source: BuffSource
    bonus_pct: float                       # 0.5 means +50%

    def __post_init__(self) -> None:
        if self.bonus_pct < 0:
            raise ValueError("bonus_pct must be >= 0")


def buffs_total_multiplier(buffs: t.Sequence[XpBuff]) -> float:
    """Stack XP buffs ADDITIVELY (FFXI canonical behavior).

    Two +50% buffs -> +100% total = 2.0x, not 2.25x.
    Empty input returns 1.0.
    """
    return 1.0 + sum(b.bonus_pct for b in buffs)


# -- compute_xp_award (the main composition entry) --------------------

@dataclasses.dataclass(frozen=True)
class XpAward:
    base_xp: int                           # natural mob XP, pre-modifiers
    chain_count: int
    chain_multiplier: float
    party_share_divisor: int
    sync_capped: bool
    buffs_total: float
    final_xp: int                          # what actually credits

    @property
    def chain_was_extended(self) -> bool:
        return self.chain_count >= 2


def compute_xp_award(
    *,
    base_xp: int,
    prev_chain: int,
    last_kill_tick: t.Optional[int],
    now_tick: int,
    party_size: int = 1,
    sync: t.Optional[LevelSync] = None,
    sync_cap_xp: t.Optional[int] = None,
    buffs: t.Sequence[XpBuff] = (),
) -> XpAward:
    """Compute the XP credit for one player on one mob kill.

    Order of operations (matches retail FFXI as best as we can):
      1. base_xp
      2. apply level-sync cap (if active and sync_cap_xp provided)
      3. divide by party_size for share
      4. multiply by chain bonus
      5. multiply by additive buff total
    """
    if base_xp < 0:
        raise ValueError("base_xp must be non-negative")
    if party_size < 1:
        raise ValueError("party_size must be >= 1")

    chain_count = next_chain_count(
        prev_chain=prev_chain,
        last_kill_tick=last_kill_tick,
        now_tick=now_tick,
        party_size=party_size,
    )
    chain_mult = chain_bonus_multiplier(chain_count)

    sync_capped = False
    capped_xp = base_xp
    if sync is not None and sync.is_active() and \
            sync_cap_xp is not None:
        if base_xp > sync_cap_xp:
            capped_xp = sync_cap_xp
            sync_capped = True

    share = capped_xp / party_size
    chained = share * chain_mult
    buff_mult = buffs_total_multiplier(buffs)
    final = int(round(chained * buff_mult))

    return XpAward(
        base_xp=base_xp,
        chain_count=chain_count,
        chain_multiplier=chain_mult,
        party_share_divisor=party_size,
        sync_capped=sync_capped,
        buffs_total=buff_mult,
        final_xp=final,
    )


__all__ = [
    "chain_bonus_multiplier",
    "chain_window_seconds",
    "is_chain_alive",
    "next_chain_count",
    "LevelSync",
    "BuffSource",
    "XpBuff",
    "buffs_total_multiplier",
    "XpAward",
    "compute_xp_award",
]
