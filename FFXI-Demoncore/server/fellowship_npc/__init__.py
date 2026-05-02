"""Fellowship NPC — pre-Trust adventuring companion.

Players hire a single NPC who fights alongside them. The NPC has
personality, equips gear, levels with the player (capped at player
level + 5 max), and is summoned via Signal Pearl. Different from
Trust (instant summon roster) — Fellowship is one-and-only, more
intimate, and grows over time with the player.

Public surface
--------------
    FellowshipPersonality enum
    FellowshipNPC dataclass
    PlayerFellowship per-character
        .hire(npc_template_id, name)
        .level_up()
        .equip(slot, item_id)
        .summon(now_tick)
        .dismiss(now_tick)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FellowshipPersonality(str, enum.Enum):
    BRAVE = "brave"           # melee tank-leaning
    SOLDIER = "soldier"       # melee dd
    HEALER = "healer"         # white-mage style
    SCHOLAR = "scholar"       # caster
    HOSPITALER = "hospitaler" # paladin-leaning
    SCOUT = "scout"           # ranger style


class FellowshipSlot(str, enum.Enum):
    MAIN_HAND = "main_hand"
    HEAD = "head"
    BODY = "body"


@dataclasses.dataclass(frozen=True)
class FellowshipTemplate:
    template_id: str
    label: str
    personality: FellowshipPersonality
    starting_level: int = 1


FELLOWSHIP_TEMPLATES: tuple[FellowshipTemplate, ...] = (
    FellowshipTemplate("ulrich", "Ulrich",
                        personality=FellowshipPersonality.BRAVE),
    FellowshipTemplate("monberaux", "Monberaux",
                        personality=FellowshipPersonality.HEALER),
    FellowshipTemplate("gilles", "Gilles",
                        personality=FellowshipPersonality.SCHOLAR),
    FellowshipTemplate("kayeel", "Kayeel-Payeel",
                        personality=FellowshipPersonality.SCOUT),
)

TEMPLATE_BY_ID: dict[str, FellowshipTemplate] = {
    t.template_id: t for t in FELLOWSHIP_TEMPLATES
}


# Summon cooldown
SUMMON_COOLDOWN_SECONDS = 60 * 60   # 1 hour
LEVEL_CAP_BUFFER_OVER_PLAYER = 5


@dataclasses.dataclass
class FellowshipNPC:
    name: str
    template_id: str
    level: int
    equipment: dict[FellowshipSlot, str] = dataclasses.field(
        default_factory=dict,
    )
    summoned: bool = False
    last_summon_tick: int = -SUMMON_COOLDOWN_SECONDS

    @property
    def template(self) -> FellowshipTemplate:
        return TEMPLATE_BY_ID[self.template_id]

    @property
    def personality(self) -> FellowshipPersonality:
        return self.template.personality


@dataclasses.dataclass(frozen=True)
class ActionResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerFellowship:
    player_id: str
    npc: t.Optional[FellowshipNPC] = None

    def hire(
        self, *, template_id: str, name: str,
    ) -> ActionResult:
        if self.npc is not None:
            return ActionResult(False, reason="already have a fellow")
        if template_id not in TEMPLATE_BY_ID:
            return ActionResult(False, reason="unknown template")
        if not name.strip():
            return ActionResult(False, reason="empty name")
        tpl = TEMPLATE_BY_ID[template_id]
        self.npc = FellowshipNPC(
            name=name, template_id=template_id,
            level=tpl.starting_level,
        )
        return ActionResult(True)

    def level_up(
        self, *, player_level: int,
    ) -> ActionResult:
        if self.npc is None:
            return ActionResult(False, reason="no fellow hired")
        cap = player_level + LEVEL_CAP_BUFFER_OVER_PLAYER
        if self.npc.level >= cap:
            return ActionResult(False, reason="level capped to player")
        self.npc.level += 1
        return ActionResult(True)

    def equip(
        self, *,
        slot: FellowshipSlot, item_id: str,
    ) -> ActionResult:
        if self.npc is None:
            return ActionResult(False, reason="no fellow hired")
        self.npc.equipment[slot] = item_id
        return ActionResult(True)

    def unequip(
        self, *, slot: FellowshipSlot,
    ) -> ActionResult:
        if self.npc is None:
            return ActionResult(False, reason="no fellow hired")
        if slot not in self.npc.equipment:
            return ActionResult(False, reason="slot empty")
        del self.npc.equipment[slot]
        return ActionResult(True)

    def summon(self, *, now_tick: int) -> ActionResult:
        if self.npc is None:
            return ActionResult(False, reason="no fellow hired")
        if self.npc.summoned:
            return ActionResult(False, reason="already summoned")
        next_avail = self.npc.last_summon_tick + \
            SUMMON_COOLDOWN_SECONDS
        if now_tick < next_avail:
            return ActionResult(
                False, reason="signal pearl on cooldown",
            )
        self.npc.summoned = True
        self.npc.last_summon_tick = now_tick
        return ActionResult(True)

    def dismiss(self) -> ActionResult:
        if self.npc is None:
            return ActionResult(False, reason="no fellow hired")
        if not self.npc.summoned:
            return ActionResult(False, reason="not summoned")
        self.npc.summoned = False
        return ActionResult(True)


__all__ = [
    "FellowshipPersonality", "FellowshipSlot",
    "FellowshipTemplate", "FELLOWSHIP_TEMPLATES",
    "TEMPLATE_BY_ID",
    "SUMMON_COOLDOWN_SECONDS",
    "LEVEL_CAP_BUFFER_OVER_PLAYER",
    "FellowshipNPC", "ActionResult", "PlayerFellowship",
]
