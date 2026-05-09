"""Player sentence record — public roll of penalties imposed.

After a court rules against a defendant, the presiding
justice imposes a sentence: a Penalty (FINE / RESTITUTION /
PUBLIC_SHAMING / BANISHMENT) with associated parameters.
Sentences accumulate against a defendant in the public
record. Fines and restitution can be PAID; banishment runs
for a fixed term and lifts automatically; public_shaming
expires on a fixed day. Pardons by an authorized pardoner
forgive an outstanding sentence.

Lifecycle (sentence)
    OUTSTANDING    not yet paid / served / lifted
    PAID           gil component remitted
    LIFTED         banishment / shaming term expired
    PARDONED       authority forgave it

Public surface
--------------
    SentenceState enum
    Penalty enum
    Sentence dataclass (frozen)
    PlayerSentenceRecordSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SentenceState(str, enum.Enum):
    OUTSTANDING = "outstanding"
    PAID = "paid"
    LIFTED = "lifted"
    PARDONED = "pardoned"


class Penalty(str, enum.Enum):
    FINE = "fine"
    RESTITUTION = "restitution"
    PUBLIC_SHAMING = "public_shaming"
    BANISHMENT = "banishment"


@dataclasses.dataclass(frozen=True)
class Sentence:
    sentence_id: str
    lawsuit_id: str
    defendant_id: str
    presiding_justice_id: str
    penalty: Penalty
    amount_gil: int           # for FINE/RESTITUTION
    expiry_day: int           # for SHAMING/BANISHMENT
    payable_to_id: str        # for RESTITUTION
    state: SentenceState
    imposed_day: int


@dataclasses.dataclass
class PlayerSentenceRecordSystem:
    _sentences: dict[str, Sentence] = (
        dataclasses.field(default_factory=dict)
    )
    _next: int = 1

    def impose(
        self, *, lawsuit_id: str,
        defendant_id: str,
        presiding_justice_id: str,
        penalty: Penalty,
        imposed_day: int,
        amount_gil: int = 0,
        expiry_day: int = 0,
        payable_to_id: str = "",
    ) -> t.Optional[str]:
        if not lawsuit_id or not defendant_id:
            return None
        if not presiding_justice_id:
            return None
        if presiding_justice_id == defendant_id:
            return None
        if imposed_day < 0:
            return None
        if penalty in (
            Penalty.FINE, Penalty.RESTITUTION,
        ):
            if amount_gil <= 0:
                return None
        if penalty == Penalty.RESTITUTION:
            if not payable_to_id:
                return None
            if payable_to_id == defendant_id:
                return None
        if penalty in (
            Penalty.PUBLIC_SHAMING,
            Penalty.BANISHMENT,
        ):
            if expiry_day <= imposed_day:
                return None
        sid = f"sent_{self._next}"
        self._next += 1
        self._sentences[sid] = Sentence(
            sentence_id=sid, lawsuit_id=lawsuit_id,
            defendant_id=defendant_id,
            presiding_justice_id=(
                presiding_justice_id
            ),
            penalty=penalty,
            amount_gil=amount_gil,
            expiry_day=expiry_day,
            payable_to_id=payable_to_id,
            state=SentenceState.OUTSTANDING,
            imposed_day=imposed_day,
        )
        return sid

    def pay(
        self, *, sentence_id: str,
        defendant_id: str,
    ) -> bool:
        if sentence_id not in self._sentences:
            return False
        s = self._sentences[sentence_id]
        if s.state != SentenceState.OUTSTANDING:
            return False
        if s.defendant_id != defendant_id:
            return False
        if s.penalty not in (
            Penalty.FINE, Penalty.RESTITUTION,
        ):
            return False
        self._sentences[sentence_id] = (
            dataclasses.replace(
                s, state=SentenceState.PAID,
            )
        )
        return True

    def check_expiry(
        self, *, sentence_id: str, current_day: int,
    ) -> bool:
        """Auto-lift banishment / shaming if expired."""
        if sentence_id not in self._sentences:
            return False
        s = self._sentences[sentence_id]
        if s.state != SentenceState.OUTSTANDING:
            return False
        if s.penalty not in (
            Penalty.PUBLIC_SHAMING,
            Penalty.BANISHMENT,
        ):
            return False
        if current_day < s.expiry_day:
            return False
        self._sentences[sentence_id] = (
            dataclasses.replace(
                s, state=SentenceState.LIFTED,
            )
        )
        return True

    def pardon(
        self, *, sentence_id: str,
        pardoner_id: str,
    ) -> bool:
        """Authority pardons an outstanding sentence."""
        if sentence_id not in self._sentences:
            return False
        s = self._sentences[sentence_id]
        if s.state != SentenceState.OUTSTANDING:
            return False
        if not pardoner_id:
            return False
        if pardoner_id == s.defendant_id:
            return False
        self._sentences[sentence_id] = (
            dataclasses.replace(
                s, state=SentenceState.PARDONED,
            )
        )
        return True

    def sentence(
        self, *, sentence_id: str,
    ) -> t.Optional[Sentence]:
        return self._sentences.get(sentence_id)

    def sentences_against(
        self, *, defendant_id: str,
    ) -> list[Sentence]:
        return [
            s for s in self._sentences.values()
            if s.defendant_id == defendant_id
        ]

    def outstanding_against(
        self, *, defendant_id: str,
    ) -> list[Sentence]:
        return [
            s for s in self._sentences.values()
            if (
                s.defendant_id == defendant_id
                and s.state == SentenceState.OUTSTANDING
            )
        ]

    def is_currently_banished(
        self, *, defendant_id: str, current_day: int,
    ) -> bool:
        for s in self._sentences.values():
            if (
                s.defendant_id == defendant_id
                and s.penalty == Penalty.BANISHMENT
                and s.state == SentenceState.OUTSTANDING
                and current_day < s.expiry_day
            ):
                return True
        return False


__all__ = [
    "SentenceState", "Penalty", "Sentence",
    "PlayerSentenceRecordSystem",
]
