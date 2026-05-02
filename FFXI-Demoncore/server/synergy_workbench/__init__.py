"""Synergy Workbench — Escutcheon-gated group craft.

The machine that drives Ambuscade Repurpose: load a Recipe Slip,
gather inputs from anywhere on the participating players,
satisfy the Escutcheon requirement, and produce an upgraded
piece. Solo / no-Escutcheon players use the NPC Master Crafter
bypass instead.

Inventory pull
--------------
The bench can read materials from any of these sources on the
LEAD CRAFTER:
    * inventory     (held)
    * mog_safe      (Mog Safe / Safe 2)
    * mog_locker    (rented foreign storage)
    * mog_wardrobe  (1-4)
    * slip_storage  (canonical FFXI slip-stored gear)
    * storage_npc   (NPC slip storage)

Contributors (other players in the group) can also volunteer
their inventory (held only — not safe/locker, since their stuff
is at home). A volunteered piece is consumed if used in the
synth.

Group charge
------------
Each contributor adds +1 to the synergy charge. Charge maps to
final stat-roll quality:
    1 contributor   -> charge 1   -> roll +0%
    2 contributors  -> charge 2   -> roll +5%
    3 contributors  -> charge 3   -> roll +10%
    4 contributors  -> charge 4   -> roll +15%
    5 contributors  -> charge 5   -> roll +20%
    6 contributors  -> charge 6   -> roll +25% (max)

NPC Master Crafter bypass
-------------------------
For solo / shieldless players. Located in capital cities.
Requirements:
    * Steep gil cost
    * 4 R drops from beastmen-stronghold NMs (R = tradable, so
      AH/bazaar-buyable for new toons that can't NM-farm yet)
    * 7 real days turn-around per piece
    * No party, no Escutcheon, no shield required
Output is capped at NQ quality (no +1/+2/+3/+4 bumps). Players
who want max stats still need to engage with group craft.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.recipe_slip_registry import RecipeSlip


MAX_CONTRIBUTORS = 6
NPC_BYPASS_DAYS = 7
NPC_BYPASS_R_DROPS_REQUIRED = 4
NPC_BYPASS_GIL_COST = 1_500_000


class StorageKind(str, enum.Enum):
    INVENTORY = "inventory"
    MOG_SAFE = "mog_safe"
    MOG_LOCKER = "mog_locker"
    MOG_WARDROBE = "mog_wardrobe"
    SLIP_STORAGE = "slip_storage"
    STORAGE_NPC = "storage_npc"


@dataclasses.dataclass(frozen=True)
class MaterialEntry:
    """A material the player has somewhere accessible."""
    item_id: str
    quantity: int
    location: StorageKind
    holder_id: str            # whose stash it lives in


@dataclasses.dataclass(frozen=True)
class CraftRequirement:
    """One line of a recipe's input list. The recipe slip resolves
    to a tuple of these. Materials can be regular items or whole
    bundles ('all_ilvl_117_body_pieces_caster')."""
    requirement_id: str
    quantity: int
    is_bundle: bool = False    # True for "all i-lvl X pieces in slot Y"


@dataclasses.dataclass
class WorkbenchSession:
    session_id: str
    lead_player_id: str
    bench_zone: str
    contributors: list[str] = dataclasses.field(default_factory=list)
    slip_loaded: t.Optional[RecipeSlip] = None
    has_escutcheon_equipped: bool = False
    npc_assist_id: t.Optional[str] = None
    materials_committed: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    state: str = "open"        # open / locked / executed / cancelled

    @property
    def synergy_charge(self) -> int:
        """1 lead + N contributors, capped at MAX_CONTRIBUTORS."""
        return min(MAX_CONTRIBUTORS, 1 + len(self.contributors))

    @property
    def quality_roll_bonus_pct(self) -> int:
        """+5% per contributor above the lead, max +25%."""
        return 5 * max(0, self.synergy_charge - 1)


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    session: t.Optional[WorkbenchSession] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ExecuteResult:
    accepted: bool
    output_item_id: t.Optional[str] = None
    quality_roll_bonus_pct: int = 0
    reason: t.Optional[str] = None


def open_session(
    *, session_id: str, lead_player_id: str, bench_zone: str,
    has_escutcheon_equipped: bool,
    npc_assist_id: t.Optional[str] = None,
) -> StartResult:
    """Begin a workbench session. Either a player has the shield
    equipped, OR they're using NPC bypass — never both."""
    if has_escutcheon_equipped and npc_assist_id is not None:
        return StartResult(
            False, reason="cannot use NPC bypass with shield",
        )
    if not has_escutcheon_equipped and npc_assist_id is None:
        return StartResult(
            False, reason="need Escutcheon equipped or NPC bypass",
        )
    s = WorkbenchSession(
        session_id=session_id,
        lead_player_id=lead_player_id,
        bench_zone=bench_zone,
        has_escutcheon_equipped=has_escutcheon_equipped,
        npc_assist_id=npc_assist_id,
    )
    return StartResult(True, session=s)


