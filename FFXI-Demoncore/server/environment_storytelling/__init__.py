"""Environment storytelling — read the world without dialogue.

In retail FFXI a ruin is just geometry. In Demoncore a
ruin is a CHAPTER. Walk up to a half-buried statue and
you can examine it; the world tells you who built this
place, what they believed, why it failed. Lore is in
the world itself, not just in NPCs.

We catalog StoryProps placed by level designers. Each
one has:
    prop_id     stable identifier
    zone_id     which zone it lives in
    kind        STATUE / TABLET / MURAL / RUIN / SHRINE
                / GRAVE / BANNER / BOOK_PILE / RELIC
    title       what the player sees in the inspect tooltip
    body        the lore text revealed on read
    fame_unlock optional — text only available after the
                player hits a fame level in some city
    research_value the research_log credit when first
                read (and a "discoverer" badge if first
                across the server)

Per-player progression: the prop is "discovered" the
first time read; subsequent reads display the body
again but credit nothing new. is_discovered() is the
indexed lookup the UI uses to display "(NEW)" markers
for unread props in a zone.

Public surface
--------------
    PropKind enum
    StoryProp dataclass (frozen)
    ReadResult dataclass (frozen)
    EnvironmentStorytelling
        .register_prop(prop) -> bool
        .read(player_id, prop_id, fame_levels) -> Optional[ReadResult]
        .is_discovered(player_id, prop_id) -> bool
        .props_in_zone(zone_id) -> list[StoryProp]
        .undiscovered_in_zone(player_id, zone_id) -> list[StoryProp]
        .discoverer(prop_id) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PropKind(str, enum.Enum):
    STATUE = "statue"
    TABLET = "tablet"
    MURAL = "mural"
    RUIN = "ruin"
    SHRINE = "shrine"
    GRAVE = "grave"
    BANNER = "banner"
    BOOK_PILE = "book_pile"
    RELIC = "relic"


@dataclasses.dataclass(frozen=True)
class StoryProp:
    prop_id: str
    zone_id: str
    kind: PropKind
    title: str
    body: str
    fame_unlock: t.Optional[tuple[str, int]] = None
    research_value: int = 1


@dataclasses.dataclass(frozen=True)
class ReadResult:
    prop_id: str
    title: str
    body: str
    is_first_discovery: bool
    research_credited: int
    is_server_first_discoverer: bool


@dataclasses.dataclass
class EnvironmentStorytelling:
    _props: dict[str, StoryProp] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, prop_id) -> True if discovered
    _discovered: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    # prop_id -> player_id of FIRST discoverer
    _first: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_prop(self, prop: StoryProp) -> bool:
        if not prop.prop_id or not prop.zone_id:
            return False
        if not prop.title or not prop.body:
            return False
        if prop.research_value < 0:
            return False
        if prop.prop_id in self._props:
            return False
        self._props[prop.prop_id] = prop
        return True

    def read(
        self, *, player_id: str, prop_id: str,
        fame_levels: t.Optional[dict[str, int]] = None,
    ) -> t.Optional[ReadResult]:
        if not player_id or prop_id not in self._props:
            return None
        prop = self._props[prop_id]
        if prop.fame_unlock is not None:
            city, needed = prop.fame_unlock
            cur = (fame_levels or {}).get(city, 0)
            if cur < needed:
                return None
        key = (player_id, prop_id)
        is_first = key not in self._discovered
        is_server_first = False
        research = 0
        if is_first:
            self._discovered.add(key)
            research = prop.research_value
            if prop_id not in self._first:
                self._first[prop_id] = player_id
                is_server_first = True
        return ReadResult(
            prop_id=prop_id,
            title=prop.title,
            body=prop.body,
            is_first_discovery=is_first,
            research_credited=research,
            is_server_first_discoverer=is_server_first,
        )

    def is_discovered(
        self, *, player_id: str, prop_id: str,
    ) -> bool:
        return (player_id, prop_id) in self._discovered

    def props_in_zone(
        self, *, zone_id: str,
    ) -> list[StoryProp]:
        return sorted(
            (p for p in self._props.values()
             if p.zone_id == zone_id),
            key=lambda p: p.prop_id,
        )

    def undiscovered_in_zone(
        self, *, player_id: str, zone_id: str,
        fame_levels: t.Optional[dict[str, int]] = None,
    ) -> list[StoryProp]:
        out = []
        for p in self.props_in_zone(zone_id=zone_id):
            if (player_id, p.prop_id) in self._discovered:
                continue
            # Hide fame-locked props the player hasn't unlocked
            if p.fame_unlock is not None:
                city, needed = p.fame_unlock
                cur = (fame_levels or {}).get(city, 0)
                if cur < needed:
                    continue
            out.append(p)
        return out

    def discoverer(
        self, *, prop_id: str,
    ) -> t.Optional[str]:
        return self._first.get(prop_id)


__all__ = [
    "PropKind", "StoryProp", "ReadResult",
    "EnvironmentStorytelling",
]
