"""Name plate system — render plates above players & mobs.

A floating tag above each entity displays:
* display_name
* level (or "?" when player level is too low for visible_health
  to reveal)
* faction/nation color
* role badge (party member / linkshell / outlaw / NM star)
* HP estimate band (FULL / WOUNDED / BLOODIED / NEAR_DEATH)
* job icon (player only)

For mobs the visible_health system already specifies the HP
GRAMMAR — this module bridges that with on-screen text. A
viewer's WIDESCAN level affects whether mob HP bands are
shown numerically or by color only.

Public surface
--------------
    PlateKind enum
    PlateBadge enum
    HPBand enum
    NamePlate dataclass
    NamePlateSystem
        .upsert_player(entity_id, name, level, nation, job, badges)
        .upsert_mob(entity_id, name, level, faction, is_nm)
        .update_hp_band(entity_id, band)
        .plates_in_zone(zone_id, viewer_id) -> tuple[NamePlate]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PlateKind(str, enum.Enum):
    PLAYER = "player"
    PARTY_MEMBER = "party_member"
    MOB = "mob"
    NM = "nm"
    NPC = "npc"


class PlateBadge(str, enum.Enum):
    PARTY = "party"
    LINKSHELL = "linkshell"
    OUTLAW = "outlaw"
    MENTOR = "mentor"
    NEW_PLAYER = "new_player"
    NM_STAR = "nm_star"
    GM = "gm"


class HPBand(str, enum.Enum):
    FULL = "full"
    LIGHTLY_WOUNDED = "lightly_wounded"
    WOUNDED = "wounded"
    BLOODIED = "bloodied"
    NEAR_DEATH = "near_death"


# Color hint per nation (for plates).
_NATION_COLOR: dict[str, str] = {
    "bastok": "yellow",
    "san_doria": "blue",
    "windurst": "magenta",
    "jeuno": "white",
    "norg": "teal",
    "tavnazia": "lime",
    "fomor": "violet",
}


_HP_BAND_COLOR: dict[HPBand, str] = {
    HPBand.FULL: "green",
    HPBand.LIGHTLY_WOUNDED: "lime",
    HPBand.WOUNDED: "yellow",
    HPBand.BLOODIED: "orange",
    HPBand.NEAR_DEATH: "red",
}


@dataclasses.dataclass
class NamePlate:
    entity_id: str
    kind: PlateKind
    display_name: str
    level: int
    zone_id: str
    nation: str = ""
    job_code: str = ""
    is_nm: bool = False
    badges: list[PlateBadge] = dataclasses.field(
        default_factory=list,
    )
    hp_band: HPBand = HPBand.FULL
    nation_color: str = ""
    hp_color: str = "green"


@dataclasses.dataclass
class NamePlateSystem:
    _plates: dict[str, NamePlate] = dataclasses.field(
        default_factory=dict,
    )
    # viewer_id -> set of party member ids for plate badge promotion
    _party_membership: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)

    def _color_for(self, nation: str) -> str:
        return _NATION_COLOR.get(nation, "white")

    def upsert_player(
        self, *, entity_id: str, display_name: str,
        level: int, nation: str = "",
        zone_id: str = "",
        job_code: str = "",
        badges: t.Iterable[PlateBadge] = (),
    ) -> NamePlate:
        plate = self._plates.get(entity_id)
        if plate is None:
            plate = NamePlate(
                entity_id=entity_id,
                kind=PlateKind.PLAYER,
                display_name=display_name,
                level=level, zone_id=zone_id,
            )
            self._plates[entity_id] = plate
        plate.display_name = display_name
        plate.level = level
        plate.nation = nation
        plate.zone_id = zone_id
        plate.job_code = job_code
        plate.badges = list(badges)
        plate.nation_color = self._color_for(nation)
        return plate

    def upsert_mob(
        self, *, entity_id: str, display_name: str,
        level: int, faction: str = "",
        zone_id: str = "",
        is_nm: bool = False,
    ) -> NamePlate:
        plate = self._plates.get(entity_id)
        if plate is None:
            plate = NamePlate(
                entity_id=entity_id,
                kind=(PlateKind.NM if is_nm else PlateKind.MOB),
                display_name=display_name,
                level=level, zone_id=zone_id,
            )
            self._plates[entity_id] = plate
        plate.display_name = display_name
        plate.level = level
        plate.zone_id = zone_id
        plate.nation = faction
        plate.is_nm = is_nm
        plate.kind = (
            PlateKind.NM if is_nm else PlateKind.MOB
        )
        plate.nation_color = self._color_for(faction)
        if is_nm and PlateBadge.NM_STAR not in plate.badges:
            plate.badges = list(plate.badges) + [
                PlateBadge.NM_STAR,
            ]
        return plate

    def update_hp_band(
        self, *, entity_id: str, band: HPBand,
    ) -> bool:
        plate = self._plates.get(entity_id)
        if plate is None:
            return False
        plate.hp_band = band
        plate.hp_color = _HP_BAND_COLOR[band]
        return True

    def add_badge(
        self, *, entity_id: str, badge: PlateBadge,
    ) -> bool:
        plate = self._plates.get(entity_id)
        if plate is None:
            return False
        if badge not in plate.badges:
            plate.badges.append(badge)
        return True

    def remove_badge(
        self, *, entity_id: str, badge: PlateBadge,
    ) -> bool:
        plate = self._plates.get(entity_id)
        if plate is None:
            return False
        if badge in plate.badges:
            plate.badges.remove(badge)
            return True
        return False

    def declare_party(
        self, *, viewer_id: str,
        member_ids: t.Iterable[str],
    ) -> bool:
        ids = set(member_ids)
        ids.add(viewer_id)
        for pid in ids:
            self._party_membership[pid] = ids
        return True

    def plate(
        self, entity_id: str,
    ) -> t.Optional[NamePlate]:
        return self._plates.get(entity_id)

    def plates_in_zone(
        self, *, zone_id: str, viewer_id: str,
    ) -> tuple[NamePlate, ...]:
        out: list[NamePlate] = []
        party = self._party_membership.get(
            viewer_id, set(),
        )
        for plate in self._plates.values():
            if plate.zone_id != zone_id:
                continue
            kind = plate.kind
            badges = list(plate.badges)
            # Promote to PARTY_MEMBER for the viewer
            if (
                plate.kind == PlateKind.PLAYER
                and plate.entity_id in party
                and plate.entity_id != viewer_id
            ):
                kind = PlateKind.PARTY_MEMBER
                if PlateBadge.PARTY not in badges:
                    badges.append(PlateBadge.PARTY)
            promoted = NamePlate(
                entity_id=plate.entity_id,
                kind=kind,
                display_name=plate.display_name,
                level=plate.level,
                zone_id=plate.zone_id,
                nation=plate.nation,
                job_code=plate.job_code,
                is_nm=plate.is_nm,
                badges=badges,
                hp_band=plate.hp_band,
                nation_color=plate.nation_color,
                hp_color=plate.hp_color,
            )
            out.append(promoted)
        return tuple(out)

    def total_plates(self) -> int:
        return len(self._plates)


__all__ = [
    "PlateKind", "PlateBadge", "HPBand",
    "NamePlate",
    "NamePlateSystem",
]
