"""Beastman phrasebook — auto-translate phrase library.

Each beastman race has its own native dialect; the goblin
neutrality treaty also uses a TRADE-PIDGIN that all races can
read. Players use a phrasebook to send tokenized
{auto-translated} phrases that the recipient sees in their own
preferred dialect.

A phrase has:
  - phrase_id (e.g., "greeting_hello")
  - translations dict, keyed by Dialect

A player picks a PREFERRED DIALECT once; outgoing phrases get
encoded in that dialect; receivers see their own preferred
dialect's translation.

Public surface
--------------
    Dialect enum     YAGUDO_TONGUE / QUADAV_TONGUE /
                     LAMIA_TONGUE / ORC_TONGUE / TRADE_PIDGIN
    Phrase dataclass
    BeastmanPhrasebook
        .register_phrase(phrase_id, translations)
        .set_preferred(player_id, dialect)
        .translate(phrase_id, recipient_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Dialect(str, enum.Enum):
    YAGUDO_TONGUE = "yagudo_tongue"
    QUADAV_TONGUE = "quadav_tongue"
    LAMIA_TONGUE = "lamia_tongue"
    ORC_TONGUE = "orc_tongue"
    TRADE_PIDGIN = "trade_pidgin"


@dataclasses.dataclass(frozen=True)
class Phrase:
    phrase_id: str
    translations: dict[Dialect, str]


@dataclasses.dataclass(frozen=True)
class TranslateResult:
    accepted: bool
    phrase_id: str
    text: str = ""
    dialect_used: t.Optional[Dialect] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanPhrasebook:
    _phrases: dict[str, Phrase] = dataclasses.field(default_factory=dict)
    _preferred: dict[str, Dialect] = dataclasses.field(default_factory=dict)

    def register_phrase(
        self, *, phrase_id: str,
        translations: dict[Dialect, str],
    ) -> t.Optional[Phrase]:
        if not phrase_id:
            return None
        if phrase_id in self._phrases:
            return None
        if not translations:
            return None
        for d, text in translations.items():
            if not text:
                return None
        # All phrases must include TRADE_PIDGIN as the fallback
        if Dialect.TRADE_PIDGIN not in translations:
            return None
        p = Phrase(
            phrase_id=phrase_id,
            translations=dict(translations),
        )
        self._phrases[phrase_id] = p
        return p

    def set_preferred(
        self, *, player_id: str, dialect: Dialect,
    ) -> bool:
        if not player_id:
            return False
        self._preferred[player_id] = dialect
        return True

    def preferred_for(
        self, *, player_id: str,
    ) -> Dialect:
        return self._preferred.get(player_id, Dialect.TRADE_PIDGIN)

    def translate(
        self, *, phrase_id: str, recipient_id: str,
    ) -> TranslateResult:
        p = self._phrases.get(phrase_id)
        if p is None:
            return TranslateResult(
                False, phrase_id, reason="unknown phrase",
            )
        pref = self._preferred.get(
            recipient_id, Dialect.TRADE_PIDGIN,
        )
        if pref in p.translations:
            return TranslateResult(
                accepted=True,
                phrase_id=phrase_id,
                text=p.translations[pref],
                dialect_used=pref,
            )
        # Fall back to trade pidgin (always present per registration)
        return TranslateResult(
            accepted=True,
            phrase_id=phrase_id,
            text=p.translations[Dialect.TRADE_PIDGIN],
            dialect_used=Dialect.TRADE_PIDGIN,
        )

    def total_phrases(self) -> int:
        return len(self._phrases)


__all__ = [
    "Dialect", "Phrase", "TranslateResult",
    "BeastmanPhrasebook",
]
