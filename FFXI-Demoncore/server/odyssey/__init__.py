"""Odyssey — recent retail endgame: Sheol A/B/C + Gaol gods.

Three difficulty tiers:
    SHEOL_A — entry-level, smaller groups
    SHEOL_B — middle-tier, NM-rich
    SHEOL_C — hardest non-Gaol, gear-check

Gaol — capstone arena hosting six gods (the Adoulin pantheon
projected onto Odyssey's mirrors). Each gaol fight has a unique
mechanic and drops mostly job-specific 119-cap REMA-tier gear.

Currency stack:
    SEGMENTS — primary currency, traded at NPC for Moglophone
        upgrades, gear, etc.
    GAOL CARDS — proof-of-clear tokens for each gaol god
    MOGLOPHONE_VOLUTE — character-level progress meter that
        unlocks higher-tier Sheol runs as you progress

Public surface
--------------
    SheolTier enum
    GaolGod enum (six gods)
    SheolEntry / GaolEntry dataclasses
    PlayerOdysseyProgress
        .award_segments(amount) / .spend_segments(amount)
        .complete_sheol(tier) -> bumps moglophone_volute
        .can_attempt_gaol(god) -> bool (volute gate)
        .clear_gaol(god) -> records card
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SheolTier(str, enum.Enum):
    A = "sheol_a"
    B = "sheol_b"
    C = "sheol_c"
    D = "sheol_d"          # Demoncore extension — top-tier above C


class GaolGod(str, enum.Enum):
    BUMBA = "bumba"        # earth — heaviest melee
    MBOZE = "mboze"        # water — sustained dot
    AREBATI = "arebati"    # wind — spike speed
    NGAI = "ngai"          # ice — frozen control
    KALUNGA = "kalunga"    # dark — recurring death
    OUROBOROS = "ouroboros"  # all elements (formerly final)
    MWIINDI = "mwiindi"    # Demoncore — capstone above Ouroboros


# How much volute progress each Sheol tier awards. Gaol gates
# scale with cumulative volute.
_SHEOL_VOLUTE_AWARD: dict[SheolTier, int] = {
    SheolTier.A: 50,
    SheolTier.B: 150,
    SheolTier.C: 350,
    SheolTier.D: 800,
}


# Volute gate per gaol god (must reach this volute to attempt).
_GAOL_VOLUTE_GATE: dict[GaolGod, int] = {
    GaolGod.BUMBA: 1000,
    GaolGod.MBOZE: 1500,
    GaolGod.AREBATI: 2000,
    GaolGod.NGAI: 2500,
    GaolGod.KALUNGA: 3500,
    GaolGod.OUROBOROS: 5000,
    GaolGod.MWIINDI: 8000,
}


# Segment payouts per tier
_SHEOL_SEGMENT_AWARD: dict[SheolTier, int] = {
    SheolTier.A: 800,
    SheolTier.B: 2000,
    SheolTier.C: 5000,
    SheolTier.D: 12000,
}


@dataclasses.dataclass(frozen=True)
class SheolEntry:
    tier: SheolTier
    label: str
    party_size_min: int
    party_size_max: int
    timer_seconds: int
    segment_award: int
    volute_award: int


@dataclasses.dataclass(frozen=True)
class GaolEntry:
    god: GaolGod
    label: str
    volute_required: int
    party_size_min: int
    party_size_max: int
    drop_pool: tuple[str, ...]


SHEOL_CATALOG: tuple[SheolEntry, ...] = (
    SheolEntry(
        SheolTier.A, "Sheol A — Wandering Ramparts",
        party_size_min=1, party_size_max=6,
        timer_seconds=15 * 60,
        segment_award=_SHEOL_SEGMENT_AWARD[SheolTier.A],
        volute_award=_SHEOL_VOLUTE_AWARD[SheolTier.A],
    ),
    SheolEntry(
        SheolTier.B, "Sheol B — Lasting Twilight",
        party_size_min=3, party_size_max=18,
        timer_seconds=30 * 60,
        segment_award=_SHEOL_SEGMENT_AWARD[SheolTier.B],
        volute_award=_SHEOL_VOLUTE_AWARD[SheolTier.B],
    ),
    SheolEntry(
        SheolTier.C, "Sheol C — Iron Gauntlet",
        party_size_min=6, party_size_max=18,
        timer_seconds=45 * 60,
        segment_award=_SHEOL_SEGMENT_AWARD[SheolTier.C],
        volute_award=_SHEOL_VOLUTE_AWARD[SheolTier.C],
    ),
    SheolEntry(
        SheolTier.D, "Sheol D — Apex Veil",
        party_size_min=12, party_size_max=18,
        timer_seconds=60 * 60,
        segment_award=_SHEOL_SEGMENT_AWARD[SheolTier.D],
        volute_award=_SHEOL_VOLUTE_AWARD[SheolTier.D],
    ),
)


GAOL_CATALOG: tuple[GaolEntry, ...] = (
    GaolEntry(
        GaolGod.BUMBA, "Bumba (earth-aspect Gaol)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.BUMBA],
        party_size_min=6, party_size_max=18,
        drop_pool=("nyame_helm", "nyame_breastplate",
                    "su5_pld_helm", "gaol_card_bumba"),
    ),
    GaolEntry(
        GaolGod.MBOZE, "Mboze (water-aspect Gaol)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.MBOZE],
        party_size_min=6, party_size_max=18,
        drop_pool=("agwu_robe", "agwu_pigaches",
                    "su5_blm_robe", "gaol_card_mboze"),
    ),
    GaolEntry(
        GaolGod.AREBATI, "Arebati (wind-aspect Gaol)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.AREBATI],
        party_size_min=6, party_size_max=18,
        drop_pool=("ayanmo_corazza", "ayanmo_zucchetto",
                    "su5_war_helm", "gaol_card_arebati"),
    ),
    GaolEntry(
        GaolGod.NGAI, "Ngai (ice-aspect Gaol)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.NGAI],
        party_size_min=12, party_size_max=18,
        drop_pool=("gleti_helm", "gleti_breastplate",
                    "su5_drk_helm", "gaol_card_ngai"),
    ),
    GaolEntry(
        GaolGod.KALUNGA, "Kalunga (dark-aspect Gaol)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.KALUNGA],
        party_size_min=12, party_size_max=18,
        drop_pool=("malignance_chapeau", "malignance_tabard",
                    "su5_sch_robe", "gaol_card_kalunga"),
    ),
    GaolEntry(
        GaolGod.OUROBOROS, "Ouroboros (all elements)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.OUROBOROS],
        party_size_min=18, party_size_max=18,
        drop_pool=("ouroboros_relic_card",
                    "ouroboros_empyrean_card",
                    "ouroboros_mythic_card",
                    "gaol_card_ouroboros"),
    ),
    GaolEntry(
        GaolGod.MWIINDI, "Mwiindi (Demoncore capstone — beyond elements)",
        volute_required=_GAOL_VOLUTE_GATE[GaolGod.MWIINDI],
        party_size_min=18, party_size_max=18,
        drop_pool=("mwiindi_prime_card",
                    "mwiindi_aeonic_card",
                    "mwiindi_relic_plus_card",
                    "shadow_genkai_progress_marker",
                    "gaol_card_mwiindi"),
    ),
)


SHEOL_BY_TIER: dict[SheolTier, SheolEntry] = {
    e.tier: e for e in SHEOL_CATALOG
}
GAOL_BY_GOD: dict[GaolGod, GaolEntry] = {
    e.god: e for e in GAOL_CATALOG
}


def sheol_entry(tier: SheolTier) -> t.Optional[SheolEntry]:
    return SHEOL_BY_TIER.get(tier)


def gaol_entry(god: GaolGod) -> t.Optional[GaolEntry]:
    return GAOL_BY_GOD.get(god)


SHEOL_RUNS_PER_VANA_DAY = 3   # Demoncore cap (was canonical-uncapped)


@dataclasses.dataclass
class PlayerOdysseyProgress:
    player_id: str
    segments: int = 0
    moglophone_volute: int = 0
    cleared_gaols: list[GaolGod] = dataclasses.field(default_factory=list)
    sheol_clears: dict[SheolTier, int] = dataclasses.field(
        default_factory=dict,
    )
    # Per-day Sheol throttle
    last_sheol_day: int = -1
    sheol_runs_today: int = 0

    def award_segments(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.segments += amount
        return True

    def spend_segments(self, *, amount: int) -> bool:
        if amount <= 0 or self.segments < amount:
            return False
        self.segments -= amount
        return True

    def can_run_sheol(self, *, current_vana_day: int) -> bool:
        if self.last_sheol_day != current_vana_day:
            return True
        return self.sheol_runs_today < SHEOL_RUNS_PER_VANA_DAY

    def complete_sheol(
        self, *, tier: SheolTier,
        current_vana_day: t.Optional[int] = None,
    ) -> int:
        """Bump volute + award segments for a Sheol clear. Returns
        new total volute. When current_vana_day is provided, the
        per-day cap (3 runs) is enforced; passing None preserves
        the legacy uncapped behavior for older callers."""
        if current_vana_day is not None:
            if self.last_sheol_day != current_vana_day:
                self.last_sheol_day = current_vana_day
                self.sheol_runs_today = 0
            if self.sheol_runs_today >= SHEOL_RUNS_PER_VANA_DAY:
                return self.moglophone_volute
            self.sheol_runs_today += 1
        entry = SHEOL_BY_TIER[tier]
        self.moglophone_volute += entry.volute_award
        self.segments += entry.segment_award
        self.sheol_clears[tier] = self.sheol_clears.get(tier, 0) + 1
        return self.moglophone_volute

    def can_attempt_gaol(self, *, god: GaolGod) -> bool:
        return self.moglophone_volute >= _GAOL_VOLUTE_GATE[god]

    def clear_gaol(self, *, god: GaolGod) -> bool:
        if not self.can_attempt_gaol(god=god):
            return False
        if god in self.cleared_gaols:
            return False
        self.cleared_gaols.append(god)
        return True


__all__ = [
    "SheolTier", "GaolGod",
    "SheolEntry", "GaolEntry",
    "SHEOL_CATALOG", "GAOL_CATALOG",
    "SHEOL_BY_TIER", "GAOL_BY_GOD",
    "SHEOL_RUNS_PER_VANA_DAY",
    "sheol_entry", "gaol_entry",
    "PlayerOdysseyProgress",
]
