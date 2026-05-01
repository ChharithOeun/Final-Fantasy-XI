"""Hidden automaton synergies — head + frame + maneuvers unlock secret abilities.

Per HARDCORE_DEATH and the Tomb Raid extension: PUP gameplay in
Demoncore is the canonical "experimentation rewards you" loop.
Mismatched head/frame combinations DO have purpose — the right
3-maneuver pattern unlocks a hidden ability with a long cooldown
and a generous duration. Under SP "Overdrive", duration AND
effectiveness scale 5x.

Module layout
-------------
    catalog.py   - Head/Frame/EffectKind enums, SynergyAbility
                       dataclass, SYNERGY_CATALOG (~25 entries),
                       check_synergy lookup
    cooldowns.py - CooldownTracker (per-master, per-ability)
    overdrive.py - ModifiedAbility wrapper, 5x SP multiplier
    effects.py   - EffectInstance dataclass, payload scaling
    activation.py- activate_synergy() — the main entry point
"""
from .activation import (
    ActivationResult,
    ActivationStatus,
    activate_synergy,
)
from .catalog import (
    AOE_RADIUS_PARTY_YALMS,
    DESIGNATED_FOUNDER_IDS,
    SYNERGY_CATALOG,
    EffectKind,
    Frame,
    Head,
    ManeuverElement,
    SynergyAbility,
    all_synergy_ids,
    check_synergy,
    get_synergy,
    synergies_for,
)
from .cooldowns import CooldownTracker
from .effects import EffectInstance, build_effect_instance
from .overdrive import (
    OVERDRIVE_MULTIPLIER,
    ModifiedAbility,
    compute_modified_ability,
    scale_effect_value,
)

__all__ = [
    # catalog
    "Head", "Frame", "ManeuverElement",
    "EffectKind", "AOE_RADIUS_PARTY_YALMS",
    "SynergyAbility", "SYNERGY_CATALOG",
    "DESIGNATED_FOUNDER_IDS",
    "check_synergy", "synergies_for", "all_synergy_ids",
    "get_synergy",
    # cooldowns
    "CooldownTracker",
    # overdrive
    "OVERDRIVE_MULTIPLIER", "ModifiedAbility",
    "compute_modified_ability", "scale_effect_value",
    # effects
    "EffectInstance", "build_effect_instance",
    # activation
    "ActivationStatus", "ActivationResult", "activate_synergy",
]
