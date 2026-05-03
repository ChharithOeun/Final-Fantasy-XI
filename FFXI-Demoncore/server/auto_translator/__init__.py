"""Auto-Translator — {Hello.} {Friend.} multilingual chat.

The signature FFXI feature: a player typing `{Hello.}` in their
locale sends a message that renders as "{Hello.}" but displays
in each recipient's preferred language. This module is the
catalog + lookup that the chat router consults when a curly-
brace token is detected in a message.

Five locales: EN, JP, DE, FR, ES.

Public surface
--------------
    Locale enum
    AutoTranslateTerm dataclass
    AT_CATALOG / lookup_term(token)
    render_for(token, locale) -> str
    parse_message(message) -> tuple[(token, raw_text), ...]
        — splits a message into AT tokens and freeform spans
"""
from __future__ import annotations

import dataclasses
import enum
import re
import typing as t


class Locale(str, enum.Enum):
    EN = "en"
    JP = "jp"
    DE = "de"
    FR = "fr"
    ES = "es"


@dataclasses.dataclass(frozen=True)
class AutoTranslateTerm:
    token: str                 # canonical key, e.g. "Hello."
    translations: dict[Locale, str]


def _t(token: str, en: str, jp: str, de: str, fr: str, es: str) -> AutoTranslateTerm:
    return AutoTranslateTerm(token=token, translations={
        Locale.EN: en, Locale.JP: jp, Locale.DE: de,
        Locale.FR: fr, Locale.ES: es,
    })


# Sample slice of canonical FFXI auto-translate terms
AT_CATALOG: dict[str, AutoTranslateTerm] = {
    "Hello.": _t("Hello.",
                  "Hello.", "こんにちは。", "Hallo.",
                  "Bonjour.", "Hola."),
    "Goodbye.": _t("Goodbye.",
                    "Goodbye.", "さようなら。", "Auf Wiedersehen.",
                    "Au revoir.", "Adiós."),
    "Yes.": _t("Yes.",
                "Yes.", "はい。", "Ja.", "Oui.", "Sí."),
    "No.": _t("No.",
               "No.", "いいえ。", "Nein.", "Non.", "No."),
    "Thank you.": _t("Thank you.",
                      "Thank you.", "ありがとう。", "Danke.",
                      "Merci.", "Gracias."),
    "Friend": _t("Friend",
                  "Friend", "友達", "Freund", "Ami", "Amigo"),
    "Looking for party.": _t(
        "Looking for party.",
        "Looking for party.", "パーティ募集中。",
        "Suche Gruppe.",
        "Recherche groupe.", "Buscando grupo."),
    "Looking for members.": _t(
        "Looking for members.",
        "Looking for members.", "メンバー募集中。",
        "Suche Mitglieder.",
        "Recherche membres.", "Buscando miembros."),
    "I'm new!": _t("I'm new!",
                    "I'm new!", "新人です！", "Ich bin neu!",
                    "Je suis nouveau !", "¡Soy nuevo!"),
    "Mentor": _t("Mentor",
                  "Mentor", "メンター", "Mentor",
                  "Mentor", "Mentor"),
    "Black Mage": _t("Black Mage",
                      "Black Mage", "黒魔道士", "Schwarzmagier",
                      "Mage Noir", "Mago Negro"),
    "White Mage": _t("White Mage",
                      "White Mage", "白魔道士", "Weißmagier",
                      "Mage Blanc", "Mago Blanco"),
    "Tank": _t("Tank",
                "Tank", "タンク", "Tank", "Tank", "Tanque"),
    "Healer": _t("Healer",
                  "Healer", "回復役", "Heiler",
                  "Soigneur", "Sanador"),
}


def lookup_term(token: str) -> t.Optional[AutoTranslateTerm]:
    return AT_CATALOG.get(token)


def render_for(*, token: str, locale: Locale) -> str:
    """Render a canonical token in the recipient's locale. Falls
    back to the token itself if missing in the catalog."""
    term = AT_CATALOG.get(token)
    if term is None:
        return f"{{{token}}}"
    return term.translations.get(locale, term.translations[Locale.EN])


_TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")


def parse_message(*, message: str
                   ) -> tuple[tuple[bool, str], ...]:
    """Split a message into (is_at_token, content) spans.

    Example:
        parse_message("Hi {Friend} {Hello.}, want to {Looking for party.}?")
        -> [
            (False, "Hi "),
            (True, "Friend"),
            (False, " "),
            (True, "Hello."),
            (False, ", want to "),
            (True, "Looking for party."),
            (False, "?"),
           ]
    """
    out: list[tuple[bool, str]] = []
    pos = 0
    for match in _TOKEN_PATTERN.finditer(message):
        if match.start() > pos:
            out.append((False, message[pos:match.start()]))
        out.append((True, match.group(1)))
        pos = match.end()
    if pos < len(message):
        out.append((False, message[pos:]))
    return tuple(out)


def render_message(*, message: str, locale: Locale) -> str:
    """Walk the parsed message and render AT tokens in the locale,
    leaving freeform spans untouched."""
    parts: list[str] = []
    for is_token, content in parse_message(message=message):
        if is_token:
            parts.append(render_for(token=content, locale=locale))
        else:
            parts.append(content)
    return "".join(parts)


__all__ = [
    "Locale", "AutoTranslateTerm", "AT_CATALOG",
    "lookup_term", "render_for",
    "parse_message", "render_message",
]
