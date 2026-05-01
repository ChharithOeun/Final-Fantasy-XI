"""Civilian NPC progression — role-tuned XP + retirement + heir succession.

Each civilian NPC has a role that determines what counts as XP for
them. Routine ticking, witnessed events, and player interactions all
contribute. When the NPC hits their role's level cap AND has saved
their gil goal, they retire and their stall passes to an heir.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NpcRole(str, enum.Enum):
    """Civilian role — drives XP source + gear wishlist."""
    SHOPKEEPER = "shopkeeper"
    GUILD_MASTER = "guild_master"
    GUARD = "guard"
    AMBIENT_TOWNFOLK = "ambient_townfolk"
    QUEST_GIVER = "quest_giver"


# Per-role level cap. Guild masters and guards reach higher caps;
# ambient townfolk plateau early.
LEVEL_CAP_BY_ROLE: dict[NpcRole, int] = {
    NpcRole.SHOPKEEPER: 65,
    NpcRole.GUILD_MASTER: 85,
    NpcRole.GUARD: 75,
    NpcRole.AMBIENT_TOWNFOLK: 30,
    NpcRole.QUEST_GIVER: 70,
}


# Per-role gil savings goal at which the NPC considers retirement.
RETIREMENT_GIL_GOAL: dict[NpcRole, int] = {
    NpcRole.SHOPKEEPER: 5_000_000,
    NpcRole.GUILD_MASTER: 8_000_000,
    NpcRole.GUARD: 2_000_000,
    NpcRole.AMBIENT_TOWNFOLK: 500_000,
    NpcRole.QUEST_GIVER: 3_000_000,
}


# Per-role per-Vana'diel-hour ambient XP earn rate
AMBIENT_HOURLY_XP: dict[NpcRole, float] = {
    NpcRole.SHOPKEEPER: 0.20,
    NpcRole.GUILD_MASTER: 0.15,
    NpcRole.GUARD: 0.30,
    NpcRole.AMBIENT_TOWNFOLK: 0.05,
    NpcRole.QUEST_GIVER: 0.10,
}


# Witnessed-event XP burst by event severity.
EVENT_XP_BURSTS: dict[str, float] = {
    "fomor_invasion_repelled": 200.0,
    "fomor_invasion_witnessed": 80.0,
    "boss_kill_witnessed": 60.0,
    "siege_repelled": 250.0,
    "siege_witnessed": 100.0,
    "city_attacked": 150.0,
    "outlaw_executed": 30.0,
    "festival_attended": 10.0,
    "neighbor_retired": 25.0,
}


# Player-interaction XP by interaction type
PLAYER_INTERACTION_XP: dict[str, float] = {
    "purchase_completed": 0.5,
    "quest_handed_out": 1.0,
    "quest_completed_by_player": 5.0,
    "advice_given_player_succeeded": 3.0,
    "training_session_completed": 2.0,
}


@dataclasses.dataclass
class NpcXpEvent:
    """One XP-granting event in the NPC's history. Useful for the
    'NPC remembers a player who saved them' lore hook."""
    timestamp: float
    source: str            # "ambient_tick" / "witness:fomor_invasion" /
                            # "player:purchase_completed"
    amount: float
    detail: t.Optional[str] = None


@dataclasses.dataclass
class NpcSnapshot:
    """Per-civilian-NPC progression state."""
    npc_id: str
    name: str
    role: NpcRole
    zone: str
    level: int = 1
    xp_into_level: float = 0.0
    gil: int = 0
    is_retired: bool = False
    heir_npc_id: t.Optional[str] = None
    xp_history: list[NpcXpEvent] = dataclasses.field(default_factory=list)


# ----------------------------------------------------------------------
# XP curve
# ----------------------------------------------------------------------

def xp_required_for_level(level: int) -> float:
    """Civilian XP curve: 100 * level cumulative-into-level."""
    if level <= 0:
        return 0.0
    return 100.0 * level


def _apply_xp(state: NpcSnapshot, amount: float, source: str,
              *, now: float, detail: t.Optional[str] = None) -> int:
    """Internal: add xp + roll level + record event. Returns the new level."""
    if amount <= 0 or state.is_retired:
        return state.level
    cap = LEVEL_CAP_BY_ROLE[state.role]
    state.xp_history.append(NpcXpEvent(timestamp=now, source=source,
                                          amount=amount, detail=detail))
    state.xp_into_level += amount
    while state.level < cap:
        threshold = xp_required_for_level(state.level + 1)
        if state.xp_into_level < threshold:
            break
        state.xp_into_level -= threshold
        state.level += 1
    return state.level


def award_xp(state: NpcSnapshot,
              *,
              kind: str,
              now: float,
              detail: t.Optional[str] = None) -> int:
    """Public XP-granting helper. `kind` is either an
    AMBIENT_HOURLY_XP key, an EVENT_XP_BURSTS key, or a
    PLAYER_INTERACTION_XP key."""
    if kind == "ambient_tick":
        amount = AMBIENT_HOURLY_XP.get(state.role, 0.05)
        return _apply_xp(state, amount, "ambient_tick", now=now, detail=detail)
    if kind in EVENT_XP_BURSTS:
        return _apply_xp(state, EVENT_XP_BURSTS[kind],
                          f"witness:{kind}", now=now, detail=detail)
    if kind in PLAYER_INTERACTION_XP:
        return _apply_xp(state, PLAYER_INTERACTION_XP[kind],
                          f"player:{kind}", now=now, detail=detail)
    return state.level


def witness_event(state: NpcSnapshot,
                   *,
                   event_kind: str,
                   now: float,
                   detail: t.Optional[str] = None) -> int:
    """The NPC witnesses something dramatic. Returns the new level."""
    return award_xp(state, kind=event_kind, now=now, detail=detail)


# ----------------------------------------------------------------------
# Retirement + heir succession
# ----------------------------------------------------------------------

def ready_to_retire(state: NpcSnapshot) -> bool:
    """An NPC retires when they hit their role cap AND their savings
    goal."""
    if state.is_retired:
        return False
    cap = LEVEL_CAP_BY_ROLE[state.role]
    goal = RETIREMENT_GIL_GOAL[state.role]
    return state.level >= cap and state.gil >= goal


def retire_npc(state: NpcSnapshot,
                *,
                heir_npc_id: str) -> bool:
    """Mark the NPC retired. Returns True if the retirement applied."""
    if not ready_to_retire(state):
        return False
    state.is_retired = True
    state.heir_npc_id = heir_npc_id
    return True


def promote_heir(*,
                  retiring: NpcSnapshot,
                  heir_id: str,
                  heir_name: str,
                  starting_level: int = 1,
                  starting_gil: int = 0) -> NpcSnapshot:
    """Construct the heir NPC inheriting the role + zone. The heir
    starts fresh — their own career begins now."""
    return NpcSnapshot(
        npc_id=heir_id,
        name=heir_name,
        role=retiring.role,
        zone=retiring.zone,
        level=starting_level,
        gil=starting_gil,
    )
