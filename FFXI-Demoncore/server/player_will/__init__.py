"""Player will — bequest items on permadeath.

Permadeath in Demoncore is real. A player who plans
ahead can write a WILL: a list of named heirs and
which items go to whom. On permadeath, the will is
EXECUTED — items move via delivery_box (caller-routed)
to each heir.

A will:
    will_id, testator_id, named_heirs (set),
    bequests (item_id -> heir_id), residue_heir
    (catches everything not specifically bequeathed),
    drafted_day, executed_day, state.

States:
    DRAFT       editable
    SEALED      locked (cannot be modified, only the
                testator can seal/unseal — until
                permadeath)
    EXECUTED    distributed at permadeath
    REVOKED     replaced by a new will

Public surface
--------------
    WillState enum
    Bequest dataclass (frozen)
    Will dataclass (frozen)
    PlayerWillSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WillState(str, enum.Enum):
    DRAFT = "draft"
    SEALED = "sealed"
    EXECUTED = "executed"
    REVOKED = "revoked"


@dataclasses.dataclass(frozen=True)
class Bequest:
    item_id: str
    heir_id: str


@dataclasses.dataclass(frozen=True)
class Will:
    will_id: str
    testator_id: str
    bequests: tuple[Bequest, ...]
    residue_heir: str
    drafted_day: int
    sealed_day: t.Optional[int]
    executed_day: t.Optional[int]
    state: WillState


@dataclasses.dataclass
class PlayerWillSystem:
    _wills: dict[str, Will] = dataclasses.field(
        default_factory=dict,
    )
    _active_will: dict[str, str] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def draft(
        self, *, testator_id: str,
        residue_heir: str, drafted_day: int,
    ) -> t.Optional[str]:
        if not testator_id or not residue_heir:
            return None
        if testator_id == residue_heir:
            return None
        if drafted_day < 0:
            return None
        # Block parallel DRAFT/SEALED active wills
        active_id = self._active_will.get(testator_id)
        if active_id is not None:
            cur = self._wills[active_id]
            if cur.state in (
                WillState.DRAFT, WillState.SEALED,
            ):
                return None
        wid = f"will_{self._next_id}"
        self._next_id += 1
        self._wills[wid] = Will(
            will_id=wid, testator_id=testator_id,
            bequests=(), residue_heir=residue_heir,
            drafted_day=drafted_day,
            sealed_day=None, executed_day=None,
            state=WillState.DRAFT,
        )
        self._active_will[testator_id] = wid
        return wid

    def add_bequest(
        self, *, will_id: str, item_id: str,
        heir_id: str,
    ) -> bool:
        if will_id not in self._wills:
            return False
        if not item_id or not heir_id:
            return False
        w = self._wills[will_id]
        if w.state != WillState.DRAFT:
            return False
        if heir_id == w.testator_id:
            return False
        # Block duplicate item_id
        if any(
            b.item_id == item_id
            for b in w.bequests
        ):
            return False
        new_bequests = w.bequests + (Bequest(
            item_id=item_id, heir_id=heir_id,
        ),)
        self._wills[will_id] = dataclasses.replace(
            w, bequests=new_bequests,
        )
        return True

    def remove_bequest(
        self, *, will_id: str, item_id: str,
    ) -> bool:
        if will_id not in self._wills:
            return False
        w = self._wills[will_id]
        if w.state != WillState.DRAFT:
            return False
        if not any(
            b.item_id == item_id
            for b in w.bequests
        ):
            return False
        new_bequests = tuple(
            b for b in w.bequests
            if b.item_id != item_id
        )
        self._wills[will_id] = dataclasses.replace(
            w, bequests=new_bequests,
        )
        return True

    def seal(
        self, *, will_id: str, now_day: int,
    ) -> bool:
        if will_id not in self._wills:
            return False
        w = self._wills[will_id]
        if w.state != WillState.DRAFT:
            return False
        if now_day < w.drafted_day:
            return False
        self._wills[will_id] = dataclasses.replace(
            w, state=WillState.SEALED,
            sealed_day=now_day,
        )
        return True

    def unseal(
        self, *, will_id: str,
    ) -> bool:
        if will_id not in self._wills:
            return False
        w = self._wills[will_id]
        if w.state != WillState.SEALED:
            return False
        self._wills[will_id] = dataclasses.replace(
            w, state=WillState.DRAFT,
            sealed_day=None,
        )
        return True

    def revoke(
        self, *, will_id: str, now_day: int,
    ) -> bool:
        if will_id not in self._wills:
            return False
        w = self._wills[will_id]
        if w.state not in (
            WillState.DRAFT, WillState.SEALED,
        ):
            return False
        self._wills[will_id] = dataclasses.replace(
            w, state=WillState.REVOKED,
        )
        if (self._active_will.get(w.testator_id)
                == will_id):
            self._active_will.pop(w.testator_id)
        return True

    def execute(
        self, *, testator_id: str, now_day: int,
        owned_items: t.Sequence[str],
    ) -> t.Optional[dict[str, list[str]]]:
        """Execute the active SEALED will. Returns
        a heir_id -> list[item_id] distribution
        (named bequests honored if testator owns
        the item, otherwise dropped; residue_heir
        gets everything else owned).
        """
        wid = self._active_will.get(testator_id)
        if wid is None:
            return None
        w = self._wills[wid]
        if w.state != WillState.SEALED:
            return None
        owned = set(owned_items)
        distribution: dict[str, list[str]] = {}
        residue: list[str] = []
        for b in w.bequests:
            if b.item_id in owned:
                distribution.setdefault(
                    b.heir_id, [],
                ).append(b.item_id)
                owned.remove(b.item_id)
        # Anything left -> residue_heir
        residue = sorted(owned)
        if residue:
            distribution.setdefault(
                w.residue_heir, [],
            ).extend(residue)
        self._wills[wid] = dataclasses.replace(
            w, state=WillState.EXECUTED,
            executed_day=now_day,
        )
        self._active_will.pop(testator_id, None)
        return distribution

    def active_will(
        self, *, testator_id: str,
    ) -> t.Optional[Will]:
        wid = self._active_will.get(testator_id)
        if wid is None:
            return None
        return self._wills[wid]

    def will(
        self, *, will_id: str,
    ) -> t.Optional[Will]:
        return self._wills.get(will_id)

    def history_for(
        self, *, testator_id: str,
    ) -> list[Will]:
        return sorted(
            (w for w in self._wills.values()
             if w.testator_id == testator_id),
            key=lambda w: w.drafted_day,
        )


__all__ = [
    "WillState", "Bequest", "Will",
    "PlayerWillSystem",
]
