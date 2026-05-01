"""Hidden automaton synergies — head/frame/maneuver combinations.

The big idea
------------
PUP players have always lived between optimal "matched" builds
(Spiritreaver head + Spiritreaver frame for nuker; Sharpshot/
Sharpshot for ranger; etc). Demoncore rewards CROSS-ROLE
experimentation: combine a non-canonical head + frame, run the
right 3-maneuver pattern, and the automaton unlocks a HIDDEN
ability. The ability fires for a duration, then locks behind a
long cooldown so it can't be spammed.

Each synergy specifies:
  - head           which automaton head must be installed
  - frame          which automaton frame must be installed
  - maneuver_req   which 3 maneuvers must be active (counts of
                       each element)
  - effect_kind    rough category (AOE buff, party heal, debuff,
                       single-target nuke, ability unlock, etc.)
  - effect_payload free-form dict the effect applicator interprets
  - duration_seconds  how long the ability runs (0 = instant)
  - cooldown_seconds  how long until it can fire again
  - aoe_radius_yalms  18 for canonical PUP party AOE; 0 for self
                          or single-target

The 5 user-defined synergies are pinned by name in the test
suite as DESIGNATED_FOUNDERS — those entries cannot be removed
without an explicit doctrine change.

Effects are payload-shaped, not hard-coded. The activation
layer hands the matched ability + payload off to the broader
effect system (mood event hooks, magic-burst trigger, etc.).

Note on heads/frames
--------------------
Demoncore extends classic PUP's six heads/frames with two more
(RDM and NIN), giving an 8x8 pairing matrix. Many crossings have
no synergy — players experimenting will hit dead ends — but the
ones that DO work feel like discoveries. The catalog covers ~25
entries, leaving the rest as untouched soil for future entries.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.automaton_attachments import Maneuver as ManeuverElement


# -- Heads & Frames ----------------------------------------------

class Head(str, enum.Enum):
    """Automaton head — drives spell/ability selection."""
    HARLEQUIN = "harlequin"        # basic, balanced
    VALOREDGE = "valoredge"        # tank/melee
    SHARPSHOT = "sharpshot"        # ranged DD
    STORMWAKER = "stormwaker"      # BLM elemental
    SOULSOOTHER = "soulsoother"    # WHM healer
    SPIRITREAVER = "spiritreaver"  # BLM dark/necromancer
    RDM = "rdm"                    # Red Mage hybrid (Demoncore +)
    NIN = "nin"                    # Ninja-styled (Demoncore +)


class Frame(str, enum.Enum):
    """Automaton frame — drives stat profile + animations."""
    HARLEQUIN = "harlequin"
    VALOREDGE = "valoredge"
    SHARPSHOT = "sharpshot"
    STORMWAKER = "stormwaker"
    SOULSOOTHER = "soulsoother"
    SPIRITREAVER = "spiritreaver"
    RDM = "rdm"
    NIN = "nin"


# -- Effect kinds ------------------------------------------------

class EffectKind(str, enum.Enum):
    """Rough category. Used by the effect applicator to dispatch."""
    SELF_BUFF              = "self_buff"
    PARTY_BUFF             = "party_buff"
    AOE_HEAL               = "aoe_heal"
    AOE_DAMAGE             = "aoe_damage"
    AOE_DEBUFF             = "aoe_debuff"
    AOE_DOT                = "aoe_dot"
    AOE_PROTECTION         = "aoe_protection"
    AOE_RESURRECTION       = "aoe_resurrection"
    AOE_UTILITY            = "aoe_utility"
    SINGLE_TARGET_DAMAGE   = "single_target_damage"
    UNLOCK_ABILITIES       = "unlock_abilities"


# Standard PUP party AOE radius in retail. Synergies override
# only when the design demands a different scale.
AOE_RADIUS_PARTY_YALMS = 18.0


# -- SynergyAbility dataclass ------------------------------------

@dataclasses.dataclass(frozen=True)
class SynergyAbility:
    """One unlocked head+frame+maneuver combination."""
    ability_id: str
    name: str
    description: str
    head: Head
    frame: Frame
    maneuver_req: tuple[tuple[ManeuverElement, int], ...]
    effect_kind: EffectKind
    effect_payload: tuple[tuple[str, t.Any], ...] = ()
    duration_seconds: int = 0      # 0 = instant
    cooldown_seconds: int = 0
    aoe_radius_yalms: float = AOE_RADIUS_PARTY_YALMS

    # Convenience: the maneuver requirement as a dict.
    @property
    def maneuver_req_map(self) -> dict[ManeuverElement, int]:
        return dict(self.maneuver_req)

    @property
    def total_maneuvers_required(self) -> int:
        return sum(count for _, count in self.maneuver_req)


# Helper: shorthand for "3 of one element"
def _three_of(element: ManeuverElement) -> tuple[
    tuple[ManeuverElement, int], ...
]:
    return ((element, 3),)


# -- Catalog -----------------------------------------------------

# The five user-pinned founders. These cannot be removed without
# a deliberate doctrine update; the test suite asserts presence.
DESIGNATED_FOUNDER_IDS: frozenset[str] = frozenset({
    "death_spikes",
    "aoe_stoneskin",
    "aoe_reraise_1",
    "aoe_corsair_roll_eleven",
    "dnc_unlock",
})


SYNERGY_CATALOG: tuple[SynergyAbility, ...] = (
    # ============== USER-DEFINED FOUNDERS (5) ==============
    SynergyAbility(
        ability_id="death_spikes",
        name="Death Spikes",
        description=(
            "Necromantic spikes radiate from the automaton; melee "
            "attackers take percent-based damage on contact."
        ),
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.SELF_BUFF,
        effect_payload=(
            ("spike_damage_pct", 8.0),
            ("spike_trigger", "on_attack_received"),
        ),
        duration_seconds=30,
        cooldown_seconds=900,            # 15 min
        aoe_radius_yalms=0.0,            # self only
    ),
    SynergyAbility(
        ability_id="aoe_stoneskin",
        name="Resonant Stoneskin",
        description=(
            "All party members within 18 yalms gain a layer of "
            "Stoneskin equal to the master's MP-derived ceiling."
        ),
        head=Head.RDM, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.EARTH),
        effect_kind=EffectKind.AOE_PROTECTION,
        effect_payload=(
            ("absorb_formula", "stoneskin_master_mp"),
            ("trigger_on_apply", True),
        ),
        duration_seconds=0,              # consumed on hit
        cooldown_seconds=180,            # 3 min
    ),
    SynergyAbility(
        ability_id="aoe_reraise_1",
        name="Soul Soother's Refrain",
        description=(
            "All party members within 18 yalms gain Reraise I."
        ),
        head=Head.SOULSOOTHER, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.AOE_RESURRECTION,
        effect_payload=(
            ("reraise_tier", 1),
            ("on_resurrect_hp_pct", 25.0),
        ),
        duration_seconds=0,              # persists until consumed
        cooldown_seconds=900,            # 15 min
    ),
    SynergyAbility(
        ability_id="aoe_corsair_roll_eleven",
        name="Phantom Roll: Eleven",
        description=(
            "The automaton mimics Corsair phantom roll, but the "
            "result is auto-pinned to the optimum 'eleven' result. "
            "Roll choice is the master's pick from the COR roll list."
        ),
        head=Head.NIN, frame=Frame.SHARPSHOT,
        maneuver_req=_three_of(ManeuverElement.WATER),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(
            ("roll_value", 11),
            ("roll_kind", "master_choice"),
        ),
        duration_seconds=180,            # 3 min
        cooldown_seconds=900,            # 15 min
    ),
    SynergyAbility(
        ability_id="dnc_unlock",
        name="Stage Director",
        description=(
            "Unlocks Dancer abilities (steps, flourishes, sambas) "
            "for all party members within 18 yalms. Mixed-element "
            "trigger: 1 ice + 1 earth + 1 water."
        ),
        head=Head.VALOREDGE, frame=Frame.NIN,
        maneuver_req=(
            (ManeuverElement.ICE, 1),
            (ManeuverElement.EARTH, 1),
            (ManeuverElement.WATER, 1),
        ),
        effect_kind=EffectKind.UNLOCK_ABILITIES,
        effect_payload=(
            ("ability_set", "dnc"),
            ("includes", "steps,flourishes,sambas"),
        ),
        duration_seconds=300,            # 5 min
        cooldown_seconds=900,            # 15 min
    ),

    # ============== SPIRITREAVER HEAD (BLM dark) ==============
    SynergyAbility(
        ability_id="necromantic_burn",
        name="Necromantic Burn",
        description="Ranged AoE Fire DoT with shadow-tinged flame.",
        head=Head.SPIRITREAVER, frame=Frame.SHARPSHOT,
        maneuver_req=_three_of(ManeuverElement.FIRE),
        effect_kind=EffectKind.AOE_DOT,
        effect_payload=(("dot_per_tick", 35), ("ticks", 10)),
        duration_seconds=30,
        cooldown_seconds=600,            # 10 min
    ),
    SynergyAbility(
        ability_id="drain_pulse",
        name="Drain Pulse",
        description=(
            "Drains HP from a single target and converts it to a "
            "party-wide AoE heal."
        ),
        head=Head.SPIRITREAVER, frame=Frame.SOULSOOTHER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_HEAL,
        effect_payload=(
            ("drain_target", "single_enemy"),
            ("heal_to_party_pct", 80.0),
        ),
        duration_seconds=0,
        cooldown_seconds=300,            # 5 min
    ),
    SynergyAbility(
        ability_id="bio_iii_aoe",
        name="Bio III Resonance",
        description="AoE Bio III on enemies within 18 yalms.",
        head=Head.SPIRITREAVER, frame=Frame.STORMWAKER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(
            ("dot_per_tick", 22),
            ("attack_down_pct", 12),
        ),
        duration_seconds=60,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="deathgaze",
        name="Deathgaze",
        description=(
            "AoE Sleep + Bind on enemies within 18 yalms; ice + dark "
            "convergence."
        ),
        head=Head.SPIRITREAVER, frame=Frame.RDM,
        maneuver_req=_three_of(ManeuverElement.ICE),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(("status", "sleep+bind")),
        duration_seconds=30,
        cooldown_seconds=720,            # 12 min
    ),
    SynergyAbility(
        ability_id="negate_magic",
        name="Negate Magic",
        description=(
            "AoE silence + magic-defense -50% on enemies within "
            "18 yalms."
        ),
        head=Head.SPIRITREAVER, frame=Frame.NIN,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(
            ("status", "silence"),
            ("magic_defense_pct", -50),
        ),
        duration_seconds=60,
        cooldown_seconds=720,
    ),

    # ============== SOULSOOTHER HEAD (WHM) ==============
    SynergyAbility(
        ability_id="banish_aoe",
        name="Banish Resonance",
        description=(
            "AoE Holy damage on undead/demon enemies; lifesteal "
            "tinted by dark frame."
        ),
        head=Head.SOULSOOTHER, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_DAMAGE,
        effect_payload=(
            ("element", "light"),
            ("on_strike_heal_master_pct", 5.0),
        ),
        duration_seconds=30,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="holy_v_burst",
        name="Holy V Burst",
        description="Single-cast AoE Holy V across 18 yalms.",
        head=Head.SOULSOOTHER, frame=Frame.STORMWAKER,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.AOE_DAMAGE,
        effect_payload=(("element", "light"), ("base_damage", 1500)),
        duration_seconds=0,
        cooldown_seconds=900,
    ),
    SynergyAbility(
        ability_id="aoe_cleanse",
        name="Stona+Cursna",
        description=(
            "AoE removal of petrification, curse, doom, plague "
            "across the party."
        ),
        head=Head.SOULSOOTHER, frame=Frame.NIN,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.AOE_UTILITY,
        effect_payload=(
            ("removes", "petrify,curse,doom,plague"),
        ),
        duration_seconds=0,
        cooldown_seconds=300,
    ),
    SynergyAbility(
        ability_id="aoe_refresh_ii",
        name="Refresh II Procession",
        description="Party-wide MP regen 4/tick for 5 min.",
        head=Head.SOULSOOTHER, frame=Frame.RDM,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(("mp_per_tick", 4),),
        duration_seconds=300,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="holy_volley",
        name="Holy Volley",
        description=(
            "Each ranged shot fires a Holy spell payload alongside "
            "the bullet for 30 seconds."
        ),
        head=Head.SOULSOOTHER, frame=Frame.SHARPSHOT,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.SELF_BUFF,
        effect_payload=(
            ("on_ranged_attack", "holy_spell"),
            ("damage_scalar", 0.6),
        ),
        duration_seconds=30,
        cooldown_seconds=720,
    ),

    # ============== VALOREDGE HEAD (tank) ==============
    SynergyAbility(
        ability_id="earth_hammer",
        name="Earth Hammer",
        description=(
            "Single target massive Earth physical hit with AoE "
            "knockback in a cone."
        ),
        head=Head.VALOREDGE, frame=Frame.SHARPSHOT,
        maneuver_req=_three_of(ManeuverElement.EARTH),
        effect_kind=EffectKind.SINGLE_TARGET_DAMAGE,
        effect_payload=(
            ("damage_scalar", 4.0),
            ("knockback_yalms", 6),
        ),
        duration_seconds=0,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="sentinel_party",
        name="Sentinel's Vow",
        description=(
            "Party-wide tank buff: +50% enmity, +25% defense, "
            "Reprisal proc on block."
        ),
        head=Head.VALOREDGE, frame=Frame.SOULSOOTHER,
        maneuver_req=_three_of(ManeuverElement.LIGHT),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(
            ("enmity_pct", 50),
            ("defense_pct", 25),
            ("reprisal_on_block", True),
        ),
        duration_seconds=60,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="berserk_party",
        name="Aggressor's March",
        description=(
            "Party-wide DPS boost (+25% atk, +20% acc) at the cost "
            "of -10% defense."
        ),
        head=Head.VALOREDGE, frame=Frame.STORMWAKER,
        maneuver_req=_three_of(ManeuverElement.FIRE),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(
            ("attack_pct", 25),
            ("accuracy_pct", 20),
            ("defense_pct", -10),
        ),
        duration_seconds=60,
        cooldown_seconds=480,            # 8 min
    ),
    SynergyAbility(
        ability_id="souleater_party",
        name="Souleater's Lament",
        description=(
            "Each melee strike costs 5% HP and adds a flat damage "
            "bonus equal to 30% of HP cost. Party-wide."
        ),
        head=Head.VALOREDGE, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(
            ("hp_cost_per_strike_pct", 5),
            ("damage_bonus_pct_of_cost", 30),
        ),
        duration_seconds=60,
        cooldown_seconds=720,
    ),
    SynergyAbility(
        ability_id="phalanx_ii_party",
        name="Phalanx II Procession",
        description=(
            "Party-wide physical damage taken -30% for 5 min."
        ),
        head=Head.VALOREDGE, frame=Frame.RDM,
        maneuver_req=_three_of(ManeuverElement.ICE),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(("phys_damage_taken_pct", -30),),
        duration_seconds=300,
        cooldown_seconds=600,
    ),

    # ============== SHARPSHOT HEAD (RNG) ==============
    SynergyAbility(
        ability_id="barrage_triple",
        name="Barrage + Triple Shot",
        description=(
            "Each ranged attack fires 3 shots at full power for 30s."
        ),
        head=Head.SHARPSHOT, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.WIND),
        effect_kind=EffectKind.SELF_BUFF,
        effect_payload=(("shots_per_attack", 3),),
        duration_seconds=30,
        cooldown_seconds=480,
    ),
    SynergyAbility(
        ability_id="sharpshot_stealth",
        name="Sharpshot Stealth",
        description="Party-wide invisible + sneak for 1 minute.",
        head=Head.SHARPSHOT, frame=Frame.NIN,
        maneuver_req=_three_of(ManeuverElement.WIND),
        effect_kind=EffectKind.AOE_UTILITY,
        effect_payload=(("statuses", "invisible+sneak"),),
        duration_seconds=60,
        cooldown_seconds=360,            # 6 min
    ),
    SynergyAbility(
        ability_id="deaths_bow",
        name="Death's Bow",
        description=(
            "Single ranged shot that ignores all defense and "
            "damage reduction. Big number, long cooldown."
        ),
        head=Head.SHARPSHOT, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.SINGLE_TARGET_DAMAGE,
        effect_payload=(
            ("ignores_defense", True),
            ("base_damage", 4500),
        ),
        duration_seconds=0,
        cooldown_seconds=900,
    ),

    # ============== STORMWAKER HEAD (BLM) ==============
    SynergyAbility(
        ability_id="lightning_storm",
        name="Lightning Storm",
        description="AoE elemental DD, 1-minute lightning weather.",
        head=Head.STORMWAKER, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.LIGHTNING),
        effect_kind=EffectKind.AOE_DAMAGE,
        effect_payload=(
            ("element", "lightning"),
            ("damage_per_tick", 80),
        ),
        duration_seconds=60,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="thundaga_v",
        name="Thundaga V",
        description="Single-cast AoE Thundaga V across 18 yalms.",
        head=Head.STORMWAKER, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.LIGHTNING),
        effect_kind=EffectKind.AOE_DAMAGE,
        effect_payload=(
            ("element", "lightning"),
            ("base_damage", 1800),
        ),
        duration_seconds=0,
        cooldown_seconds=900,
    ),
    SynergyAbility(
        ability_id="aquaveil_party",
        name="Aquaveil Procession",
        description=(
            "Party-wide spell-interrupt immunity for 5 min."
        ),
        head=Head.STORMWAKER, frame=Frame.SOULSOOTHER,
        maneuver_req=_three_of(ManeuverElement.WATER),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(("interrupt_immunity", True),),
        duration_seconds=300,
        cooldown_seconds=600,
    ),

    # ============== RDM HEAD (Demoncore-extended) ==============
    SynergyAbility(
        ability_id="distract_frazzle_aoe",
        name="Distract+Frazzle Procession",
        description=(
            "AoE evasion-down + magic-evasion-down on enemies."
        ),
        head=Head.RDM, frame=Frame.STORMWAKER,
        maneuver_req=_three_of(ManeuverElement.FIRE),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(
            ("evasion_pct", -25),
            ("magic_evasion_pct", -25),
        ),
        duration_seconds=300,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="convert_party",
        name="Convert Procession",
        description=(
            "All party members within 18 yalms swap HP and MP "
            "(canonical Convert behavior, party-wide)."
        ),
        head=Head.RDM, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_UTILITY,
        effect_payload=(("operation", "swap_hp_mp"),),
        duration_seconds=0,
        cooldown_seconds=900,
    ),

    # ============== NIN HEAD (Demoncore-extended) ==============
    SynergyAbility(
        ability_id="hojo_ichi_aoe",
        name="Hojo:Ichi Procession",
        description=(
            "AoE Slow on enemies within 18 yalms (ninjutsu)."
        ),
        head=Head.NIN, frame=Frame.VALOREDGE,
        maneuver_req=_three_of(ManeuverElement.ICE),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(("slow_pct", 25),),
        duration_seconds=180,
        cooldown_seconds=480,
    ),
    SynergyAbility(
        ability_id="kurayami_san",
        name="Kurayami:San",
        description=(
            "AoE Blind on enemies within 18 yalms (ninjutsu)."
        ),
        head=Head.NIN, frame=Frame.SPIRITREAVER,
        maneuver_req=_three_of(ManeuverElement.DARK),
        effect_kind=EffectKind.AOE_DEBUFF,
        effect_payload=(("accuracy_pct", -30),),
        duration_seconds=180,
        cooldown_seconds=600,
    ),
    SynergyAbility(
        ability_id="suiton_san_party",
        name="Suiton:San Procession",
        description=(
            "Party-wide evasion buff + sneak."
        ),
        head=Head.NIN, frame=Frame.RDM,
        maneuver_req=_three_of(ManeuverElement.WATER),
        effect_kind=EffectKind.PARTY_BUFF,
        effect_payload=(
            ("evasion_pct", 30),
            ("status", "sneak"),
        ),
        duration_seconds=180,
        cooldown_seconds=480,
    ),
)


# Quick lookup index. Built from the catalog at import time.
_BY_HEAD_FRAME: dict[
    tuple[Head, Frame], tuple[SynergyAbility, ...]
] = {}
for _ability in SYNERGY_CATALOG:
    _key = (_ability.head, _ability.frame)
    _BY_HEAD_FRAME.setdefault(_key, ())
    _BY_HEAD_FRAME[_key] = _BY_HEAD_FRAME[_key] + (_ability,)


def _maneuvers_satisfy(
    requirement: tuple[tuple[ManeuverElement, int], ...],
    active: t.Mapping[ManeuverElement, int],
) -> bool:
    """Active maneuvers must include AT LEAST the required count
    for each element. Extra maneuvers don't hurt — what matters
    is the requirement is met."""
    for element, needed in requirement:
        if active.get(element, 0) < needed:
            return False
    return True


def check_synergy(
    *,
    head: Head,
    frame: Frame,
    active_maneuvers: t.Mapping[ManeuverElement, int],
) -> t.Optional[SynergyAbility]:
    """Find a synergy that matches this (head, frame, maneuvers).

    Returns the matched SynergyAbility, or None if no synergy
    fits. If multiple synergies match the same combo (shouldn't
    happen by design, but defensive), the first registered wins.
    """
    candidates = _BY_HEAD_FRAME.get((head, frame), ())
    for ability in candidates:
        if _maneuvers_satisfy(
            ability.maneuver_req, active_maneuvers,
        ):
            return ability
    return None


def synergies_for(
    *, head: Head, frame: Frame,
) -> tuple[SynergyAbility, ...]:
    """All synergies registered for this head+frame pair."""
    return _BY_HEAD_FRAME.get((head, frame), ())


def all_synergy_ids() -> tuple[str, ...]:
    return tuple(a.ability_id for a in SYNERGY_CATALOG)


def get_synergy(ability_id: str) -> SynergyAbility:
    for a in SYNERGY_CATALOG:
        if a.ability_id == ability_id:
            return a
    raise KeyError(f"unknown synergy ability_id: {ability_id}")


__all__ = [
    "Head", "Frame", "ManeuverElement",
    "EffectKind", "AOE_RADIUS_PARTY_YALMS",
    "SynergyAbility",
    "SYNERGY_CATALOG", "DESIGNATED_FOUNDER_IDS",
    "check_synergy", "synergies_for", "all_synergy_ids",
    "get_synergy",
]
