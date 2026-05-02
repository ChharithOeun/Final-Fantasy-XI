"""Temp item pool — instance-scoped consumables.

Sky/Sea/Salvage and other instances grant TEMP items: a parallel
inventory that:
* lives only inside the instance — exit purges everything
* can't be traded, stored, sent to delivery box, or auctioned
* stacks differently from regular items (unique slot per id)
* has a hard cap (default 30) per player

Public surface
--------------
    TempItemKind enum (POTION / ETHER / VILE_ELIXIR / ...)
    TempItemDef
    TEMP_ITEM_CATALOG
    PlayerTempInventory
        .grant(item_id, count)
        .consume(item_id, count)
        .clear()  # called on instance exit
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_TEMP_ITEMS_PER_PLAYER = 30


class TempItemKind(str, enum.Enum):
    HEAL_HP = "heal_hp"
    HEAL_MP = "heal_mp"
    BUFF = "buff"
    UTILITY = "utility"
    REVIVE = "revive"


@dataclasses.dataclass(frozen=True)
class TempItemDef:
    item_id: str
    kind: TempItemKind
    label: str
    max_stack: int = 12


# Sample catalog — modeled on Sky/Sea/Salvage temps
TEMP_ITEM_CATALOG: dict[str, TempItemDef] = {
    "potion_temp": TempItemDef(
        "potion_temp", TempItemKind.HEAL_HP, "Potion (Temp)",
    ),
    "hi_potion_temp": TempItemDef(
        "hi_potion_temp", TempItemKind.HEAL_HP, "Hi-Potion (Temp)",
    ),
    "ether_temp": TempItemDef(
        "ether_temp", TempItemKind.HEAL_MP, "Ether (Temp)",
    ),
    "hi_ether_temp": TempItemDef(
        "hi_ether_temp", TempItemKind.HEAL_MP, "Hi-Ether (Temp)",
    ),
    "vile_elixir_temp": TempItemDef(
        "vile_elixir_temp", TempItemKind.HEAL_HP,
        "Vile Elixir (Temp)", max_stack=4,
    ),
    "vile_elixir_p2_temp": TempItemDef(
        "vile_elixir_p2_temp", TempItemKind.HEAL_HP,
        "Vile Elixir +1 (Temp)", max_stack=4,
    ),
    "remedy_temp": TempItemDef(
        "remedy_temp", TempItemKind.UTILITY, "Remedy (Temp)",
    ),
    "reraiser_temp": TempItemDef(
        "reraiser_temp", TempItemKind.REVIVE, "Reraiser (Temp)",
        max_stack=4,
    ),
    "icarus_wing_temp": TempItemDef(
        "icarus_wing_temp", TempItemKind.BUFF,
        "Icarus Wing (Temp)", max_stack=4,
    ),
    "blink_band_temp": TempItemDef(
        "blink_band_temp", TempItemKind.BUFF,
        "Blink Band (Temp)", max_stack=4,
    ),
}


@dataclasses.dataclass(frozen=True)
class GrantResult:
    accepted: bool
    granted: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ConsumeResult:
    accepted: bool
    consumed: int = 0
    remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerTempInventory:
    player_id: str
    _slots: dict[str, int] = dataclasses.field(default_factory=dict)

    @property
    def total_slots_used(self) -> int:
        return len(self._slots)

    def count(self, item_id: str) -> int:
        return self._slots.get(item_id, 0)

    def grant(self, *, item_id: str, count: int = 1) -> GrantResult:
        d = TEMP_ITEM_CATALOG.get(item_id)
        if d is None:
            return GrantResult(False, reason="unknown temp item")
        if count <= 0:
            return GrantResult(False, reason="count must be > 0")
        existing = self._slots.get(item_id, 0)
        # New slot? Check cap.
        if existing == 0 and self.total_slots_used >= MAX_TEMP_ITEMS_PER_PLAYER:
            return GrantResult(False, reason="temp inventory full")
        new_total = min(existing + count, d.max_stack)
        granted = new_total - existing
        if granted <= 0:
            return GrantResult(False, reason="stack already maxed")
        self._slots[item_id] = new_total
        return GrantResult(accepted=True, granted=granted)

    def consume(self, *, item_id: str,
                 count: int = 1) -> ConsumeResult:
        existing = self._slots.get(item_id, 0)
        if existing <= 0:
            return ConsumeResult(False, reason="none in inventory")
        if count <= 0:
            return ConsumeResult(False, reason="count must be > 0")
        consumed = min(existing, count)
        remaining = existing - consumed
        if remaining <= 0:
            del self._slots[item_id]
        else:
            self._slots[item_id] = remaining
        return ConsumeResult(
            accepted=True, consumed=consumed, remaining=remaining,
        )

    def clear(self) -> int:
        """Called on instance exit. Returns number of slots cleared."""
        n = len(self._slots)
        self._slots.clear()
        return n


__all__ = [
    "MAX_TEMP_ITEMS_PER_PLAYER",
    "TempItemKind", "TempItemDef", "TEMP_ITEM_CATALOG",
    "GrantResult", "ConsumeResult",
    "PlayerTempInventory",
]
