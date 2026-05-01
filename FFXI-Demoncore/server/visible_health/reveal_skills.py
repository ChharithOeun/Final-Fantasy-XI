"""Reveal-skill catalog — the canonical FFXI reveal mechanics.

Per VISUAL_HEALTH_SYSTEM.md the user requested 'we use existing
FFXI skills, not invent new ones'. This module names the 11 reveal
mechanics the doc describes and exposes their tuning anchors.

The actual grant + expire lifecycle lives in reveal_handle.py;
this module is the static catalog the combat pipeline reads.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RevealKind(str, enum.Enum):
    """What information the reveal exposes."""
    HP_NUMERIC = "hp_numeric"        # exact HP and HP_max
    HP_AND_MP_NUMERIC = "hp_and_mp_numeric"  # both
    MP_NUMERIC = "mp_numeric"
    PARTY_HP_NUMERIC = "party_hp_numeric"
    PARTY_HP_AND_MP_NUMERIC = "party_hp_and_mp_numeric"
    DESCRIPTOR_ONLY = "descriptor_only"   # /check, vague
    PARTY_STAGE_SUMMARY = "party_stage_summary"   # /pol
    SURFACE_STAGE_LESS_PRECISE = "surface_stage_less_precise"


class RevealScope(str, enum.Enum):
    """Who sees the reveal."""
    CASTER_ONLY = "caster_only"
    PARTY = "party"
    SELF = "self"


@dataclasses.dataclass(frozen=True)
class RevealSkill:
    """One row of the doc's reveal-skill catalog."""
    skill_id: str
    label: str
    job_or_command: str            # 'all' / 'BLU+SCH' / 'BLM+RDM+SCH' / etc.
    kind: RevealKind
    scope: RevealScope
    duration_seconds: float        # how long the reveal lasts
    cooldown_seconds: float
    mp_cost: int = 0
    proc_chance: float = 1.0       # Mug 30%
    notes: str = ""


