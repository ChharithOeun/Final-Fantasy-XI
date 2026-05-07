"""GearSwap signature — author motto + flair on every
published lua.

Famous players develop a brand. Chharith's RDM lua isn't
just "rdm_chharith"; it's "rdm_chharith — *speed kills*"
with a small RDM-themed glyph. This module gives every
published author a personalized signature panel:

    motto         a short signature line, ≤ 60 chars
    glyph         one of N preset symbols (job-themed
                  + neutral) — the gallery card renders
                  this next to the author display name
    accent_color  one of M curated palette entries
                  (no #FF00FF eye-bleed; we constrain
                  to a tasteful set)

Authors edit their signature once per cooldown (24h) so
the brand stays stable — you can't gold-rush flair
changes to spam the trending tab. The cooldown resets
fresh authors with no signature history (so a brand-new
mentor can pick their first signature immediately).

The signature attaches to the AUTHOR, not per-publish.
All Chharith's published luas share one signature panel.
That's intentional — a famous mentor wants brand
consistency across builds.

Public surface
--------------
    Glyph enum        16 preset glyphs
    AccentColor enum  10 curated colors
    Signature dataclass (frozen)
    GearswapSignature
        .set_signature(author_id, motto, glyph,
                       accent_color, now) -> bool
        .get_signature(author_id) -> Optional[Signature]
        .can_edit(author_id, now) -> bool
        .seconds_until_can_edit(author_id, now) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MOTTO_MAX = 60
_EDIT_COOLDOWN_SEC = 86400


class Glyph(str, enum.Enum):
    NONE = "none"
    SWORD = "sword"
    STAFF = "staff"
    BOW = "bow"
    DAGGER = "dagger"
    SHIELD = "shield"
    BOOK = "book"
    FLAME = "flame"
    SNOWFLAKE = "snowflake"
    LEAF = "leaf"
    CROWN = "crown"
    STAR = "star"
    MOON = "moon"
    ANVIL = "anvil"
    LUTE = "lute"
    SCALES = "scales"


class AccentColor(str, enum.Enum):
    SLATE = "slate"
    CRIMSON = "crimson"
    AMBER = "amber"
    EMERALD = "emerald"
    SAPPHIRE = "sapphire"
    VIOLET = "violet"
    ROSE = "rose"
    TEAL = "teal"
    BRONZE = "bronze"
    SILVER = "silver"


@dataclasses.dataclass(frozen=True)
class Signature:
    author_id: str
    motto: str
    glyph: Glyph
    accent_color: AccentColor
    last_edited_at: int


@dataclasses.dataclass
class GearswapSignature:
    _signatures: dict[
        str, Signature,
    ] = dataclasses.field(default_factory=dict)

    def can_edit(
        self, *, author_id: str, now: int,
    ) -> bool:
        cur = self._signatures.get(author_id)
        if cur is None:
            return True   # never set; free initial pick
        return (now - cur.last_edited_at) >= _EDIT_COOLDOWN_SEC

    def seconds_until_can_edit(
        self, *, author_id: str, now: int,
    ) -> int:
        cur = self._signatures.get(author_id)
        if cur is None:
            return 0
        elapsed = now - cur.last_edited_at
        if elapsed >= _EDIT_COOLDOWN_SEC:
            return 0
        return _EDIT_COOLDOWN_SEC - elapsed

    def set_signature(
        self, *, author_id: str, motto: str,
        glyph: Glyph, accent_color: AccentColor,
        now: int,
    ) -> bool:
        if not author_id:
            return False
        motto = motto.strip()
        if len(motto) > _MOTTO_MAX:
            return False
        if not self.can_edit(author_id=author_id, now=now):
            return False
        self._signatures[author_id] = Signature(
            author_id=author_id, motto=motto,
            glyph=glyph, accent_color=accent_color,
            last_edited_at=now,
        )
        return True

    def get_signature(
        self, *, author_id: str,
    ) -> t.Optional[Signature]:
        return self._signatures.get(author_id)

    def total_signatures(self) -> int:
        return len(self._signatures)

    @staticmethod
    def glyph_count() -> int:
        return len(list(Glyph))

    @staticmethod
    def color_count() -> int:
        return len(list(AccentColor))


__all__ = [
    "Glyph", "AccentColor", "Signature", "GearswapSignature",
]
