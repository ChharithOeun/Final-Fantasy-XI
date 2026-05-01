"""Treasure pool — group loot distribution after a kill.

Why this module exists
----------------------
FFXI's classic group loot system: when a mob dies, items go into
a shared pool. Members of the alliance/party have a window
(default 5 minutes) to LOT (1-999), PASS, or just let the timer
run out. Highest LOT after the window wins. Ties are resolved
deterministically via rng_pool's achievement_tie_break stream so
the same kill replayed produces the same allocation.

If no one lots before the window expires, FFXI's default behavior
varies: ex/rare items are typically dropped to the pool floor
("freed"); common items can auto-distribute. This module models
both via the *expire_policy* per slot.

Public surface
--------------
    LotAction               PASS / LOT / RECEIVE / EXPIRED
    ExpirePolicy            FREE_TO_FLOOR / RANDOM_TO_PARTY / DISCARD
    TreasureSlot            one item awaiting allocation
    LotResult               outcome of a single member's action
    AllocationResult        slot's resolution after window or full PASS
    TreasurePool            container per party
        .add_drop(...)      push an ItemDrop into the pool
        .lot(slot_id, ...)  member lots N
        .pass_(slot_id,...) member passes
        .receive_directly(slot_id, member)
                            instant award (e.g. EX item to nominated
                            heir)
        .tick(now)          advance time; resolve expired slots
        .open_slots()       slots still awaiting allocation
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ACHIEVEMENT_TIE_BREAK


DEFAULT_WINDOW_SECONDS = 300       # 5 minutes per FFXI retail
LOT_MIN = 1
LOT_MAX = 999


class LotAction(str, enum.Enum):
    PASS = "pass"
    LOT = "lot"
    RECEIVE = "receive"
    EXPIRED = "expired"


class ExpirePolicy(str, enum.Enum):
    FREE_TO_FLOOR = "free_to_floor"          # ex/rare default
    RANDOM_TO_PARTY = "random_to_party"      # common items
    DISCARD = "discard"                      # vanish


@dataclasses.dataclass(frozen=True)
class LotEntry:
    """A single member's lot/pass action on a slot."""
    member_id: str
    action: LotAction
    value: int = 0                            # only meaningful if LOT
    timestamp: int = 0


@dataclasses.dataclass
class TreasureSlot:
    """One item in the pool awaiting resolution."""
    slot_id: int
    item_id: str
    drop_tick: int
    expires_at_tick: int
    expire_policy: ExpirePolicy
    party_members: tuple[str, ...]
    # action history per member:
    actions: dict[str, LotEntry] = dataclasses.field(default_factory=dict)
    # set once allocation resolves:
    awarded_to: t.Optional[str] = None
    final_action: t.Optional[LotAction] = None


@dataclasses.dataclass(frozen=True)
class LotResult:
    """Outcome of a single .lot()/.pass_() call."""
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AllocationResult:
    """The final outcome of a slot."""
    slot_id: int
    item_id: str
    awarded_to: t.Optional[str]
    final_action: LotAction
    expire_policy: ExpirePolicy


def _all_passed(slot: TreasureSlot) -> bool:
    """Did every party member already PASS?"""
    if not slot.party_members:
        return True
    for mid in slot.party_members:
        e = slot.actions.get(mid)
        if e is None or e.action != LotAction.PASS:
            return False
    return True


def _highest_lot(
    slot: TreasureSlot,
    *,
    rng_pool: RngPool,
) -> t.Optional[str]:
    """Find the highest-lotting member; tie-break deterministically."""
    lots = [
        e for e in slot.actions.values()
        if e.action == LotAction.LOT
    ]
    if not lots:
        return None
    top_value = max(e.value for e in lots)
    top_lots = [e for e in lots if e.value == top_value]
    if len(top_lots) == 1:
        return top_lots[0].member_id
    # Tie. Sort by member_id for determinism, then pick via
    # tie-break stream so replay matches.
    sorted_ids = sorted(e.member_id for e in top_lots)
    rng = rng_pool.stream(STREAM_ACHIEVEMENT_TIE_BREAK)
    return rng.choice(sorted_ids)


