"""Heretic branded — surface NPCs treat cult players differently.

Once a player is BRANDED (high taint OR HOLLOWED OR known
cult member), surface NPCs react with prejudice. Each NPC
has a REACTION CLASS based on their faction:
  HEALER          - refuses to heal/raise/cure
  MERCHANT        - refuses sale; reports to guard
  GUARD           - aggros on sight
  COMMONER        - flees
  COUNCIL_NEUTRAL - acts normally (mermaid TIDE_KEEPERS that
                    aren't surface npcs)

The BRAND is set when the player crosses into ABYSSAL band
(taint >= 60) or performs the drowned pact. It persists
until corruption_taint drops below the SICKENED ceiling
(taint < 30) — i.e. the brand is sticky one band below the
trigger.

Some surface zones are SAFE (cult-tolerant) — Norg pirate
town historically takes outlaws so it tolerates branded
players too. The system publishes is_safe_zone(zone_id)
that callers can check before applying NPC reactions.

Public surface
--------------
    NPCReaction enum
    BrandStatus dataclass
    HereticBranded
        .recompute(player_id, taint_level, performed_pact)
        .npc_reaction(player_id, npc_class)
        .is_branded(player_id)
        .is_safe_zone(zone_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NPCReaction(str, enum.Enum):
    NORMAL = "normal"
    REFUSE_HEAL = "refuse_heal"
    REFUSE_SALE = "refuse_sale"
    AGGRO = "aggro"
    FLEE = "flee"


class NPCClass(str, enum.Enum):
    HEALER = "healer"
    MERCHANT = "merchant"
    GUARD = "guard"
    COMMONER = "commoner"
    COUNCIL_NEUTRAL = "council_neutral"


_BRANDED_REACTION: dict[NPCClass, NPCReaction] = {
    NPCClass.HEALER: NPCReaction.REFUSE_HEAL,
    NPCClass.MERCHANT: NPCReaction.REFUSE_SALE,
    NPCClass.GUARD: NPCReaction.AGGRO,
    NPCClass.COMMONER: NPCReaction.FLEE,
    NPCClass.COUNCIL_NEUTRAL: NPCReaction.NORMAL,
}

# brand sets when taint hits this; clears below the lower bound
_BRAND_SET_THRESHOLD = 60
_BRAND_CLEAR_THRESHOLD = 30

# zones that tolerate branded players (cult-tolerant)
_SAFE_ZONES = (
    "norg_port",
    "drowned_void",        # cult HQ
    "wreckage_graveyard",  # pirate territory
    "abyss_trench",        # nobody's law
)


@dataclasses.dataclass
class BrandStatus:
    player_id: str
    branded: bool = False
    via_pact: bool = False
    via_taint: bool = False
    last_recompute_at: int = 0


@dataclasses.dataclass
class HereticBranded:
    _statuses: dict[str, BrandStatus] = dataclasses.field(
        default_factory=dict,
    )

    def recompute(
        self, *, player_id: str,
        taint_level: int,
        performed_pact: bool,
        now_seconds: int = 0,
    ) -> BrandStatus:
        st = self._statuses.setdefault(
            player_id,
            BrandStatus(player_id=player_id),
        )
        st.via_pact = bool(performed_pact)
        # taint-based brand: latch on at >= SET, clear at < CLEAR
        if taint_level >= _BRAND_SET_THRESHOLD:
            st.via_taint = True
        elif taint_level < _BRAND_CLEAR_THRESHOLD:
            st.via_taint = False
        # branded if either reason holds
        st.branded = st.via_pact or st.via_taint
        st.last_recompute_at = now_seconds
        return st

    def is_branded(self, *, player_id: str) -> bool:
        st = self._statuses.get(player_id)
        return bool(st and st.branded)

    def npc_reaction(
        self, *, player_id: str,
        npc_class: NPCClass,
        zone_id: t.Optional[str] = None,
    ) -> NPCReaction:
        if not self.is_branded(player_id=player_id):
            return NPCReaction.NORMAL
        # safe zones suspend reactions
        if zone_id is not None and self.is_safe_zone(zone_id=zone_id):
            return NPCReaction.NORMAL
        return _BRANDED_REACTION.get(npc_class, NPCReaction.NORMAL)

    @staticmethod
    def is_safe_zone(*, zone_id: str) -> bool:
        return zone_id in _SAFE_ZONES


__all__ = [
    "NPCReaction", "NPCClass",
    "BrandStatus", "HereticBranded",
]