def load_slip(*, session: WorkbenchSession,
              slip: RecipeSlip) -> bool:
    if session.state != "open":
        return False
    if session.slip_loaded is not None:
        return False
    session.slip_loaded = slip
    return True


def add_contributor(*, session: WorkbenchSession,
                     player_id: str) -> bool:
    """Add another player to the synergy group. NPC-assisted
    sessions don't allow contributors."""
    if session.npc_assist_id is not None:
        return False
    if session.state != "open":
        return False
    if player_id == session.lead_player_id:
        return False
    if player_id in session.contributors:
        return False
    if len(session.contributors) >= MAX_CONTRIBUTORS - 1:
        return False
    session.contributors.append(player_id)
    return True


def gather_materials(
    *, session: WorkbenchSession,
    available: t.Iterable[MaterialEntry],
    required: t.Iterable[CraftRequirement],
) -> tuple[bool, list[str]]:
    """Try to satisfy *required* from *available* across all
    storage kinds and contributors.

    Returns (ok, missing_requirement_ids). On ok=True, the
    session.materials_committed is populated with the items the
    bench will consume."""
    # Build a multimap of available materials keyed by item_id
    pool: dict[str, int] = {}
    for m in available:
        pool[m.item_id] = pool.get(m.item_id, 0) + m.quantity
    missing: list[str] = []
    consumed: dict[str, int] = {}
    for req in required:
        have = pool.get(req.requirement_id, 0)
        if have < req.quantity:
            missing.append(req.requirement_id)
        else:
            pool[req.requirement_id] = have - req.quantity
            consumed[req.requirement_id] = req.quantity
    if missing:
        return False, missing
    session.materials_committed = consumed
    return True, []


def execute_synth(
    *, session: WorkbenchSession,
) -> ExecuteResult:
    if session.state != "open":
        return ExecuteResult(False, reason="session not open")
    if session.slip_loaded is None:
        return ExecuteResult(False, reason="no recipe slip loaded")
    if not session.materials_committed:
        return ExecuteResult(False, reason="no materials committed")
    # Resolve output piece id from the slip
    slip = session.slip_loaded
    output = (
        f"ambuscade_{slip.archetype.value}_{slip.slot.value}"
    )
    quality_bonus = (
        0 if session.npc_assist_id else session.quality_roll_bonus_pct
    )
    session.state = "executed"
    return ExecuteResult(
        accepted=True,
        output_item_id=output,
        quality_roll_bonus_pct=quality_bonus,
    )


def cancel_session(*, session: WorkbenchSession) -> bool:
    if session.state in ("executed", "cancelled"):
        return False
    session.state = "cancelled"
    return True


@dataclasses.dataclass(frozen=True)
class NpcBypassQuote:
    accepted: bool
    gil_cost: int = 0
    days_required: int = 0
    r_drops_required: int = 0
    reason: t.Optional[str] = None


def npc_bypass_quote(
    *, slip: RecipeSlip, has_required_r_drops: int,
    has_gil: int,
) -> NpcBypassQuote:
    """Quote whether the NPC will accept the commission."""
    if has_required_r_drops < NPC_BYPASS_R_DROPS_REQUIRED:
        return NpcBypassQuote(
            False,
            gil_cost=NPC_BYPASS_GIL_COST,
            days_required=NPC_BYPASS_DAYS,
            r_drops_required=NPC_BYPASS_R_DROPS_REQUIRED,
            reason="missing R-drop materials",
        )
    if has_gil < NPC_BYPASS_GIL_COST:
        return NpcBypassQuote(
            False,
            gil_cost=NPC_BYPASS_GIL_COST,
            days_required=NPC_BYPASS_DAYS,
            r_drops_required=NPC_BYPASS_R_DROPS_REQUIRED,
            reason="insufficient gil",
        )
    return NpcBypassQuote(
        accepted=True,
        gil_cost=NPC_BYPASS_GIL_COST,
        days_required=NPC_BYPASS_DAYS,
        r_drops_required=NPC_BYPASS_R_DROPS_REQUIRED,
    )


__all__ = [
    "MAX_CONTRIBUTORS",
    "NPC_BYPASS_DAYS", "NPC_BYPASS_R_DROPS_REQUIRED",
    "NPC_BYPASS_GIL_COST",
    "StorageKind",
    "MaterialEntry", "CraftRequirement",
    "WorkbenchSession",
    "StartResult", "ExecuteResult", "NpcBypassQuote",
    "open_session", "load_slip", "add_contributor",
    "gather_materials", "execute_synth", "cancel_session",
    "npc_bypass_quote",
]
