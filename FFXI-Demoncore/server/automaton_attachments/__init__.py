"""Automaton attachments — PUP automaton hardware + Tomb Raid set.

Why this module exists
----------------------
PUP's automaton has 8 attachment slots. Attachments are tiny
hardware mods that influence elemental capacity, stat lines, and
maneuver effects. Most attachments are crafted or bought at the
Cobra Unit shop. The Tomb Raid set is the spicy exception:

    Tomb Raid I  -> Tomb Raid V

Five attachments tied to the Lightning maneuver, R/EX (one per
character, no AH, no bazaar), NOT craftable, dropped only by a
roaming neutral WHM Rogue Automaton at a 1% rate per kill, and
they drop in order:

    A character with nothing rolls Tomb Raid I when the drop
    fires. After they own I, the next drop is II. After II, III.
    And so on, until they own all five.

Per-kill cap: a roaming automaton kill drops AT MOST one Tomb
Raid attachment, even if multiple drop slots existed. This makes
the chain a deliberate progression — players know the next slot
will roll the next tier they need.

Public surface
--------------
    Maneuver                  enum (8 elements)
    Attachment                immutable: id, label, maneuver, tier,
                                rarity flags, source mob
    TOMB_RAID_SET             tuple[Attachment, ...] — 5 entries
    AttachmentInventory       per-character ownership tracker
    next_tomb_raid_drop(inv)  -> Attachment | None
    WHM_AUTOMATON_DROP_CHANCE 0.01 (1%)
    roll_roaming_automaton_drop(...) -> Attachment | None
        AT MOST one item per call — enforced
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.loot_table import (
    DEFAULT_TH_PROC_CHANCE,
    TreasureHunterState,
    proc_treasure_hunter,
)
from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class Maneuver(str, enum.Enum):
    """The 8 elemental maneuvers PUP can stack on automaton."""
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


@dataclasses.dataclass(frozen=True)
class Attachment:
    """One automaton attachment definition."""
    attachment_id: str
    label: str
    maneuver: Maneuver
    tier: int                          # 1..N within a set
    is_rare_ex: bool                   # R/EX = single copy per char
    is_craftable: bool                 # False = drop-only
    source_mob: str                    # mob_class_id of dropping mob
    description: str = ""


# -- the Tomb Raid set ------------------------------------------------

# Source mob: a roaming neutral WHM Rogue Automaton. Lives in the
# wilds (not bound to a fixed spawn). Drops at 1% per kill,
# locked to in-order tier progression per character.
SOURCE_MOB_ID = "rogue_automaton_whm_neutral"

TOMB_RAID_SET: tuple[Attachment, ...] = (
    Attachment(
        attachment_id="tomb_raid_1",
        label="Tomb Raid I",
        maneuver=Maneuver.LIGHTNING,
        tier=1,
        is_rare_ex=True,
        is_craftable=False,
        source_mob=SOURCE_MOB_ID,
        description=(
            "Spectral conduit attachment salvaged from a fallen "
            "rogue. Lightning maneuver entry tier."
        ),
    ),
    Attachment(
        attachment_id="tomb_raid_2",
        label="Tomb Raid II",
        maneuver=Maneuver.LIGHTNING,
        tier=2,
        is_rare_ex=True,
        is_craftable=False,
        source_mob=SOURCE_MOB_ID,
        description=(
            "Refined spectral conduit. Lightning maneuver tier II."
        ),
    ),
    Attachment(
        attachment_id="tomb_raid_3",
        label="Tomb Raid III",
        maneuver=Maneuver.LIGHTNING,
        tier=3,
        is_rare_ex=True,
        is_craftable=False,
        source_mob=SOURCE_MOB_ID,
        description=(
            "Polished spectral conduit. Lightning maneuver tier III."
        ),
    ),
    Attachment(
        attachment_id="tomb_raid_4",
        label="Tomb Raid IV",
        maneuver=Maneuver.LIGHTNING,
        tier=4,
        is_rare_ex=True,
        is_craftable=False,
        source_mob=SOURCE_MOB_ID,
        description=(
            "Master-class spectral conduit. Lightning maneuver "
            "tier IV."
        ),
    ),
    Attachment(
        attachment_id="tomb_raid_5",
        label="Tomb Raid V",
        maneuver=Maneuver.LIGHTNING,
        tier=5,
        is_rare_ex=True,
        is_craftable=False,
        source_mob=SOURCE_MOB_ID,
        description=(
            "Apex spectral conduit. Lightning maneuver tier V — "
            "the chain-ender."
        ),
    ),
)

# Stable index by attachment_id for fast lookup.
ATTACHMENT_BY_ID: dict[str, Attachment] = {
    a.attachment_id: a for a in TOMB_RAID_SET
}


# -- per-character ownership ------------------------------------------

@dataclasses.dataclass
class AttachmentInventory:
    """Per-character attachment ownership tracker.

    Set semantics: adding the same attachment twice is a no-op.
    R/EX rules enforce at-most-one-per-character upstream; this
    container just records ownership.
    """
    player_id: str
    owned: set[str] = dataclasses.field(default_factory=set)

    def add(self, attachment_id: str) -> bool:
        """Record ownership. Returns True if this was a new item,
        False if the player already had it (R/EX no-op)."""
        if attachment_id in self.owned:
            return False
        self.owned.add(attachment_id)
        return True

    def has(self, attachment_id: str) -> bool:
        return attachment_id in self.owned

    def tomb_raid_progress(self) -> int:
        """How many Tomb Raid tiers the player has collected (0..5)."""
        return sum(
            1 for a in TOMB_RAID_SET if a.attachment_id in self.owned
        )


# -- drop chain --------------------------------------------------------

def next_tomb_raid_drop(
    inventory: AttachmentInventory,
) -> t.Optional[Attachment]:
    """Return the next Tomb Raid tier this player needs.

    Walks TOMB_RAID_SET in tier order; returns the first tier the
    player does NOT own. Returns None when they own all 5.
    """
    for att in TOMB_RAID_SET:
        if att.attachment_id not in inventory.owned:
            return att
    return None


# Roaming WHM automaton drops at 1% per kill, AT MOST one item.
WHM_AUTOMATON_DROP_CHANCE = 0.01


def roll_roaming_automaton_drop(
    *,
    inventory: AttachmentInventory,
    rng_pool: RngPool,
    drop_chance: float = WHM_AUTOMATON_DROP_CHANCE,
    stream_name: str = STREAM_LOOT_DROPS,
) -> t.Optional[Attachment]:
    """Roll one drop from a roaming WHM automaton kill.

    Per the Tomb Raid drop chain rules:
      - At most ONE attachment per kill (caller doesn't loop).
      - Returns the next tier the killer needs (in-order progression).
      - Player who already owns all 5 never sees another drop.
      - drop_chance must be in [0, 1].

    Returns the Attachment on a fired drop, or None on a miss
    (and also None when the inventory is already maxed).
    """
    if not 0.0 <= drop_chance <= 1.0:
        raise ValueError("drop_chance must be in [0, 1]")
    next_att = next_tomb_raid_drop(inventory)
    if next_att is None:
        return None
    rng = rng_pool.stream(stream_name)
    if rng.random() < drop_chance:
        return next_att
    return None


def award_drop(
    *,
    inventory: AttachmentInventory,
    attachment: Attachment,
) -> bool:
    """Add the attachment to the player's inventory.

    Convenience wrapper that just calls inventory.add. Caller can
    also call inventory.add directly. Returns True on success
    (the attachment was new), False if they already owned it.
    """
    return inventory.add(attachment.attachment_id)


# -- Tomb Raid gameplay effects -------------------------------------

# Per-attachment TH proc-chance bonus, per active lightning maneuver.
# Each Tomb Raid piece equipped contributes this much PER active
# lightning maneuver. With 3 maneuvers and 5 pieces: 3*5*0.01 = 15%.
TH_PROC_CHANCE_PER_LIGHTNING_PER_PIECE = 0.01


def _is_tomb_raid(att: Attachment) -> bool:
    return att.attachment_id in {
        a.attachment_id for a in TOMB_RAID_SET
    }


def tomb_raid_th_bonus(
    equipped: t.Iterable[Attachment],
) -> int:
    """Sum of tier values for equipped Tomb Raid attachments.

    Tomb Raid I = +1 TH, II = +2, III = +3, IV = +4, V = +5.
    Equip the full set and you contribute +15 to equipment_level.
    The TreasureHunterState equipped-stack cap (MAX_TH_EQUIPPED=9)
    clamps the contribution before procs apply.

    Non-Tomb-Raid attachments are ignored.
    """
    return sum(a.tier for a in equipped if _is_tomb_raid(a))


def lightning_proc_chance_bonus(
    equipped: t.Iterable[Attachment],
    *,
    lightning_maneuvers_active: int,
) -> float:
    """The bonus added to TH proc chance from lightning + Tomb Raid.

    Rule: every active lightning maneuver adds 1% TH proc chance
    per equipped Tomb Raid attachment. Pure multiplication:

        bonus = pieces * maneuvers * 0.01

    Returns 0.0 if no maneuvers are up or no Tomb Raid pieces are
    equipped.
    """
    if lightning_maneuvers_active < 0:
        raise ValueError(
            f"lightning_maneuvers_active {lightning_maneuvers_active} "
            "must be >= 0"
        )
    pieces = sum(1 for a in equipped if _is_tomb_raid(a))
    if pieces == 0 or lightning_maneuvers_active == 0:
        return 0.0
    return (
        pieces
        * lightning_maneuvers_active
        * TH_PROC_CHANCE_PER_LIGHTNING_PER_PIECE
    )


def equipment_level_with_attachments(
    base_equipment_level: int,
    equipped: t.Iterable[Attachment],
) -> int:
    """Combine base gear TH with Tomb Raid attachment tiers.

    Returns the raw sum (not yet clamped). Caller should pass this
    into a TreasureHunterState; effective_th_level applies the
    MAX_TH_EQUIPPED cap.
    """
    if base_equipment_level < 0:
        raise ValueError("base_equipment_level must be >= 0")
    return base_equipment_level + tomb_raid_th_bonus(equipped)


def proc_with_attachments(
    state: TreasureHunterState,
    rng_pool: RngPool,
    *,
    equipped: t.Iterable[Attachment],
    lightning_maneuvers_active: int,
    base_proc_chance: float = DEFAULT_TH_PROC_CHANCE,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[bool, TreasureHunterState]:
    """Roll a TH proc taking Tomb Raid + lightning maneuvers into
    account.

    Total proc chance = base_proc_chance + lightning_proc_chance_bonus.
    The combined chance is clamped to [0, 1] before the roll fires
    so wild values (e.g. 8 maneuvers) don't blow past 100%.

    Returns the same shape as proc_treasure_hunter:
    (procced: bool, new_state: TreasureHunterState).
    """
    # Materialize once — the iterable might be a generator and we
    # use it twice (bonus calc + future inspection by tests).
    equipped_tuple = tuple(equipped)
    bonus = lightning_proc_chance_bonus(
        equipped_tuple,
        lightning_maneuvers_active=lightning_maneuvers_active,
    )
    total = base_proc_chance + bonus
    clamped = max(0.0, min(1.0, total))
    return proc_treasure_hunter(
        state, rng_pool,
        proc_chance=clamped,
        stream_name=stream_name,
    )


__all__ = [
    "Maneuver",
    "Attachment",
    "TOMB_RAID_SET",
    "ATTACHMENT_BY_ID",
    "SOURCE_MOB_ID",
    "AttachmentInventory",
    "next_tomb_raid_drop",
    "WHM_AUTOMATON_DROP_CHANCE",
    "roll_roaming_automaton_drop",
    "award_drop",
    "TH_PROC_CHANCE_PER_LIGHTNING_PER_PIECE",
    "tomb_raid_th_bonus",
    "lightning_proc_chance_bonus",
    "equipment_level_with_attachments",
    "proc_with_attachments",
]
