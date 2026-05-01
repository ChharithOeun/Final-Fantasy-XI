"""PvP / griefing rules for structure damage.

Per DAMAGE_PHYSICS_HEALING.md:
    - Damaging structures inside your own nation lowers your Honor
      gauge (HONOR_REPUTATION.md) and racks up a fine.
    - Damaging structures inside an enemy nation as part of an outlaw
      raid is normal (encouraged during nation-vs-nation periods).
    - Destroying iconic structures triggers a server-wide alert and
      tags the perpetrator with a high-priority bounty.
    - Mob AoE during normal play does not damage structures unless the
      mob is part of a Besieged-tier event. This prevents accidental
      griefing and keeps fishing-for-XP-near-stalls a viable activity.

The combat pipeline calls classify_strike(...) BEFORE applying damage
to a structure. The returned StrikeRuling tells the caller whether
the hit lands at all and what gauges to update.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .structure_kinds import is_iconic
from .structure_state import HealingStructure


class StrikeOutcome(str, enum.Enum):
    """The outcome of running a structure-strike through the rules."""
    APPLY = "apply"                       # hit is legal, apply damage
    BLOCKED_MOB_AOE_NORMAL = "blocked_mob_aoe_normal"
    BLOCKED_NON_OUTLAW_FOREIGN = "blocked_non_outlaw_foreign"


@dataclasses.dataclass(frozen=True)
class StrikeRuling:
    """Caller's instructions after the rules check."""
    outcome: StrikeOutcome
    apply_damage: bool
    honor_delta: int = 0                  # negative for own-nation damage
    fine_gil: int = 0
    iconic_alert: bool = False
    bounty_priority: t.Optional[str] = None    # 'low' | 'high'
    reason: str = ""


# Tuning anchors. Honor / fine values are the per-strike base; the
# Honor system stacks them across a session.
OWN_NATION_HONOR_PENALTY = -5
OWN_NATION_FINE_GIL = 500
ICONIC_HONOR_PENALTY = -50
ICONIC_FINE_GIL = 25_000


@dataclasses.dataclass(frozen=True)
class StrikeContext:
    """Inputs the caller passes to classify_strike."""
    attacker_id: str
    attacker_nation: str
    attacker_is_outlaw: bool
    attacker_in_nation_vs_nation_period: bool
    structure_nation: str             # the nation whose territory the
                                          # structure sits in
    is_mob_attack: bool
    is_besieged_event: bool


def classify_strike(structure: HealingStructure,
                       *,
                       ctx: StrikeContext) -> StrikeRuling:
    """Decide whether `ctx.attacker_id` may damage `structure`.

    Players: hitting their own nation's stuff is allowed but costly.
    Mobs: only Besieged-tier events damage structures; otherwise a
    cleric_brother fireball melting the cart in front of the gate is
    a no-op so XP-near-stalls remains viable.
    """
    if ctx.is_mob_attack:
        if not ctx.is_besieged_event:
            return StrikeRuling(
                outcome=StrikeOutcome.BLOCKED_MOB_AOE_NORMAL,
                apply_damage=False,
                reason="mob AoE doesn't damage structures outside Besieged",
            )
        return StrikeRuling(
            outcome=StrikeOutcome.APPLY,
            apply_damage=True,
            reason="Besieged-tier mob attack",
        )

    iconic = is_iconic(structure.kind)

    if ctx.attacker_nation == ctx.structure_nation:
        # Own-nation. Allowed, but penalize.
        ruling = StrikeRuling(
            outcome=StrikeOutcome.APPLY,
            apply_damage=True,
            honor_delta=OWN_NATION_HONOR_PENALTY,
            fine_gil=OWN_NATION_FINE_GIL,
            reason="own-nation damage: legal but fined",
        )
        if iconic:
            ruling = dataclasses.replace(
                ruling,
                honor_delta=ICONIC_HONOR_PENALTY,
                fine_gil=ICONIC_FINE_GIL,
                iconic_alert=True,
                bounty_priority="high",
                reason="iconic-structure damage triggers server alert",
            )
        return ruling

    # Foreign-nation damage. Outlaw or nation-vs-nation period required.
    if not (ctx.attacker_is_outlaw
              or ctx.attacker_in_nation_vs_nation_period):
        return StrikeRuling(
            outcome=StrikeOutcome.BLOCKED_NON_OUTLAW_FOREIGN,
            apply_damage=False,
            reason="must be outlaw or in nation-vs-nation period",
        )

    if iconic:
        return StrikeRuling(
            outcome=StrikeOutcome.APPLY,
            apply_damage=True,
            iconic_alert=True,
            bounty_priority="high",
            reason="foreign iconic-structure damage triggers alert",
        )
    return StrikeRuling(
        outcome=StrikeOutcome.APPLY,
        apply_damage=True,
        bounty_priority="low",
        reason="foreign-nation damage during outlaw raid",
    )
