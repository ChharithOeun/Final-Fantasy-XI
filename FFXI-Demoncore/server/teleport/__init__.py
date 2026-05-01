"""Teleport — warp gating with crystal cost + Honor/Reputation rules.

Vana'diel teleporting comes in flavors:
  - Crystal teleports: Mea, Holla, Dem (require attuned crystal)
  - Outpost warps: nation-controlled, requires nation conquest level
  - Airship/chocobo: gil cost + zone unlock
  - Home Point: free, but only to attuned points

Each TeleportNode declares its requirements: MP cost, gil cost,
attunement quest_id, minimum honor/reputation, and any zone unlock
prereqs. The request_teleport function checks all of them.

Public surface
--------------
    TeleportKind enum (crystal/outpost/airship/chocobo/home_point)
    TeleportNode immutable spec with cost + requirements
    TELEPORT_CATALOG sample registered nodes
    TeleportRequest / TeleportResult
    request_teleport(...)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TeleportKind(str, enum.Enum):
    CRYSTAL = "crystal"        # WHM Teleport spell
    OUTPOST = "outpost"        # Nation outpost warp
    AIRSHIP = "airship"
    CHOCOBO = "chocobo"
    HOME_POINT = "home_point"
    SPELL = "spell"            # Warp/Recall


@dataclasses.dataclass(frozen=True)
class TeleportNode:
    node_id: str
    label: str
    destination_zone_id: str
    kind: TeleportKind
    mp_cost: int = 0
    gil_cost: int = 0
    attunement_quest_id: t.Optional[str] = None
    nation: str = "neutral"
    min_honor: int = 0
    min_reputation: int = 0


# Sample catalog
TELEPORT_CATALOG: tuple[TeleportNode, ...] = (
    # Crystal teleports
    TeleportNode("teleport_mea", "Teleport-Mea",
                 destination_zone_id="tahrongi_canyon",
                 kind=TeleportKind.CRYSTAL, mp_cost=100,
                 attunement_quest_id="mea_crystal"),
    TeleportNode("teleport_holla", "Teleport-Holla",
                 destination_zone_id="la_theine_plateau",
                 kind=TeleportKind.CRYSTAL, mp_cost=100,
                 attunement_quest_id="holla_crystal"),
    TeleportNode("teleport_dem", "Teleport-Dem",
                 destination_zone_id="konschtat_highlands",
                 kind=TeleportKind.CRYSTAL, mp_cost=100,
                 attunement_quest_id="dem_crystal"),
    # Bastok outposts
    TeleportNode("op_north_gusta", "Bastok OP - North Gustaberg",
                 destination_zone_id="north_gustaberg",
                 kind=TeleportKind.OUTPOST, gil_cost=200,
                 nation="bastok"),
    TeleportNode("op_pashhow", "Bastok OP - Pashhow",
                 destination_zone_id="pashhow_marshlands",
                 kind=TeleportKind.OUTPOST, gil_cost=400,
                 nation="bastok", min_reputation=2),
    # Sandy outposts
    TeleportNode("op_jugner", "Sandy OP - Jugner Forest",
                 destination_zone_id="jugner_forest",
                 kind=TeleportKind.OUTPOST, gil_cost=300,
                 nation="sandy", min_reputation=2),
    # Airship
    TeleportNode("airship_jeuno_bastok", "Airship - Jeuno to Bastok",
                 destination_zone_id="bastok_markets",
                 kind=TeleportKind.AIRSHIP, gil_cost=200,
                 attunement_quest_id="airship_pass"),
    # Chocobo (free travel between adjacent zones)
    TeleportNode("chocobo_south_gusta", "Chocobo to South Gustaberg",
                 destination_zone_id="south_gustaberg",
                 kind=TeleportKind.CHOCOBO, gil_cost=100),
    # Spells
    TeleportNode("warp", "Warp",
                 destination_zone_id="home_point",
                 kind=TeleportKind.SPELL, mp_cost=22),
    TeleportNode("home_point_aht", "HP - Aht Urhgan Whitegate",
                 destination_zone_id="aht_urhgan_whitegate",
                 kind=TeleportKind.HOME_POINT,
                 attunement_quest_id="aht_hp_unlock"),
)

NODES_BY_ID: dict[str, TeleportNode] = {
    n.node_id: n for n in TELEPORT_CATALOG
}


@dataclasses.dataclass(frozen=True)
class TeleportRequest:
    player_id: str
    node_id: str
    current_mp: int = 9999
    current_gil: int = 999_999_999
    completed_quests: tuple[str, ...] = ()
    honor: int = 0
    reputation_by_nation: t.Mapping[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass(frozen=True)
class TeleportResult:
    accepted: bool
    node_id: str
    destination_zone_id: t.Optional[str] = None
    mp_charged: int = 0
    gil_charged: int = 0
    reason: t.Optional[str] = None


def request_teleport(req: TeleportRequest) -> TeleportResult:
    node = NODES_BY_ID.get(req.node_id)
    if node is None:
        return TeleportResult(False, req.node_id, reason="unknown node")
    if node.attunement_quest_id and \
            node.attunement_quest_id not in req.completed_quests:
        return TeleportResult(
            False, req.node_id,
            reason=f"missing attunement: {node.attunement_quest_id}",
        )
    if req.current_mp < node.mp_cost:
        return TeleportResult(
            False, req.node_id,
            reason=f"insufficient MP (need {node.mp_cost})",
        )
    if req.current_gil < node.gil_cost:
        return TeleportResult(
            False, req.node_id,
            reason=f"insufficient gil (need {node.gil_cost})",
        )
    if req.honor < node.min_honor:
        return TeleportResult(
            False, req.node_id,
            reason=f"honor {req.honor} below {node.min_honor}",
        )
    if node.nation != "neutral":
        rep = req.reputation_by_nation.get(node.nation, 0)
        if rep < node.min_reputation:
            return TeleportResult(
                False, req.node_id,
                reason=(
                    f"{node.nation} rep {rep} < {node.min_reputation}"
                ),
            )
    return TeleportResult(
        accepted=True,
        node_id=req.node_id,
        destination_zone_id=node.destination_zone_id,
        mp_charged=node.mp_cost,
        gil_charged=node.gil_cost,
    )


def nodes_available_to(req: TeleportRequest) -> tuple[TeleportNode, ...]:
    """All teleport nodes the player meets prereqs for."""
    out = []
    for node in TELEPORT_CATALOG:
        check_req = TeleportRequest(
            player_id=req.player_id, node_id=node.node_id,
            current_mp=req.current_mp, current_gil=req.current_gil,
            completed_quests=req.completed_quests,
            honor=req.honor,
            reputation_by_nation=req.reputation_by_nation,
        )
        if request_teleport(check_req).accepted:
            out.append(node)
    return tuple(out)


__all__ = [
    "TeleportKind", "TeleportNode",
    "TELEPORT_CATALOG", "NODES_BY_ID",
    "TeleportRequest", "TeleportResult",
    "request_teleport", "nodes_available_to",
]
