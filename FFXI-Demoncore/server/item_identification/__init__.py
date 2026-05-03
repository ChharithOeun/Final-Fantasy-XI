"""Item identification — unidentified loot from chests/dungeons.

Some loot drops UNIDENTIFIED. The player sees a generic descriptor
("scarred sword", "weathered tome") instead of the real name.
Until identified, the item is UNUSABLE — can't be equipped, can't
be cast, can't be sold for full value (vendors offer a flat
junk price for unknowns).

Identification methods
----------------------
    APPRAISER_NPC      pay an Appraiser NPC; flat fee per tier
    SELF_APPRAISE      use the Appraisal skill; success rate
                       scales with skill vs item tier
    SCROLL_OF_IDENTIFY consume an Identify scroll; auto-success
    ITEM_USE           equip / use the item to learn it (risk:
                       if the unknown is CURSED, big penalty)

Public surface
--------------
    UnknownTier enum (COMMON / RARE / RELIC / MYTHIC)
    IdentifyMethod enum
    UnknownItem dataclass
    IdentifyOutcome enum (IDENTIFIED / FAILED / CURSED_TRIGGERED)
    IdentifyResult dataclass
    ItemIdentificationRegistry
        .register_unknown(player_id, unknown)
        .appraise_via_npc(player_id, unknown_id, gil_paid)
        .self_appraise(player_id, unknown_id, skill, rng)
        .scroll_identify(player_id, unknown_id)
        .item_use_identify(player_id, unknown_id)
        .known_for(player_id) / .pending_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


class UnknownTier(str, enum.Enum):
    COMMON = "common"
    RARE = "rare"
    RELIC = "relic"
    MYTHIC = "mythic"


class IdentifyMethod(str, enum.Enum):
    APPRAISER_NPC = "appraiser_npc"
    SELF_APPRAISE = "self_appraise"
    SCROLL_OF_IDENTIFY = "scroll_of_identify"
    ITEM_USE = "item_use"


class IdentifyOutcome(str, enum.Enum):
    IDENTIFIED = "identified"
    FAILED = "failed"                    # skill failed; item unchanged
    CURSED_TRIGGERED = "cursed_triggered"  # item was cursed; penalty


# NPC fee per tier.
_APPRAISER_FEE: dict[UnknownTier, int] = {
    UnknownTier.COMMON: 200,
    UnknownTier.RARE: 1500,
    UnknownTier.RELIC: 25000,
    UnknownTier.MYTHIC: 250000,
}

# Self-appraise skill DC per tier (out of 200).
_SELF_APPRAISE_DC: dict[UnknownTier, int] = {
    UnknownTier.COMMON: 30,
    UnknownTier.RARE: 80,
    UnknownTier.RELIC: 140,
    UnknownTier.MYTHIC: 999,        # only special methods
}


@dataclasses.dataclass(frozen=True)
class UnknownItem:
    unknown_id: str
    placeholder_descriptor: str          # "scarred sword"
    real_item_id: str                    # "excalibur"
    tier: UnknownTier = UnknownTier.COMMON
    is_cursed: bool = False
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class IdentifyResult:
    outcome: IdentifyOutcome
    method: IdentifyMethod
    real_item_id: t.Optional[str] = None
    fee_paid: int = 0
    cursed_penalty: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerIDStore:
    pending: dict[str, UnknownItem] = dataclasses.field(
        default_factory=dict,
    )
    known: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class ItemIdentificationRegistry:
    _stores: dict[str, _PlayerIDStore] = dataclasses.field(
        default_factory=dict,
    )

    def _store(self, player_id: str) -> _PlayerIDStore:
        s = self._stores.get(player_id)
        if s is None:
            s = _PlayerIDStore()
            self._stores[player_id] = s
        return s

    def register_unknown(
        self, *, player_id: str, unknown: UnknownItem,
    ) -> bool:
        s = self._store(player_id)
        if unknown.unknown_id in s.pending:
            return False
        s.pending[unknown.unknown_id] = unknown
        return True

    def pending_for(
        self, player_id: str,
    ) -> tuple[UnknownItem, ...]:
        return tuple(self._store(player_id).pending.values())

    def known_for(
        self, player_id: str,
    ) -> tuple[str, ...]:
        return tuple(self._store(player_id).known)

    def _resolve_success(
        self, *, player_id: str, unknown_id: str,
    ) -> tuple[t.Optional[UnknownItem], _PlayerIDStore]:
        s = self._store(player_id)
        unknown = s.pending.pop(unknown_id, None)
        if unknown is not None:
            s.known.add(unknown.real_item_id)
        return unknown, s

    def appraise_via_npc(
        self, *, player_id: str, unknown_id: str,
        gil_offered: int,
    ) -> IdentifyResult:
        s = self._store(player_id)
        unknown = s.pending.get(unknown_id)
        if unknown is None:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.APPRAISER_NPC,
                reason="no such unknown item",
            )
        fee = _APPRAISER_FEE[unknown.tier]
        if gil_offered < fee:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.APPRAISER_NPC,
                fee_paid=0,
                reason=f"need {fee} gil",
            )
        u, _ = self._resolve_success(
            player_id=player_id, unknown_id=unknown_id,
        )
        # NPC appraisal does NOT trigger curses; they note them.
        return IdentifyResult(
            outcome=IdentifyOutcome.IDENTIFIED,
            method=IdentifyMethod.APPRAISER_NPC,
            real_item_id=u.real_item_id,
            fee_paid=fee,
        )

    def self_appraise(
        self, *, player_id: str, unknown_id: str,
        appraisal_skill: int,
        rng: t.Optional[random.Random] = None,
    ) -> IdentifyResult:
        rng = rng or random.Random()
        s = self._store(player_id)
        unknown = s.pending.get(unknown_id)
        if unknown is None:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.SELF_APPRAISE,
                reason="no such unknown item",
            )
        dc = _SELF_APPRAISE_DC[unknown.tier]
        if appraisal_skill < dc:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.SELF_APPRAISE,
                reason=(
                    f"skill {appraisal_skill} < DC {dc}"
                ),
            )
        # Skill >= DC: probability proportional to margin
        margin = appraisal_skill - dc
        success_chance = min(95, 50 + margin)
        if rng.randint(1, 100) > success_chance:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.SELF_APPRAISE,
                reason="skill check failed roll",
            )
        u, _ = self._resolve_success(
            player_id=player_id, unknown_id=unknown_id,
        )
        return IdentifyResult(
            outcome=IdentifyOutcome.IDENTIFIED,
            method=IdentifyMethod.SELF_APPRAISE,
            real_item_id=u.real_item_id,
        )

    def scroll_identify(
        self, *, player_id: str, unknown_id: str,
    ) -> IdentifyResult:
        s = self._store(player_id)
        unknown = s.pending.get(unknown_id)
        if unknown is None:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.SCROLL_OF_IDENTIFY,
                reason="no such unknown item",
            )
        u, _ = self._resolve_success(
            player_id=player_id, unknown_id=unknown_id,
        )
        return IdentifyResult(
            outcome=IdentifyOutcome.IDENTIFIED,
            method=IdentifyMethod.SCROLL_OF_IDENTIFY,
            real_item_id=u.real_item_id,
        )

    def item_use_identify(
        self, *, player_id: str, unknown_id: str,
    ) -> IdentifyResult:
        """Wear/use the unknown to learn it. Risk: cursed
        unknowns trigger their curse on the user."""
        s = self._store(player_id)
        unknown = s.pending.get(unknown_id)
        if unknown is None:
            return IdentifyResult(
                outcome=IdentifyOutcome.FAILED,
                method=IdentifyMethod.ITEM_USE,
                reason="no such unknown item",
            )
        # Always ID — but cursed items snap shut.
        u, _ = self._resolve_success(
            player_id=player_id, unknown_id=unknown_id,
        )
        if u.is_cursed:
            return IdentifyResult(
                outcome=IdentifyOutcome.CURSED_TRIGGERED,
                method=IdentifyMethod.ITEM_USE,
                real_item_id=u.real_item_id,
                cursed_penalty="curse triggered on wear",
            )
        return IdentifyResult(
            outcome=IdentifyOutcome.IDENTIFIED,
            method=IdentifyMethod.ITEM_USE,
            real_item_id=u.real_item_id,
        )

    def total_pending(self, player_id: str) -> int:
        return len(self._store(player_id).pending)


__all__ = [
    "UnknownTier", "IdentifyMethod", "IdentifyOutcome",
    "UnknownItem", "IdentifyResult",
    "ItemIdentificationRegistry",
]
