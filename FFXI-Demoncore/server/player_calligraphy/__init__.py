"""Player calligraphy — hand-written notes, scrolls, signed maps.

The most personal craft. A player who's mastered
calligraphy can produce: signed greeting cards left
in friends' Mog Houses, treasure maps with their own
ink-marks, scrolls of poetry, and hand-copied books.
Every output bears a SCRIBE_SIGNATURE; collectors
seek out work by famous scribes the way some seek
NM trophies.

Document kinds:
    NOTE              short personal letter
    GREETING_CARD     occasion / festival
    SCROLL_POEM       longer literary piece
    TREASURE_MAP      hand-drawn map with X-marks
    BOUND_BOOK        copy of an existing tome
    PROCLAMATION      formal decree (LS/nation use)

Each document has a craftsmanship_grade derived from
the scribe's skill, ink quality, and effort_minutes.

Public surface
--------------
    DocumentKind enum
    InkQuality enum
    Document dataclass (frozen)
    PlayerCalligraphySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DocumentKind(str, enum.Enum):
    NOTE = "note"
    GREETING_CARD = "greeting_card"
    SCROLL_POEM = "scroll_poem"
    TREASURE_MAP = "treasure_map"
    BOUND_BOOK = "bound_book"
    PROCLAMATION = "proclamation"


class InkQuality(str, enum.Enum):
    POOR = "poor"
    STANDARD = "standard"
    FINE = "fine"
    MASTER = "master"


_INK_BONUS = {
    "poor": -10,
    "standard": 0,
    "fine": 10,
    "master": 25,
}


@dataclasses.dataclass(frozen=True)
class Document:
    document_id: str
    scribe_id: str
    scribe_signature: str
    kind: DocumentKind
    title: str
    body: str
    ink_quality: InkQuality
    effort_minutes: int
    craftsmanship_grade: int  # 0..100
    crafted_day: int
    is_signed_authentic: bool


@dataclasses.dataclass
class PlayerCalligraphySystem:
    _documents: dict[str, Document] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def craft(
        self, *, scribe_id: str,
        scribe_signature: str,
        kind: DocumentKind, title: str,
        body: str, ink_quality: InkQuality,
        effort_minutes: int,
        scribe_skill: int, crafted_day: int,
        is_signed_authentic: bool = True,
    ) -> t.Optional[str]:
        if not scribe_id or not scribe_signature:
            return None
        if not title or not body:
            return None
        if effort_minutes <= 0:
            return None
        if not 0 <= scribe_skill <= 100:
            return None
        if crafted_day < 0:
            return None
        # Grade composition: skill (max 100) +
        # ink bonus (-10..+25) + effort scaling
        # (more time = better quality up to a cap).
        effort_bonus = min(15, effort_minutes // 10)
        grade = (
            scribe_skill
            + _INK_BONUS[ink_quality.value]
            + effort_bonus
        )
        grade = max(0, min(100, grade))
        did = f"doc_{self._next_id}"
        self._next_id += 1
        self._documents[did] = Document(
            document_id=did, scribe_id=scribe_id,
            scribe_signature=scribe_signature,
            kind=kind, title=title, body=body,
            ink_quality=ink_quality,
            effort_minutes=effort_minutes,
            craftsmanship_grade=grade,
            crafted_day=crafted_day,
            is_signed_authentic=is_signed_authentic,
        )
        return did

    def forge(
        self, *, forger_id: str,
        claimed_signature: str, kind: DocumentKind,
        title: str, body: str,
        ink_quality: InkQuality,
        effort_minutes: int,
        forger_skill: int, crafted_day: int,
    ) -> t.Optional[str]:
        """Create an unauthentic document signed
        with someone else's name. is_signed_authentic
        is False; experts can spot it."""
        return self.craft(
            scribe_id=forger_id,
            scribe_signature=claimed_signature,
            kind=kind, title=title, body=body,
            ink_quality=ink_quality,
            effort_minutes=effort_minutes,
            scribe_skill=forger_skill,
            crafted_day=crafted_day,
            is_signed_authentic=False,
        )

    def authenticate(
        self, *, document_id: str,
        appraiser_skill: int,
    ) -> t.Optional[bool]:
        """An appraiser tries to detect forgery.
        Returns True if forgery detected, False if
        confirmed genuine, None if invalid input or
        unknown document. The appraiser succeeds if
        their skill > forgery's craftsmanship_grade
        (genuines always confirm)."""
        if document_id not in self._documents:
            return None
        if not 0 <= appraiser_skill <= 100:
            return None
        d = self._documents[document_id]
        if d.is_signed_authentic:
            return False
        return appraiser_skill > d.craftsmanship_grade

    def document(
        self, *, document_id: str,
    ) -> t.Optional[Document]:
        return self._documents.get(document_id)

    def documents_by_scribe(
        self, *, scribe_id: str,
    ) -> list[Document]:
        return [
            d for d in self._documents.values()
            if d.scribe_id == scribe_id
        ]

    def documents_signed(
        self, *, signature: str,
    ) -> list[Document]:
        return [
            d for d in self._documents.values()
            if d.scribe_signature == signature
        ]

    def famous_works(
        self, *, min_grade: int,
    ) -> list[Document]:
        if min_grade < 0 or min_grade > 100:
            return []
        return sorted(
            (d for d in self._documents.values()
             if (d.craftsmanship_grade >= min_grade
                 and d.is_signed_authentic)),
            key=lambda d: -d.craftsmanship_grade,
        )


__all__ = [
    "DocumentKind", "InkQuality", "Document",
    "PlayerCalligraphySystem",
]
