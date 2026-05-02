"""Einherjar — WotG-era Norse-themed instance battle system.

Players exchange Ichor (currency) for chamber passes, then enter
a Therion-style instance: 3 waves of escalating Valkyrie / Thor
/ undead beastmen, capped by a boss chamber.

Drops:
* Glory of Valor / Honor / Triumph (rank tokens)
* Norse-themed armor pieces (Askar, Marduk, Goetia, Aoidos, Estoqueur)
* Ichor (some self-replenishment to fuel future runs)

Composes on instance_engine for the lifecycle. This module owns
the chambers, ichor economy, and chamber-pass logic.

Public surface
--------------
    EinherjarTier enum (I, II, III, ODIN)
    Chamber dataclass / EINHERJAR_CHAMBERS
    PlayerEinherjarBalance (ichor + chamber-pass tracker)
    chamber_for_tier(tier) -> Chamber
    pass_cost_in_ichor(tier) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EinherjarTier(str, enum.Enum):
    I = "tier_1"        # Wave 1, regular Valkyrie / Pawn classes
    II = "tier_2"       # Wave 2, mixed mid-tier
    III = "tier_3"      # Wave 3, elite + mini-boss
    ODIN = "odin"       # Capstone — Odin's chamber


@dataclasses.dataclass(frozen=True)
class Chamber:
    chamber_id: str
    tier: EinherjarTier
    label: str
    ichor_pass_cost: int
    timer_seconds: int
    party_size_min: int
    party_size_max: int
    drop_pool: tuple[str, ...]


# Sample drop pools — Norse-set armor (canonical FFXI Einherjar gear)
_ASKAR_PIECES = (
    "askar_zucchetto", "askar_korazin", "askar_manopolas",
    "askar_dirs", "askar_gambieras",
)
_MARDUK_PIECES = (
    "marduk_tiara", "marduk_jubbah", "marduk_dastanas",
    "marduk_shalwar", "marduk_crackows",
)
_GOETIA_PIECES = (
    "goetia_petasos", "goetia_chlamys", "goetia_gages",
    "goetia_chausses", "goetia_sandals",
)
_AOIDOS_PIECES = (
    "aoidos_calot", "aoidos_hongreline", "aoidos_manchettes",
    "aoidos_rhingrave", "aoidos_cothurnes",
)
_ESTOQUEUR_PIECES = (
    "estoqueur_chappel", "estoqueur_saio", "estoqueur_gantelets",
    "estoqueur_houseaux", "estoqueur_houseaux_low",
)


# Capstone glory / honor tokens
_GLORY_TOKENS = (
    "glory_token_valor", "glory_token_honor", "glory_token_triumph",
)


EINHERJAR_CHAMBERS: tuple[Chamber, ...] = (
    Chamber(
        "chamber_tier_1", EinherjarTier.I,
        "Tier I — Apprentice Valkyries",
        ichor_pass_cost=200,
        timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_ASKAR_PIECES[:2] + _MARDUK_PIECES[:2]
                   + ("ichor_x10", "ichor_x10"),
    ),
    Chamber(
        "chamber_tier_2", EinherjarTier.II,
        "Tier II — Knights of Sessrumnir",
        ichor_pass_cost=600,
        timer_seconds=30 * 60,
        party_size_min=6, party_size_max=18,
        drop_pool=_GOETIA_PIECES + _AOIDOS_PIECES[:2]
                   + ("ichor_x20",) + _GLORY_TOKENS[:1],
    ),
    Chamber(
        "chamber_tier_3", EinherjarTier.III,
        "Tier III — Champions of Aesir",
        ichor_pass_cost=1500,
        timer_seconds=30 * 60,
        party_size_min=12, party_size_max=18,
        drop_pool=_ESTOQUEUR_PIECES + _MARDUK_PIECES[2:]
                   + ("ichor_x40",) + _GLORY_TOKENS[:2],
    ),
    Chamber(
        "chamber_odin", EinherjarTier.ODIN,
        "Odin's Chamber (capstone)",
        ichor_pass_cost=3000,
        timer_seconds=30 * 60,
        party_size_min=18, party_size_max=18,
        drop_pool=_ASKAR_PIECES + _MARDUK_PIECES + _GOETIA_PIECES
                   + _AOIDOS_PIECES + _ESTOQUEUR_PIECES
                   + _GLORY_TOKENS + ("odins_helm", "ichor_x100"),
    ),
)


CHAMBER_BY_TIER: dict[EinherjarTier, Chamber] = {
    c.tier: c for c in EINHERJAR_CHAMBERS
}


def chamber_for_tier(tier: EinherjarTier) -> t.Optional[Chamber]:
    return CHAMBER_BY_TIER.get(tier)


def pass_cost_in_ichor(tier: EinherjarTier) -> int:
    c = CHAMBER_BY_TIER.get(tier)
    return c.ichor_pass_cost if c else 0


@dataclasses.dataclass
class PlayerEinherjarBalance:
    player_id: str
    ichor: int = 0
    chamber_passes: list[EinherjarTier] = dataclasses.field(
        default_factory=list,
    )

    def buy_pass(self, *, tier: EinherjarTier) -> bool:
        cost = pass_cost_in_ichor(tier)
        if cost == 0 or self.ichor < cost:
            return False
        self.ichor -= cost
        self.chamber_passes.append(tier)
        return True

    def consume_pass(self, *, tier: EinherjarTier) -> bool:
        if tier not in self.chamber_passes:
            return False
        self.chamber_passes.remove(tier)
        return True

    def grant_ichor(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.ichor += amount
        return True


__all__ = [
    "EinherjarTier", "Chamber",
    "EINHERJAR_CHAMBERS", "CHAMBER_BY_TIER",
    "chamber_for_tier", "pass_cost_in_ichor",
    "PlayerEinherjarBalance",
]
