"""Environment hazards — consequences when features break.

When a feature in the arena_environment crosses its break
threshold, it fires a BreakEvent. This module turns that
event into concrete in-fight CONSEQUENCES that affect
players in radius:

    FLOOR_COLLAPSE → fall damage to all in radius;
                     players are dropped to a lower band
                     (continue fighting in the basement)
    ICE_BREAK      → players go from "standing on ice"
                     to "submerged under cold water" with
                     a forced swim-up timer; risk of
                     FROST_SLEEP
    CEILING_CRUMBLE→ debris damage + STUN to all in
                     radius
    PILLAR_FALL    → directional crush along its lean
                     axis + partial floor cave-in
    BRIDGE_SEVER   → splits the party — half stays on
                     this side, half on the other (until
                     someone repairs or routes around)
    DAM_BURST      → gradual flood (water_line += 1
                     band per N seconds) — pushes mid-
                     band fights underwater
    SHIP_LIST      → once a hull is breached the deck
                     tilts; players slide; a 2nd breach
                     starts taking on water faster
    WALL_BREACH    → exposes a new sub-zone (handled in
                     habitat_disturbance)

Each hazard tags the affected players with the
appropriate effect: damage, knockback, status, or band
relocation.

Public surface
--------------
    HazardKind enum
    HazardEffect dataclass (frozen)
    PlayerEffect dataclass (frozen)
    EnvironmentHazards
        .__init__()
        .resolve_break(arena_id, feature_id,
                       feature_kind, players_in_radius,
                       feature_band) -> tuple[PlayerEffect, ...]
        .resolve_crack(...) -> tuple[PlayerEffect, ...]

Players are passed in as (player_id, band) tuples — the
hazard module doesn't own player state, only emits effects
the combat layer applies.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import FeatureKind, FeatureState


class HazardKind(str, enum.Enum):
    FLOOR_COLLAPSE = "floor_collapse"
    ICE_BREAK = "ice_break"
    CEILING_CRUMBLE = "ceiling_crumble"
    PILLAR_FALL = "pillar_fall"
    BRIDGE_SEVER = "bridge_sever"
    DAM_BURST = "dam_burst"
    SHIP_LIST = "ship_list"
    WALL_BREACH = "wall_breach"


# Default damage/knockback/status numbers
FLOOR_FALL_DAMAGE = 800
ICE_BREAK_FROST_SLEEP_SECONDS = 12
ICE_BREAK_DROWN_TIMER_SECONDS = 60
CEILING_DEBRIS_DAMAGE = 600
CEILING_STUN_SECONDS = 4
PILLAR_CRUSH_DAMAGE = 1500
DAM_FLOOD_BAND_SECONDS = 30   # 30s per 1 band rise
SHIP_LIST_SLIDE_YALMS = 8


@dataclasses.dataclass(frozen=True)
class PlayerEffect:
    player_id: str
    hazard: HazardKind
    damage: int = 0
    knockback_yalms: int = 0
    status_id: t.Optional[str] = None
    status_seconds: int = 0
    band_change: int = 0     # negative = drop down, positive = rise
    drown_timer_seconds: int = 0
    notes: str = ""


# Map FeatureKind → corresponding HazardKind on hard break
_BREAK_MAP: dict[FeatureKind, HazardKind] = {
    FeatureKind.FLOOR: HazardKind.FLOOR_COLLAPSE,
    FeatureKind.ICE_SHEET: HazardKind.ICE_BREAK,
    FeatureKind.CEILING: HazardKind.CEILING_CRUMBLE,
    FeatureKind.PILLAR: HazardKind.PILLAR_FALL,
    FeatureKind.BRIDGE: HazardKind.BRIDGE_SEVER,
    FeatureKind.DAM: HazardKind.DAM_BURST,
    FeatureKind.SHIP_HULL: HazardKind.SHIP_LIST,
    FeatureKind.WALL: HazardKind.WALL_BREACH,
}


@dataclasses.dataclass
class EnvironmentHazards:

    def resolve_break(
        self, *, arena_id: str, feature_id: str,
        feature_kind: FeatureKind,
        feature_band: int,
        players_in_radius: t.Iterable[tuple[str, int]],
    ) -> tuple[PlayerEffect, ...]:
        hazard = _BREAK_MAP.get(feature_kind)
        if hazard is None:
            return ()
        plist = [(pid, b) for pid, b in players_in_radius if pid]
        if not plist:
            return ()
        out: list[PlayerEffect] = []
        for pid, pband in plist:
            if hazard == HazardKind.FLOOR_COLLAPSE:
                # everyone on or above the floor falls one band
                if pband >= feature_band:
                    out.append(PlayerEffect(
                        player_id=pid, hazard=hazard,
                        damage=FLOOR_FALL_DAMAGE,
                        band_change=-1,
                        notes="floor caved in",
                    ))
            elif hazard == HazardKind.ICE_BREAK:
                if pband == feature_band:
                    out.append(PlayerEffect(
                        player_id=pid, hazard=hazard,
                        status_id="frost_sleep",
                        status_seconds=ICE_BREAK_FROST_SLEEP_SECONDS,
                        drown_timer_seconds=(
                            ICE_BREAK_DROWN_TIMER_SECONDS
                        ),
                        band_change=-1,   # plunged below ice
                        notes="ice broke under foot",
                    ))
            elif hazard == HazardKind.CEILING_CRUMBLE:
                if pband <= feature_band:
                    out.append(PlayerEffect(
                        player_id=pid, hazard=hazard,
                        damage=CEILING_DEBRIS_DAMAGE,
                        status_id="stun",
                        status_seconds=CEILING_STUN_SECONDS,
                        notes="debris from above",
                    ))
            elif hazard == HazardKind.PILLAR_FALL:
                if pband == feature_band:
                    out.append(PlayerEffect(
                        player_id=pid, hazard=hazard,
                        damage=PILLAR_CRUSH_DAMAGE,
                        knockback_yalms=10,
                        notes="pillar crash zone",
                    ))
            elif hazard == HazardKind.BRIDGE_SEVER:
                # 50/50 cut — emit a side tag the combat layer
                # uses to split the party
                out.append(PlayerEffect(
                    player_id=pid, hazard=hazard,
                    notes="bridge severed — party split",
                ))
            elif hazard == HazardKind.DAM_BURST:
                # flood will climb 1 band per DAM_FLOOD_BAND_SECONDS
                out.append(PlayerEffect(
                    player_id=pid, hazard=hazard,
                    notes=f"flood rising {DAM_FLOOD_BAND_SECONDS}s/band",
                ))
            elif hazard == HazardKind.SHIP_LIST:
                out.append(PlayerEffect(
                    player_id=pid, hazard=hazard,
                    knockback_yalms=SHIP_LIST_SLIDE_YALMS,
                    notes="deck tilting",
                ))
            elif hazard == HazardKind.WALL_BREACH:
                # tagging only — habitat_disturbance handles spawns
                out.append(PlayerEffect(
                    player_id=pid, hazard=hazard,
                    notes="wall breached",
                ))
        return tuple(out)

    def resolve_crack(
        self, *, arena_id: str, feature_id: str,
        feature_kind: FeatureKind,
        feature_band: int,
        players_in_radius: t.Iterable[tuple[str, int]],
    ) -> tuple[PlayerEffect, ...]:
        """A cracked-but-not-broken feature still fires soft
        warnings — the combat layer can play sound + show an
        AOE_TELEGRAPH so players know to move."""
        hazard = _BREAK_MAP.get(feature_kind)
        if hazard is None:
            return ()
        out: list[PlayerEffect] = []
        for pid, pband in players_in_radius:
            if not pid:
                continue
            if abs(pband - feature_band) > 1:
                continue
            out.append(PlayerEffect(
                player_id=pid, hazard=hazard,
                notes=f"warning: {feature_id} cracked",
            ))
        return tuple(out)


__all__ = [
    "HazardKind", "PlayerEffect", "EnvironmentHazards",
    "FLOOR_FALL_DAMAGE", "ICE_BREAK_FROST_SLEEP_SECONDS",
    "ICE_BREAK_DROWN_TIMER_SECONDS",
    "CEILING_DEBRIS_DAMAGE", "CEILING_STUN_SECONDS",
    "PILLAR_CRUSH_DAMAGE", "DAM_FLOOD_BAND_SECONDS",
    "SHIP_LIST_SLIDE_YALMS",
]