@dataclasses.dataclass
class TreasurePool:
    """Per-party loot pool."""
    party_id: str
    rng_pool: RngPool
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    _slots: dict[int, TreasureSlot] = dataclasses.field(
        default_factory=dict, repr=False
    )
    _next_slot_id: int = 1

    def add_drop(
        self,
        *,
        item_id: str,
        drop_tick: int,
        party_members: t.Sequence[str],
        expire_policy: ExpirePolicy = ExpirePolicy.FREE_TO_FLOOR,
    ) -> TreasureSlot:
        if not party_members:
            raise ValueError("party_members must be non-empty")
        slot = TreasureSlot(
            slot_id=self._next_slot_id,
            item_id=item_id,
            drop_tick=drop_tick,
            expires_at_tick=drop_tick + self.window_seconds,
            expire_policy=expire_policy,
            party_members=tuple(party_members),
        )
        self._slots[slot.slot_id] = slot
        self._next_slot_id += 1
        return slot

    def get(self, slot_id: int) -> TreasureSlot:
        return self._slots[slot_id]

    def open_slots(self) -> tuple[TreasureSlot, ...]:
        """Slots whose final_action hasn't been set yet."""
        return tuple(
            s for s in self._slots.values()
            if s.final_action is None
        )

    def lot(
        self,
        *,
        slot_id: int,
        member_id: str,
        value: int,
        timestamp: int,
    ) -> LotResult:
        if slot_id not in self._slots:
            return LotResult(False, "unknown slot")
        slot = self._slots[slot_id]
        if slot.final_action is not None:
            return LotResult(False, "slot already resolved")
        if member_id not in slot.party_members:
            return LotResult(False, "member not in party for this slot")
        if not LOT_MIN <= value <= LOT_MAX:
            return LotResult(False,
                             f"lot value {value} outside "
                             f"[{LOT_MIN},{LOT_MAX}]")
        prev = slot.actions.get(member_id)
        if prev is not None:
            return LotResult(False,
                             f"member already acted ({prev.action.value})")
        slot.actions[member_id] = LotEntry(
            member_id=member_id,
            action=LotAction.LOT,
            value=value,
            timestamp=timestamp,
        )
        # If everyone has now acted (lotted or passed), resolve early.
        if self._all_acted(slot):
            self._resolve(slot)
        return LotResult(True)

    def pass_(
        self,
        *,
        slot_id: int,
        member_id: str,
        timestamp: int,
    ) -> LotResult:
        if slot_id not in self._slots:
            return LotResult(False, "unknown slot")
        slot = self._slots[slot_id]
        if slot.final_action is not None:
            return LotResult(False, "slot already resolved")
        if member_id not in slot.party_members:
            return LotResult(False, "member not in party for this slot")
        prev = slot.actions.get(member_id)
        if prev is not None:
            return LotResult(False,
                             f"member already acted ({prev.action.value})")
        slot.actions[member_id] = LotEntry(
            member_id=member_id,
            action=LotAction.PASS,
            timestamp=timestamp,
        )
        if self._all_acted(slot):
            self._resolve(slot)
        return LotResult(True)

    def receive_directly(
        self,
        *,
        slot_id: int,
        member_id: str,
        timestamp: int,
    ) -> LotResult:
        """Bypass the lot window — used for nominated EX-item heirs."""
        if slot_id not in self._slots:
            return LotResult(False, "unknown slot")
        slot = self._slots[slot_id]
        if slot.final_action is not None:
            return LotResult(False, "slot already resolved")
        if member_id not in slot.party_members:
            return LotResult(False, "member not in party for this slot")
        slot.actions[member_id] = LotEntry(
            member_id=member_id,
            action=LotAction.RECEIVE,
            timestamp=timestamp,
        )
        slot.awarded_to = member_id
        slot.final_action = LotAction.RECEIVE
        return LotResult(True)

    def tick(self, *, now_tick: int) -> tuple[AllocationResult, ...]:
        """Advance the clock; resolve any expired un-acted slots.

        Returns the resolutions that fired this tick (empty if none).
        """
        out: list[AllocationResult] = []
        for slot in list(self._slots.values()):
            if slot.final_action is not None:
                continue
            if now_tick >= slot.expires_at_tick:
                self._resolve(slot, expired=True)
            if slot.final_action is not None and \
               slot.slot_id not in {a.slot_id for a in out}:
                # Only emit slots that resolved THIS tick. We detect
                # that by checking the slot was un-resolved at top
                # of loop. Append once.
                out.append(AllocationResult(
                    slot_id=slot.slot_id,
                    item_id=slot.item_id,
                    awarded_to=slot.awarded_to,
                    final_action=slot.final_action,
                    expire_policy=slot.expire_policy,
                ))
        return tuple(out)

    # -- internal helpers -------------------------------------------

    def _all_acted(self, slot: TreasureSlot) -> bool:
        return all(
            mid in slot.actions for mid in slot.party_members
        )

    def _resolve(
        self,
        slot: TreasureSlot,
        *,
        expired: bool = False,
    ) -> None:
        """Decide who gets *slot* and lock it."""
        # 1. Any LOT -> highest lotter wins.
        winner = _highest_lot(slot, rng_pool=self.rng_pool)
        if winner is not None:
            slot.awarded_to = winner
            slot.final_action = LotAction.LOT
            return

        # 2. No lots. If everyone passed and we hit expiry OR all
        # members passed already, fall through to expire policy.
        if expired or _all_passed(slot):
            policy = slot.expire_policy
            if policy == ExpirePolicy.FREE_TO_FLOOR:
                slot.awarded_to = None
                slot.final_action = LotAction.EXPIRED
            elif policy == ExpirePolicy.RANDOM_TO_PARTY:
                # Pick a random party member via tie-break stream so
                # replay is deterministic.
                rng = self.rng_pool.stream(
                    STREAM_ACHIEVEMENT_TIE_BREAK
                )
                slot.awarded_to = rng.choice(
                    sorted(slot.party_members)
                )
                slot.final_action = LotAction.RECEIVE
            else:  # DISCARD
                slot.awarded_to = None
                slot.final_action = LotAction.EXPIRED


__all__ = [
    "DEFAULT_WINDOW_SECONDS",
    "LOT_MIN", "LOT_MAX",
    "LotAction", "ExpirePolicy",
    "LotEntry", "TreasureSlot",
    "LotResult", "AllocationResult",
    "TreasurePool",
]
