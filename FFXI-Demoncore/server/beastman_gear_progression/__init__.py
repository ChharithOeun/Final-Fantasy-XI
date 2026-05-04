"""Beastman gear progression — race-specific gear ladders.

Each beastman race has a tiered gear ladder that lines up
canonically with the hume tier curve. The retail TIERS are
roughly: STARTER (lvl 1) -> NOVICE (10) -> JOURNEYMAN (30) ->
EXPERT (50) -> RELIC_TIER (75) -> EMPYREAN_TIER (90) ->
MYTHIC_TIER (99) -> SU_TIER (119+).

Each beastman gear PIECE has a CANON_EQUIVALENT pointing at the
hume-side item it parallels (so balance and itemization match).
The ladder enforces that you can only craft/wield the next tier
once the prior tier requirement is met.

Public surface
--------------
    GearTier enum
    GearSlotCategory enum
    BeastmanGearPiece dataclass
    UnlockResult dataclass
    BeastmanGearProgression
        .register_piece(piece_id, race, tier, canon_eq, slot)
        .unlock(player_id, piece_id, prior_tier_unlocked)
        .progression_for(race) -> tuple[BeastmanGearPiece]
        .next_tier_for_player(player_id, race) -> Optional[GearTier]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class GearTier(str, enum.Enum):
    STARTER = "starter"          # lvl 1 cloth
    NOVICE = "novice"            # 10
    JOURNEYMAN = "journeyman"    # 30
    EXPERT = "expert"            # 50
    RELIC_TIER = "relic_tier"    # 75
    EMPYREAN_TIER = "empyrean"   # 90
    MYTHIC_TIER = "mythic"       # 99
    SU_TIER = "su"               # 119+


_TIER_ORDER: tuple[GearTier, ...] = tuple(GearTier)
_TIER_INDEX: dict[GearTier, int] = {
    t: i for i, t in enumerate(_TIER_ORDER)
}


_TIER_LEVEL_GATE: dict[GearTier, int] = {
    GearTier.STARTER: 1,
    GearTier.NOVICE: 10,
    GearTier.JOURNEYMAN: 30,
    GearTier.EXPERT: 50,
    GearTier.RELIC_TIER: 75,
    GearTier.EMPYREAN_TIER: 90,
    GearTier.MYTHIC_TIER: 99,
    GearTier.SU_TIER: 119,
}


class GearSlotCategory(str, enum.Enum):
    WEAPON = "weapon"
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    ACCESSORY = "accessory"


@dataclasses.dataclass(frozen=True)
class BeastmanGearPiece:
    piece_id: str
    race: BeastmanRace
    tier: GearTier
    slot: GearSlotCategory
    label: str
    canon_equivalent_item_id: str
    level_gate: int


@dataclasses.dataclass(frozen=True)
class UnlockResult:
    accepted: bool
    piece_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanGearProgression:
    _pieces: dict[str, BeastmanGearPiece] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, race) -> set of unlocked piece_ids
    _unlocked: dict[
        tuple[str, BeastmanRace], set[str],
    ] = dataclasses.field(default_factory=dict)

    def register_piece(
        self, *, piece_id: str,
        race: BeastmanRace,
        tier: GearTier,
        slot: GearSlotCategory,
        label: str,
        canon_equivalent_item_id: str,
    ) -> t.Optional[BeastmanGearPiece]:
        if piece_id in self._pieces:
            return None
        if not label or not canon_equivalent_item_id:
            return None
        p = BeastmanGearPiece(
            piece_id=piece_id, race=race, tier=tier,
            slot=slot, label=label,
            canon_equivalent_item_id=(
                canon_equivalent_item_id
            ),
            level_gate=_TIER_LEVEL_GATE[tier],
        )
        self._pieces[piece_id] = p
        return p

    def get(self, piece_id: str) -> t.Optional[BeastmanGearPiece]:
        return self._pieces.get(piece_id)

    def progression_for(
        self, *, race: BeastmanRace,
    ) -> tuple[BeastmanGearPiece, ...]:
        rows = [
            p for p in self._pieces.values()
            if p.race == race
        ]
        rows.sort(
            key=lambda p: (
                _TIER_INDEX[p.tier],
                p.slot.value, p.piece_id,
            ),
        )
        return tuple(rows)

    def _player_set(
        self, player_id: str, race: BeastmanRace,
    ) -> set[str]:
        return self._unlocked.setdefault(
            (player_id, race), set(),
        )

    def unlock(
        self, *, player_id: str,
        race: BeastmanRace,
        piece_id: str,
        player_level: int,
    ) -> UnlockResult:
        p = self._pieces.get(piece_id)
        if p is None:
            return UnlockResult(
                False, piece_id=piece_id,
                reason="no such piece",
            )
        if p.race != race:
            return UnlockResult(
                False, piece_id=piece_id,
                reason="race mismatch",
            )
        if player_level < p.level_gate:
            return UnlockResult(
                False, piece_id=piece_id,
                reason=f"level < {p.level_gate}",
            )
        unlocked = self._player_set(player_id, race)
        # Check that the player has at least one piece of the
        # immediately-prior tier of any slot for this race.
        idx = _TIER_INDEX[p.tier]
        if idx > 0:
            prior_tier = _TIER_ORDER[idx - 1]
            owned_prior_tier = any(
                self._pieces[pid].tier == prior_tier
                and self._pieces[pid].race == race
                for pid in unlocked
            )
            if not owned_prior_tier:
                return UnlockResult(
                    False, piece_id=piece_id,
                    reason=(
                        "prior tier not unlocked"
                    ),
                )
        if piece_id in unlocked:
            return UnlockResult(
                False, piece_id=piece_id,
                reason="already unlocked",
            )
        unlocked.add(piece_id)
        return UnlockResult(
            accepted=True, piece_id=piece_id,
        )

    def unlocked_for(
        self, *, player_id: str,
        race: BeastmanRace,
    ) -> tuple[str, ...]:
        s = self._unlocked.get((player_id, race), set())
        return tuple(sorted(s))

    def next_tier_for_player(
        self, *, player_id: str,
        race: BeastmanRace,
    ) -> t.Optional[GearTier]:
        unlocked_ids = self._unlocked.get(
            (player_id, race), set(),
        )
        if not unlocked_ids:
            return GearTier.STARTER
        owned_tiers = {
            _TIER_INDEX[self._pieces[pid].tier]
            for pid in unlocked_ids
        }
        highest = max(owned_tiers)
        if highest + 1 >= len(_TIER_ORDER):
            return None
        return _TIER_ORDER[highest + 1]

    def total_pieces(self) -> int:
        return len(self._pieces)


__all__ = [
    "GearTier", "GearSlotCategory",
    "BeastmanGearPiece", "UnlockResult",
    "BeastmanGearProgression",
]
