"""TP system — tactical points generation + decay rules.

TP starts at 0, caps at 3000. Each successful melee hit grants TP
based on weapon delay (slower weapons gain more per hit). Store TP
gear bumps the gain. Zoning resets TP to 0 (configurable). Healing
in retail does NOT reset TP, but in some setups party share applies.

Public surface
--------------
    TPState dataclass
        .gain_from_hit(weapon_delay)
        .consume(amount) -> remaining
        .zone_out()
"""
from __future__ import annotations

import dataclasses


# Cap per FFXI canon
TP_MIN = 0
TP_MAX = 3000


# Base TP gain formula approximation: TP per hit = 5.75 + delay*0.066
# Caps around 18 TP per hit at delay 240, 36 at delay 480.
def base_tp_per_hit(*, weapon_delay: int) -> int:
    if weapon_delay <= 0:
        raise ValueError("weapon_delay must be > 0")
    raw = 5.75 + (weapon_delay * 0.066)
    return int(raw * 10)         # FFXI displays TP at 100 = 1%


def store_tp_modifier(
    *, base_gain: int, store_tp_pct: int,
) -> int:
    """Apply Store TP percentage to a base gain. Caps at 100% extra."""
    pct = max(0, min(100, store_tp_pct))
    return int(base_gain * (1.0 + pct / 100.0))


@dataclasses.dataclass
class TPState:
    actor_id: str
    tp: int = 0
    store_tp_pct: int = 0

    def gain_from_hit(
        self, *, weapon_delay: int,
    ) -> int:
        """Apply TP gain from one hit. Returns new TP."""
        base = base_tp_per_hit(weapon_delay=weapon_delay)
        gain = store_tp_modifier(
            base_gain=base, store_tp_pct=self.store_tp_pct,
        )
        self.tp = min(TP_MAX, self.tp + gain)
        return self.tp

    def take_damage_tp_gain(self, *, raw_damage: int) -> int:
        """Take damage; gain a small TP bump (1/4 normal)."""
        if raw_damage <= 0:
            return self.tp
        gain = max(1, raw_damage // 100)
        self.tp = min(TP_MAX, self.tp + gain)
        return self.tp

    def consume(self, *, amount: int) -> int:
        """Spend TP. Returns remaining; rejects if insufficient."""
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if self.tp < amount:
            return self.tp
        self.tp -= amount
        return self.tp

    def consume_all(self) -> int:
        """Spend all TP (e.g. on a weapon skill)."""
        consumed = self.tp
        self.tp = 0
        return consumed

    def zone_out(self) -> None:
        """Crossing zones resets TP to 0 in retail."""
        self.tp = 0

    @property
    def has_full_tp(self) -> bool:
        return self.tp >= TP_MAX

    @property
    def can_weapon_skill(self) -> bool:
        return self.tp >= 1000


__all__ = [
    "TP_MIN", "TP_MAX",
    "base_tp_per_hit", "store_tp_modifier",
    "TPState",
]
