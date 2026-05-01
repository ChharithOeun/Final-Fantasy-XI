"""Intervention Magic Burst — the heroic save mechanic.

Per INTERVENTION_MB.md: 'The most lethal moment in a Demoncore fight
is the enemy skillchain... Unless your WHM read the chain element,
started Cure IV at the right moment, and lands the cast inside the
enemy's MB window. In which case the tank takes ZERO damage — and
gets healed at 3x with a 30-second Regen.'

The world plays both sides — mob healers can intervention-cure
their friendlies against player chains, so a 4-mob group with a
healer is harder than a 6-mob group without.

Module layout:
    window.py             - InterventionWindow + 3s timer + Light flag
    amplification.py      - 3x base / 5x Light per spell family
    dual_cast.py          - 30s dual-cast unlock per family + GEO/Tank carve-outs
    callouts.py           - per-job + mob-class voice lines
    resolver.py           - resolve_intervention pipeline (cancel + amp + buffs)
"""
from .amplification import (
    BASE_AMPLIFICATION,
    LIGHT_AMPLIFICATION,
    SpellFamily,
    amplification_for,
    apply_amplification,
    is_eligible,
)
from .callouts import (
    Callout,
    callout_for,
    failure_grunt,
    mob_intervention_callout,
)
from .dual_cast import (
    DUAL_CAST_DURATION_SECONDS,
    FAMILY_TO_BUFF,
    DualCastBuff,
    DualCastBuffId,
    DualCastManager,
)
from .resolver import (
    INTERVENTION_IMMUNITY_DURATION_S,
    INTERVENTION_REGEN_DURATION_S,
    LIGHT_IMMUNITY_DURATION_S,
    InterventionResult,
    resolve_intervention,
)
from .window import (
    INTERVENTION_WINDOW_SECONDS,
    ChainElement,
    InterventionWindow,
    lands_in_window,
    open_window,
)

__all__ = [
    # window
    "ChainElement", "InterventionWindow",
    "INTERVENTION_WINDOW_SECONDS", "open_window", "lands_in_window",
    # amplification
    "SpellFamily", "BASE_AMPLIFICATION", "LIGHT_AMPLIFICATION",
    "amplification_for", "apply_amplification", "is_eligible",
    # dual_cast
    "DualCastBuffId", "DualCastBuff", "DualCastManager",
    "FAMILY_TO_BUFF", "DUAL_CAST_DURATION_SECONDS",
    # callouts
    "Callout", "callout_for", "failure_grunt",
    "mob_intervention_callout",
    # resolver
    "InterventionResult", "resolve_intervention",
    "INTERVENTION_REGEN_DURATION_S",
    "INTERVENTION_IMMUNITY_DURATION_S",
    "LIGHT_IMMUNITY_DURATION_S",
]
