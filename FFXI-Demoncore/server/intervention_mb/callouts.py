"""Per-job intervention callouts — voice as combat UI.

Per INTERVENTION_MB.md the audible callouts table:

    Cure intervention lands                  -> "Magic Burst — Cure!"
    Cure on Light chain (5x bonus)           -> "MAGIC BURST — CURE V!"
    Curaga intervention                      -> "Magic Burst — Curaga!"
    -na intervention                         -> "Magic Burst — Paralyna!"
    Erase intervention                       -> "Magic Burst — Erase!"
    Failed (started, didn't land in window)  -> *grunt of frustration*
    RDM enhancing                            -> "Magic Burst — Haste!" / Refresh
    BLM debuff                               -> "Magic Burst — Bio!" / Slow
    BRD song                                 -> "Magic Burst — Mage's Ballad!"
    SCH helix                                -> "Magic Burst — Firestorm Helix!"
    GEO                                      -> "Magic Burst — Indi-Refresh!"
    Tank                                     -> "PROVOKE BURST!" / "FLASH BURST!"
"""
from __future__ import annotations

import dataclasses
import enum

from .amplification import SpellFamily


@dataclasses.dataclass(frozen=True)
class Callout:
    """One voice line tagged with intensity and family."""
    line: str
    family: SpellFamily
    is_light_bonus: bool
    is_failure: bool = False


# Per-family base callouts. Subspell-specific lines get filled in by
# the caller passing `spell_label` (e.g. 'Haste' for RDM enhancing).
_BASE_CALLOUT: dict[SpellFamily, str] = {
    SpellFamily.CURE: "Magic Burst — Cure!",
    SpellFamily.CURAGA: "Magic Burst — Curaga!",
    SpellFamily.NA_SPELL: "Magic Burst — {spell}!",
    SpellFamily.ERASE: "Magic Burst — Erase!",
    SpellFamily.RDM_ENHANCING: "Magic Burst — {spell}!",
    SpellFamily.BLM_DEBUFF: "Magic Burst — {spell}!",
    SpellFamily.BRD_SONG: "Magic Burst — {spell}!",
    SpellFamily.SCH_HELIX: "Magic Burst — {spell}!",
    SpellFamily.GEO_LUOPAN: "Magic Burst — {spell}!",
    SpellFamily.TANK_FLASH: "{spell} BURST!",
}

_LIGHT_CALLOUT: dict[SpellFamily, str] = {
    SpellFamily.CURE: "MAGIC BURST — CURE V!",
    SpellFamily.CURAGA: "MAGIC BURST — CURAGA V!",
    SpellFamily.NA_SPELL: "MAGIC BURST — {spell}!",
    SpellFamily.ERASE: "MAGIC BURST — ERASE!",
    SpellFamily.RDM_ENHANCING: "MAGIC BURST — {spell}!",
    SpellFamily.BLM_DEBUFF: "MAGIC BURST — {spell}!",
    SpellFamily.BRD_SONG: "MAGIC BURST — {spell}!",
    SpellFamily.SCH_HELIX: "MAGIC BURST — {spell}!",
    SpellFamily.GEO_LUOPAN: "LUOPAN BURST!",
    SpellFamily.TANK_FLASH: "{spell} BURST!",
}


# Mob-side intervention callouts use a per-class voice. We expose a
# single string template; the voice pipeline maps it to the mob's
# cloned voice id.
def mob_intervention_callout(*,
                                  mob_class: str,
                                  family: SpellFamily,
                                  light_bonus: bool) -> str:
    """Generate a mob-side intervention shout.

    Doc: 'A Quadav Healer shouts "[gruff Quadav speech] Cure burst!"
    in their canonical mob voice'.
    """
    family_label = family.value.replace("_", " ").title()
    if light_bonus:
        return f"[{mob_class} voice] {family_label.upper()} BURST!"
    return f"[{mob_class} voice] {family_label} burst!"


def callout_for(*,
                  family: SpellFamily,
                  light_bonus: bool,
                  spell_label: str = "") -> Callout:
    """Build the player-side callout for a successful intervention."""
    template = (_LIGHT_CALLOUT if light_bonus
                  else _BASE_CALLOUT).get(family, "Magic Burst!")
    line = template.format(spell=spell_label or family.value.title())
    return Callout(line=line, family=family,
                       is_light_bonus=light_bonus)


def failure_grunt(family: SpellFamily) -> Callout:
    """A spell that started but didn't land in window — frustration."""
    return Callout(
        line="*grunt of frustration*",
        family=family,
        is_light_bonus=False,
        is_failure=True,
    )
