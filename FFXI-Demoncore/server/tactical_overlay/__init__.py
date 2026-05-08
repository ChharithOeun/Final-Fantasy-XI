"""Tactical overlay — chess-board battlefield read.

When a player is in TACTICAL or TOP_DOWN, normal-scale
character models are too small to read. The overlay
projects a flattened, simplified read-out of the
battlefield onto the camera plane:

    mob silhouettes    one icon per mob, colored by
                       con (easy/decent/tough/etc.)
    AOE rings          the AOE telegraphs from
                       aoe_telegraph projected as flat
                       rings on the floor
    party dots         each party member as a colored
                       dot with a job glyph
    range circles      attack/spell range circles around
                       the player (target-pull guidance)

Privacy is preserved: a sneaked / invisible / disguised
entity that the player CAN'T see in third-person
ALSO doesn't appear on the overlay. If you can't see
the THF behind you in over-shoulder, you can't see them
in chess view either. The reveal predicate is supplied
by the caller (sneak_invisible / disguise_system).

Mob count cap: 50 mobs in the overlay at once. If there
are 60 mobs in detection range, we show the 50 closest
to the player. Performance + UI clarity.

Public surface
--------------
    OverlayItemKind enum
    ConTier enum  (5 difficulty tiers; matches
                   minimap_difficulty_check style)
    OverlayItem dataclass (frozen)
    OverlayFrame dataclass (frozen)
    TacticalOverlay
        .build_frame(player_id, mobs, aoes, party,
                     range_circles, reveal_predicate)
            -> OverlayFrame
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_MOBS = 50


class OverlayItemKind(str, enum.Enum):
    MOB = "mob"
    AOE = "aoe"
    PARTY = "party"
    RANGE_CIRCLE = "range_circle"


class ConTier(str, enum.Enum):
    TRIVIAL = "trivial"        # too weak to give XP
    EASY = "easy"
    DECENT = "decent"
    TOUGH = "tough"
    DEADLY = "deadly"


@dataclasses.dataclass(frozen=True)
class OverlayItem:
    kind: OverlayItemKind
    entity_id: str            # mob_id / player_id / aoe_id
    x: float                  # world-relative position
    y: float
    radius: float             # for AOE/range circles; 0 otherwise
    label: str                # icon/glyph hint
    con_tier: str             # "" unless MOB; ConTier value


@dataclasses.dataclass(frozen=True)
class OverlayFrame:
    player_id: str
    items: tuple[OverlayItem, ...]
    truncated_mobs: bool       # True if mob list got
                               # capped at _MAX_MOBS


@dataclasses.dataclass
class _MobRef:
    mob_id: str
    x: float
    y: float
    distance_to_player: float
    con_tier: ConTier


@dataclasses.dataclass
class _AoeRef:
    aoe_id: str
    x: float
    y: float
    radius: float


@dataclasses.dataclass
class _PartyRef:
    player_id: str
    x: float
    y: float
    job: str


@dataclasses.dataclass
class _RangeCircle:
    label: str          # "melee", "spell", etc.
    x: float            # usually = player position
    y: float
    radius: float


@dataclasses.dataclass
class TacticalOverlay:

    @staticmethod
    def build_frame(
        *, player_id: str,
        mobs: list[_MobRef],
        aoes: list[_AoeRef],
        party: list[_PartyRef],
        range_circles: list[_RangeCircle],
        reveal_predicate: t.Callable[[str], bool],
    ) -> OverlayFrame:
        """Build a frame for player_id.

        reveal_predicate(entity_id) returns True if the
        entity is visible to player_id (i.e. not hidden
        by sneak/invis/disguise from this player's POV).
        """
        items: list[OverlayItem] = []
        # Mobs: filter via predicate, sort by distance,
        # cap at _MAX_MOBS
        visible_mobs = [
            m for m in mobs
            if reveal_predicate(m.mob_id)
        ]
        visible_mobs.sort(key=lambda m: m.distance_to_player)
        truncated = len(visible_mobs) > _MAX_MOBS
        for m in visible_mobs[:_MAX_MOBS]:
            items.append(OverlayItem(
                kind=OverlayItemKind.MOB,
                entity_id=m.mob_id, x=m.x, y=m.y,
                radius=0.0, label="mob",
                con_tier=m.con_tier.value,
            ))
        # AOEs: always shown (telegraphs are public)
        for a in aoes:
            items.append(OverlayItem(
                kind=OverlayItemKind.AOE,
                entity_id=a.aoe_id, x=a.x, y=a.y,
                radius=a.radius, label="aoe",
                con_tier="",
            ))
        # Party: predicate filters too (in case a party
        # member is in disguise; also self always shown)
        for pm in party:
            if pm.player_id != player_id:
                if not reveal_predicate(pm.player_id):
                    continue
            items.append(OverlayItem(
                kind=OverlayItemKind.PARTY,
                entity_id=pm.player_id, x=pm.x, y=pm.y,
                radius=0.0, label=pm.job, con_tier="",
            ))
        # Range circles
        for rc in range_circles:
            items.append(OverlayItem(
                kind=OverlayItemKind.RANGE_CIRCLE,
                entity_id=rc.label, x=rc.x, y=rc.y,
                radius=rc.radius, label=rc.label,
                con_tier="",
            ))
        return OverlayFrame(
            player_id=player_id,
            items=tuple(items),
            truncated_mobs=truncated,
        )


__all__ = [
    "OverlayItemKind", "ConTier", "OverlayItem",
    "OverlayFrame",
    # public test helpers also exported so callers can
    # build refs to pass in
    "_MobRef", "_AoeRef", "_PartyRef", "_RangeCircle",
    "TacticalOverlay",
]