REVEAL_SKILLS: dict[str, RevealSkill] = {
    "check": RevealSkill(
        skill_id="check", label="/check",
        job_or_command="all",
        kind=RevealKind.DESCRIPTOR_ONLY,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=0.0,           # one-shot read
        cooldown_seconds=5.0,
        notes=("vague descriptor + mood read + damage read; no numbers"),
    ),
    "scan": RevealSkill(
        skill_id="scan", label="Scan",
        job_or_command="BLU60_SCH40",
        kind=RevealKind.HP_AND_MP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=5.0,
        cooldown_seconds=30.0,
        mp_cost=25,
        notes="exact HP and MP for 5 seconds",
    ),
    "drain": RevealSkill(
        skill_id="drain", label="Drain",
        job_or_command="BLM_RDM_DRK",
        kind=RevealKind.HP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        # Doc: 'while casting and for 2 seconds after the spell lands'
        # The cast-time component is added by the caller; we record
        # only the post-land window here.
        duration_seconds=2.0,
        cooldown_seconds=30.0,
        notes="HP read during cast + 2s post-land",
    ),
    "aspir": RevealSkill(
        skill_id="aspir", label="Aspir",
        job_or_command="BLM_RDM_SCH",
        kind=RevealKind.MP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=2.0,
        cooldown_seconds=30.0,
        notes="MP read during cast + 2s post-land",
    ),
    "mug": RevealSkill(
        skill_id="mug", label="Mug",
        job_or_command="THF25",
        kind=RevealKind.HP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=3.0,
        cooldown_seconds=60.0,
        proc_chance=0.30,           # 30% chance per the doc
        notes="30%% reveal HP for 3s; SA-Mug guarantees the reveal",
    ),
    "glee_tango": RevealSkill(
        skill_id="glee_tango", label="Glee Tango",
        job_or_command="BRD",
        kind=RevealKind.PARTY_HP_AND_MP_NUMERIC,
        scope=RevealScope.PARTY,
        duration_seconds=180.0,         # 3 minutes
        cooldown_seconds=10.0,
        mp_cost=30,
        notes="party HP/MP visible while song active; doesn't reveal "
                "enemies",
    ),
    "cure_target_peek": RevealSkill(
        skill_id="cure_target_peek", label="Cure (peek)",
        job_or_command="WHM_RDM_SCH",
        kind=RevealKind.HP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=2.0,
        cooldown_seconds=0.0,           # ungated; cost is the spell
        notes="target HP visible during cast + 2s; allows healers "
                "to 'tap Cure' to peek",
    ),
    "cura_party_peek": RevealSkill(
        skill_id="cura_party_peek", label="Cura (party peek)",
        job_or_command="WHM",
        kind=RevealKind.PARTY_HP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=2.0,
        cooldown_seconds=0.0,
        notes="all party member HP for cast duration",
    ),
    "magic_burst_reveal": RevealSkill(
        skill_id="magic_burst_reveal", label="Magic Burst (reveal)",
        job_or_command="any_caster",
        kind=RevealKind.HP_NUMERIC,
        scope=RevealScope.PARTY,
        duration_seconds=2.0,
        cooldown_seconds=0.0,
        notes="successful MB > 100 dmg reveals target HP to entire "
                "party for 2s",
    ),
    "indicolure_aspir": RevealSkill(
        skill_id="indicolure_aspir", label="Indicolure: Aspir",
        job_or_command="GEO",
        kind=RevealKind.MP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=120.0,
        cooldown_seconds=180.0,
        mp_cost=40,
        notes="passive MP read on a target",
    ),
    "indicolure_drain": RevealSkill(
        skill_id="indicolure_drain", label="Indicolure: Drain",
        job_or_command="GEO",
        kind=RevealKind.HP_NUMERIC,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=120.0,
        cooldown_seconds=180.0,
        mp_cost=40,
        notes="passive HP read on a target",
    ),
    "stoneskin_attacker_read": RevealSkill(
        skill_id="stoneskin_attacker_read", label="Stoneskin (attacker read)",
        job_or_command="WHM_RDM",
        kind=RevealKind.SURFACE_STAGE_LESS_PRECISE,
        scope=RevealScope.SELF,
        duration_seconds=300.0,         # while Stoneskin is active
        cooldown_seconds=0.0,
        notes="while Stoneskin is up, attacker stage read one stage "
                "less precise",
    ),
    "pol_command": RevealSkill(
        skill_id="pol_command", label="/pol",
        job_or_command="all",
        kind=RevealKind.PARTY_STAGE_SUMMARY,
        scope=RevealScope.CASTER_ONLY,
        duration_seconds=0.0,           # one-shot read
        cooldown_seconds=2.0,
        notes="vague party stage summary; '3 pristine 1 wounded 1 broken'",
    ),
}


# Magic-Burst threshold per the doc: 'Successfully magic-bursting
# (>100 burst damage) reveals'.
MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD: int = 100


def get_skill(skill_id: str) -> RevealSkill:
    """Look up a reveal skill. KeyError on unknown."""
    return REVEAL_SKILLS[skill_id]


def is_reveal_skill(skill_id: str) -> bool:
    return skill_id in REVEAL_SKILLS


def magic_burst_grants_reveal(burst_damage: int) -> bool:
    """Does this MB damage qualify the party for the 2s HP reveal?"""
    return burst_damage > MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD


def mug_reveal_proc(*, sneak_attack_active: bool) -> tuple[bool, float]:
    """Resolve Mug's reveal-proc gate.

    Returns (always_reveals, proc_chance). With Sneak Attack the
    reveal is guaranteed (always_reveals=True); otherwise the
    caller rolls against proc_chance=0.30.
    """
    if sneak_attack_active:
        return True, 1.0
    return False, REVEAL_SKILLS["mug"].proc_chance
