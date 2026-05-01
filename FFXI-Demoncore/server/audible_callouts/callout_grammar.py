"""Doc-exact callout strings per AUDIBLE_CALLOUTS.md."""
from __future__ import annotations

import enum


class CalloutKind(str, enum.Enum):
    SKILLCHAIN_OPEN = "skillchain_open"
    CHAIN_CLOSE_LV1 = "chain_close_lv1"
    CHAIN_CLOSE_LV2 = "chain_close_lv2"        # Fusion / Distortion / etc.
    LIGHT_OR_DARKNESS = "light_or_darkness"   # Lv3
    MAGIC_BURST_DAMAGE = "mb_damage"
    MAGIC_BURST_AILMENT = "mb_ailment"
    SETUP = "setup"
    GRUNT_FRUSTRATION = "grunt_frustration"


CALLOUT_TEMPLATES: dict[CalloutKind, str] = {
    CalloutKind.SKILLCHAIN_OPEN: "Skillchain open!",
    CalloutKind.CHAIN_CLOSE_LV1: "Closing — {chain}!",
    CalloutKind.CHAIN_CLOSE_LV2: "{chain}!",
    CalloutKind.LIGHT_OR_DARKNESS: "{chain}!",
    CalloutKind.MAGIC_BURST_DAMAGE: "Magic Burst — {spell}!",
    CalloutKind.MAGIC_BURST_AILMENT: "Magic Burst — {spell}!",
    CalloutKind.SETUP: "Setting up — close on me!",
    CalloutKind.GRUNT_FRUSTRATION: "*grunt of frustration*",
}


def skillchain_open_callout() -> str:
    return CALLOUT_TEMPLATES[CalloutKind.SKILLCHAIN_OPEN]


def chain_close_callout(chain_name: str) -> str:
    """Doc: 'Closing — Fusion!' / 'Closing — Distortion!' / 'Gravitation!'."""
    return CALLOUT_TEMPLATES[CalloutKind.CHAIN_CLOSE_LV1].format(
        chain=chain_name)


def light_or_darkness_callout(chain_name: str) -> str:
    """Doc: '**LIGHT!**' / '**DARKNESS!**' (Lv3 chains)."""
    if chain_name.lower() not in ("light", "darkness"):
        raise ValueError(
            f"Lv3 chain must be Light or Darkness; got {chain_name!r}")
    return chain_name.upper() + "!"


def mb_callout(spell_name: str) -> str:
    """Damage MB callout: 'Magic Burst — Fire!' / 'Magic Burst — Blizzard!'."""
    return CALLOUT_TEMPLATES[CalloutKind.MAGIC_BURST_DAMAGE].format(
        spell=spell_name)


def mb_ailment_callout(ailment_name: str) -> str:
    """Ailment-MB callout: 'Magic Burst — Slow!' / '...Bind!'."""
    return CALLOUT_TEMPLATES[CalloutKind.MAGIC_BURST_AILMENT].format(
        spell=ailment_name)


def setup_callout() -> str:
    """Doc: 'Setting up — close on me!'"""
    return CALLOUT_TEMPLATES[CalloutKind.SETUP]
