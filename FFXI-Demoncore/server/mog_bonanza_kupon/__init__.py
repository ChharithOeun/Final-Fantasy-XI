"""Mog Bonanza Kupon — special-event prize redemption.

Distinct from bonanza_marbles (the prediction lottery). Kupons
are stacking event currency dropped during seasonal campaigns or
special promotions; they're traded at the Mog Bonanza Moogle for
cosmetic prizes.

Each kupon is *tier-numbered*: A.M.A.N. Trove style: kupons that
look identical but have a hidden numeric tier driving prize
weights. Higher tier kupons unlock better prize wheels.

Each redemption rolls one prize from the wheel and consumes the
kupon. Prizes include cosmetic items, mannequin paints, music
boxes, dye kits, etc.

Public surface
--------------
    KuponTier enum (I-V)
    KuponPrize dataclass
    PRIZE_CATALOG (per-tier wheel)
    PlayerKuponWallet
        .grant(tier, n)
        .redeem(tier, rng_pool) -> KuponPrize
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import STREAM_LOOT_DROPS, RngPool


class KuponTier(str, enum.Enum):
    I = "tier_1"
    II = "tier_2"
    III = "tier_3"
    IV = "tier_4"
    V = "tier_5"


@dataclasses.dataclass(frozen=True)
class KuponPrize:
    prize_id: str
    label: str
    rarity_weight: int          # higher = more common in wheel


# Per-tier prize wheel. Tier I gives the smallest prizes; Tier V
# gives capstone collector items.
_PRIZE_WHEEL: dict[KuponTier, tuple[KuponPrize, ...]] = {
    KuponTier.I: (
        KuponPrize("dye_white_basic", "White Dye (basic)", 60),
        KuponPrize("music_box_chocobo",
                    "Chocobo Music Box", 30),
        KuponPrize("mog_garden_seedling",
                    "Mog Garden Seedling", 10),
    ),
    KuponTier.II: (
        KuponPrize("dye_red_basic", "Red Dye (basic)", 50),
        KuponPrize("music_box_bastok",
                    "Bastok Theme Music Box", 30),
        KuponPrize("mannequin_paint_kit_basic",
                    "Mannequin Paint Kit (basic)", 20),
    ),
    KuponTier.III: (
        KuponPrize("dye_purple_premium", "Purple Dye (premium)", 40),
        KuponPrize("music_box_windurst",
                    "Windurst Theme Music Box", 35),
        KuponPrize("mannequin_paint_kit_advanced",
                    "Mannequin Paint Kit (advanced)", 20),
        KuponPrize("seasonal_emote_unlock",
                    "Seasonal Emote Unlock", 5),
    ),
    KuponTier.IV: (
        KuponPrize("dye_gold_premium", "Gold Dye (premium)", 30),
        KuponPrize("music_box_jeuno",
                    "Jeuno Theme Music Box", 25),
        KuponPrize("mannequin_legendary_pose",
                    "Mannequin Legendary Pose", 30),
        KuponPrize("seasonal_emote_unlock",
                    "Seasonal Emote Unlock", 10),
        KuponPrize("title_event_attendant",
                    "Title: Event Attendant", 5),
    ),
    KuponTier.V: (
        KuponPrize("dye_eternal_radiance",
                    "Dye: Eternal Radiance", 25),
        KuponPrize("music_box_capstone",
                    "Vana'diel Capstone Music Box", 20),
        KuponPrize("mannequin_signature_pose",
                    "Mannequin Signature Pose", 25),
        KuponPrize("title_collector_supreme",
                    "Title: Collector Supreme", 15),
        KuponPrize("ancient_chocobo_egg_voucher",
                    "Ancient Chocobo Egg Voucher", 10),
        KuponPrize("first_of_vanadiel_pose",
                    "First-of-Vana'diel Pose", 5),
    ),
}


def prize_wheel(tier: KuponTier) -> tuple[KuponPrize, ...]:
    return _PRIZE_WHEEL[tier]


def _weighted_pick(
    *, prizes: tuple[KuponPrize, ...], rng_pool: RngPool,
) -> KuponPrize:
    total = sum(p.rarity_weight for p in prizes)
    rng = rng_pool.stream(STREAM_LOOT_DROPS)
    pick = rng.random() * total
    accumulator = 0.0
    for p in prizes:
        accumulator += p.rarity_weight
        if pick < accumulator:
            return p
    return prizes[-1]   # fallback (rounding)


@dataclasses.dataclass(frozen=True)
class RedeemResult:
    accepted: bool
    prize: t.Optional[KuponPrize] = None
    tier: t.Optional[KuponTier] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerKuponWallet:
    player_id: str
    holdings: dict[KuponTier, int] = dataclasses.field(
        default_factory=dict,
    )

    def count(self, tier: KuponTier) -> int:
        return self.holdings.get(tier, 0)

    def grant(self, *, tier: KuponTier, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        self.holdings[tier] = self.holdings.get(tier, 0) + quantity
        return True

    def redeem(
        self, *, tier: KuponTier, rng_pool: RngPool,
    ) -> RedeemResult:
        held = self.holdings.get(tier, 0)
        if held <= 0:
            return RedeemResult(False, reason="no kupons of this tier")
        prize = _weighted_pick(
            prizes=prize_wheel(tier), rng_pool=rng_pool,
        )
        self.holdings[tier] = held - 1
        return RedeemResult(accepted=True, prize=prize, tier=tier)


__all__ = [
    "KuponTier", "KuponPrize",
    "prize_wheel", "RedeemResult",
    "PlayerKuponWallet",
]
