"""Beastman language barrier — translator quests + speech translation.

A hume reading "Krek krek-krek!" gets random gibberish until
they complete the per-language TRANSLATOR QUEST. After the quest
is done, that listener can read all speech in that language.

Five LanguageKinds match the languages in the playable races
plus VANADIELIAN (the canonical lingua franca that everyone
already understands by default).

Public surface
--------------
    LanguageKind enum
    TranslatorQuestStatus enum
    TranslateResult dataclass
    BeastmanLanguageBarrier
        .declare_native(player_id, language)
        .translator_quest_complete(player_id, language)
        .can_understand(listener_id, speech_language)
        .translate(listener_id, speaker_id, speech, speech_language)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LanguageKind(str, enum.Enum):
    VANADIELIAN = "vanadielian"     # canonical default
    YAGUDIC = "yagudic"
    QUADAVIC = "quadavic"
    SERPENTTONGUE = "serpenttongue"  # Lamia
    ORCISH = "orcish"


# Hume / Elvaan / Mithra / Tarutaru all default to Vanadielian.
# Each beastman race natively speaks one of the four beastman
# languages but learns Vanadielian as their second tongue.
_DEFAULT_NATIVE: dict[str, LanguageKind] = {
    "hume": LanguageKind.VANADIELIAN,
    "elvaan": LanguageKind.VANADIELIAN,
    "mithra": LanguageKind.VANADIELIAN,
    "tarutaru": LanguageKind.VANADIELIAN,
    "yagudo": LanguageKind.YAGUDIC,
    "quadav": LanguageKind.QUADAVIC,
    "lamia": LanguageKind.SERPENTTONGUE,
    "orc": LanguageKind.ORCISH,
}


# Gibberish glyphs by language for the renderer to splash if
# the listener doesn't understand. Deterministic, not random.
_GIBBERISH_BY_LANGUAGE: dict[LanguageKind, str] = {
    LanguageKind.VANADIELIAN: "...",
    LanguageKind.YAGUDIC: "kreek-krek-kraw",
    LanguageKind.QUADAVIC: "thrum-thrum-tok",
    LanguageKind.SERPENTTONGUE: "ssssh-ssss",
    LanguageKind.ORCISH: "grrah-grrr",
}


@dataclasses.dataclass(frozen=True)
class TranslateResult:
    listener_id: str
    speaker_id: str
    rendered_text: str
    is_translated: bool
    is_native: bool


@dataclasses.dataclass
class _ListenerState:
    listener_id: str
    native_language: LanguageKind
    completed_translators: set[LanguageKind] = (
        dataclasses.field(default_factory=set)
    )


@dataclasses.dataclass
class BeastmanLanguageBarrier:
    _states: dict[str, _ListenerState] = dataclasses.field(
        default_factory=dict,
    )

    def declare_native(
        self, *, player_id: str,
        language: LanguageKind,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None:
            st = _ListenerState(
                listener_id=player_id,
                native_language=language,
            )
            self._states[player_id] = st
        else:
            st.native_language = language
        return True

    def declare_native_by_race(
        self, *, player_id: str, race: str,
    ) -> bool:
        race_l = race.lower()
        lang = _DEFAULT_NATIVE.get(race_l)
        if lang is None:
            return False
        return self.declare_native(
            player_id=player_id, language=lang,
        )

    def translator_quest_complete(
        self, *, player_id: str,
        language: LanguageKind,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None:
            return False
        if language == st.native_language:
            return False     # nothing to learn
        if language in st.completed_translators:
            return False
        st.completed_translators.add(language)
        return True

    def can_understand(
        self, *, listener_id: str,
        language: LanguageKind,
    ) -> bool:
        st = self._states.get(listener_id)
        if st is None:
            # An unconfigured listener is conservatively
            # assumed to know Vanadielian only.
            return language == LanguageKind.VANADIELIAN
        if language == st.native_language:
            return True
        # Vanadielian is universally understood by all sentient
        # races (it's the lingua franca).
        if language == LanguageKind.VANADIELIAN:
            return True
        return language in st.completed_translators

    def translate(
        self, *, listener_id: str, speaker_id: str,
        speech: str,
        speech_language: LanguageKind,
    ) -> TranslateResult:
        if not speech:
            return TranslateResult(
                listener_id=listener_id,
                speaker_id=speaker_id,
                rendered_text="",
                is_translated=False,
                is_native=False,
            )
        st = self._states.get(listener_id)
        is_native = (
            st is not None
            and st.native_language == speech_language
        )
        if self.can_understand(
            listener_id=listener_id,
            language=speech_language,
        ):
            return TranslateResult(
                listener_id=listener_id,
                speaker_id=speaker_id,
                rendered_text=speech,
                is_translated=not is_native,
                is_native=is_native,
            )
        # Listener can't understand — render gibberish
        glyph = _GIBBERISH_BY_LANGUAGE.get(
            speech_language, "...",
        )
        # Length-roughly-matching gibberish so it FEELS like
        # someone said something — repeat the glyph a few times
        chunks = max(1, len(speech) // 12)
        rendered = " ".join([glyph] * chunks)
        return TranslateResult(
            listener_id=listener_id,
            speaker_id=speaker_id,
            rendered_text=rendered,
            is_translated=False,
            is_native=False,
        )

    def total_listeners(self) -> int:
        return len(self._states)


__all__ = [
    "LanguageKind",
    "TranslateResult",
    "BeastmanLanguageBarrier",
]
