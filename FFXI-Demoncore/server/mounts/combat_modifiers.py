"""Mounted action modifiers.

Per MOUNTS.md combat-while-mounted rules:
    Auto-attack from mount: half normal damage
    Cast spells from mount: full damage but +50% cast time
    Weapon Skills: possible but +25% TP cost
    Cannot use 2hr / Job Master abilities while mounted (too unstable)
    Cannot use Stealth / Sneak / Invisible abilities while mounted
"""
from __future__ import annotations


AUTO_ATTACK_DMG_MULT = 0.50
CAST_TIME_MULT = 1.50
WEAPON_SKILL_TP_COST_MULT = 1.25


class MountedActionModifiers:
    """Static-method modifier resolver for the combat pipeline."""

    @staticmethod
    def auto_attack_dmg_mult() -> float:
        return AUTO_ATTACK_DMG_MULT

    @staticmethod
    def cast_time_mult() -> float:
        return CAST_TIME_MULT

    @staticmethod
    def weapon_skill_tp_cost_mult() -> float:
        return WEAPON_SKILL_TP_COST_MULT

    @staticmethod
    def can_use_two_hour_ability() -> bool:
        """Two-hour / Job Master abilities are blocked while mounted."""
        return False

    @staticmethod
    def can_use_stealth_skill(skill_name: str) -> bool:
        """Stealth / Sneak / Invisible blocked while mounted (more
        visible, not less). Skill_name lowercased; returns False for
        the standard stealth library names."""
        s = skill_name.lower()
        if s in ("sneak", "invisible", "hide", "perfect_dodge", "stealth"):
            return False
        return True

    @staticmethod
    def adjusted_cast_time(base_cast_time: float) -> float:
        if base_cast_time <= 0:
            return 0.0
        return base_cast_time * CAST_TIME_MULT

    @staticmethod
    def adjusted_weapon_skill_tp(base_tp_cost: int) -> int:
        if base_tp_cost <= 0:
            return 0
        return int(round(base_tp_cost * WEAPON_SKILL_TP_COST_MULT))

    @staticmethod
    def adjusted_auto_attack_damage(base_dmg: int) -> int:
        return int(round(base_dmg * AUTO_ATTACK_DMG_MULT))
