"""Spice rack — modify a meal's outcome with seasonings.

A pinch of chili in the stew turns a flat str+3 dish
into something with bite — a little fire resistance, a
little less duration. Spices are the reason two players
making the same Hunter's Stew end up with different buffs.

Each spice has a SpiceEffect describing what it adds or
multiplies on the BuffPayload. Players add 0..N spices
to a recipe before cooking. Each spice consumes 1
"spice slot" and a meal allows up to 3 slots. Stacking
the same spice diminishes — chili once gives +10 fire
resist, twice gives +15 (not +20), thrice gives +18.

Spice profiles
--------------
    CHILI       +heat_resist, -duration
    GINGER      +cold_resist, +str
    SALT        +duration_pct (preservation)
    HONEY       +regen, sweetens (no penalty)
    GARLIC      +str, smell penalty (no game effect — flavor)
    BLACK_PEPPER +dex, +heat_resist (mild)
    THYME       +mp_max_pct, +refresh
    SAFFRON     rare; +all stats slightly

Public surface
--------------
    SpiceKind enum
    SpiceEffect dataclass (frozen)
    SpiceRack
        .add_to_dish(dish_token, spice, count) -> bool
        .clear(dish_token) -> int
        .apply(payload, dish_token) -> BuffPayload
        .spices_on(dish_token) -> dict[SpiceKind, int]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload


class SpiceKind(str, enum.Enum):
    CHILI = "chili"
    GINGER = "ginger"
    SALT = "salt"
    HONEY = "honey"
    GARLIC = "garlic"
    BLACK_PEPPER = "black_pepper"
    THYME = "thyme"
    SAFFRON = "saffron"


_MAX_SPICE_SLOTS = 3


# Diminishing-returns multipliers when stacking the same
# spice. 1st pinch = 1.0x, 2nd = 0.5x, 3rd = 0.3x.
_STACK_FACTORS = (0.0, 1.0, 1.5, 1.8)


@dataclasses.dataclass(frozen=True)
class SpiceEffect:
    """Adjustments a single pinch makes to a payload."""
    str_add: int = 0
    dex_add: int = 0
    vit_add: int = 0
    regen_add: int = 0
    refresh_add: int = 0
    mp_max_pct_add: int = 0
    cold_resist_add: int = 0
    heat_resist_add: int = 0
    duration_seconds_add: int = 0
    duration_seconds_mult_pct: int = 100   # 100 = no change


_SPICE_EFFECTS: dict[SpiceKind, SpiceEffect] = {
    SpiceKind.CHILI: SpiceEffect(
        heat_resist_add=10, duration_seconds_add=-300,
    ),
    SpiceKind.GINGER: SpiceEffect(
        cold_resist_add=10, str_add=1,
    ),
    SpiceKind.SALT: SpiceEffect(
        duration_seconds_mult_pct=125,
    ),
    SpiceKind.HONEY: SpiceEffect(
        regen_add=2,
    ),
    SpiceKind.GARLIC: SpiceEffect(
        str_add=2,
    ),
    SpiceKind.BLACK_PEPPER: SpiceEffect(
        dex_add=2, heat_resist_add=3,
    ),
    SpiceKind.THYME: SpiceEffect(
        refresh_add=1, mp_max_pct_add=3,
    ),
    SpiceKind.SAFFRON: SpiceEffect(
        str_add=1, dex_add=1, vit_add=1,
        cold_resist_add=3, heat_resist_add=3,
    ),
}


def _stack_factor(count: int) -> float:
    if count <= 0:
        return 0.0
    if count >= len(_STACK_FACTORS):
        return _STACK_FACTORS[-1]
    return _STACK_FACTORS[count]


@dataclasses.dataclass
class SpiceRack:
    # dish_token is an opaque string — caller picks how
    # to identify the dish-in-progress (typically a uuid).
    _on_dish: dict[str, dict[SpiceKind, int]] = \
        dataclasses.field(default_factory=dict)

    def add_to_dish(
        self, *, dish_token: str, spice: SpiceKind,
        count: int = 1,
    ) -> bool:
        if not dish_token or count <= 0:
            return False
        on_dish = self._on_dish.setdefault(dish_token, {})
        used = sum(on_dish.values())
        if used + count > _MAX_SPICE_SLOTS:
            return False
        on_dish[spice] = on_dish.get(spice, 0) + count
        return True

    def spices_on(
        self, *, dish_token: str,
    ) -> dict[SpiceKind, int]:
        return dict(self._on_dish.get(dish_token, {}))

    def clear(self, *, dish_token: str) -> int:
        if dish_token not in self._on_dish:
            return 0
        out = sum(self._on_dish[dish_token].values())
        del self._on_dish[dish_token]
        return out

    def apply(
        self, *, payload: BuffPayload, dish_token: str,
    ) -> BuffPayload:
        spices = self._on_dish.get(dish_token)
        if not spices:
            return payload
        # accumulate all spice deltas (with diminishing
        # returns per stack), then build a new payload
        d_str = d_dex = d_vit = 0
        d_regen = d_refresh = 0
        d_mp = d_cold = d_heat = 0
        d_duration_add = 0
        # use a single multiplicative pct for duration —
        # take the max of the spice-applied multipliers
        # so SALT meaningfully extends duration even if
        # CHILI is also present (chili shortens via
        # duration_add, salt extends via mult).
        duration_mult_pct = 100
        for spice, count in spices.items():
            factor = _stack_factor(count)
            eff = _SPICE_EFFECTS[spice]
            d_str += int(eff.str_add * factor)
            d_dex += int(eff.dex_add * factor)
            d_vit += int(eff.vit_add * factor)
            d_regen += int(eff.regen_add * factor)
            d_refresh += int(eff.refresh_add * factor)
            d_mp += int(eff.mp_max_pct_add * factor)
            d_cold += int(eff.cold_resist_add * factor)
            d_heat += int(eff.heat_resist_add * factor)
            d_duration_add += int(eff.duration_seconds_add * factor)
            if eff.duration_seconds_mult_pct > duration_mult_pct:
                duration_mult_pct = eff.duration_seconds_mult_pct
        new_duration = int(
            (payload.duration_seconds + d_duration_add)
            * duration_mult_pct / 100,
        )
        if new_duration < 1:
            new_duration = 1
        return BuffPayload(
            str_bonus=payload.str_bonus + d_str,
            dex_bonus=payload.dex_bonus + d_dex,
            vit_bonus=payload.vit_bonus + d_vit,
            regen_per_tick=payload.regen_per_tick + d_regen,
            refresh_per_tick=payload.refresh_per_tick + d_refresh,
            hp_max_pct=payload.hp_max_pct,
            mp_max_pct=payload.mp_max_pct + d_mp,
            cold_resist=payload.cold_resist + d_cold,
            heat_resist=payload.heat_resist + d_heat,
            duration_seconds=new_duration,
        )

    def total_dishes_in_progress(self) -> int:
        return len(self._on_dish)


__all__ = [
    "SpiceKind", "SpiceEffect", "SpiceRack",
]
