"""Character model library — upgraded character catalog.

The casting room's other half. ``voice_role_registry`` owns
who *speaks* for a character; this module owns what they
*look like*. Per-character record carries the full live-
action presentation stack: a four-step LOD set (Nanite-dense
hero through billboard impostor), a PBR material set keyed
by surface (skin / eyes / teeth / hair groom), costume
layers, scar decals, eye anatomy (sclera / iris / cornea
IOR), tooth setup, hair groom URI plus card count for the
fallback hair shader.

The Bastok Markets demo roster — Volker, Cid, Iron Eater,
Naji, Romaa Mihgo, Cornelia, Lhe Lhangavo — plus five
generic crowd archetypes (one per playable race) — fills
out the eleven-character minimum the showcase needs.

Public surface
--------------
    Archetype enum
    LODKind enum
    HairGroomKind enum
    EyeSetup dataclass (frozen)
    ToothSetup dataclass (frozen)
    CostumeLayer dataclass (frozen)
    MeshLODSet dataclass (frozen)
    MaterialSet dataclass (frozen)
    CharacterEntry dataclass (frozen)
    CharacterModelLibrary
    BUILTIN_BASTOK_DEMO tuple
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Archetype(enum.Enum):
    HERO = "hero"
    FLAGSHIP_NPC = "flagship_npc"
    GENERIC_BASTOK = "generic_bastok"
    GENERIC_SANDORIA = "generic_sandoria"
    GENERIC_WINDURST = "generic_windurst"
    GENERIC_JEUNO = "generic_jeuno"
    MOB = "mob"
    BEASTMAN = "beastman"


class LODKind(enum.Enum):
    NANITE_DENSE = "nanite_dense"   # 0-15m hero close-ups
    NANITE_MID = "nanite_mid"       # 15-50m crowd
    CARD_BILLBOARD = "card_billboard"  # 50-150m
    IMPOSTOR = "impostor"            # 150m+


class HairGroomKind(enum.Enum):
    GROOM_STRANDS = "groom_strands"    # full Niagara grooms
    HAIR_CARDS = "hair_cards"          # textured planes
    BAKED_HELMET = "baked_helmet"      # under armour cap


@dataclasses.dataclass(frozen=True)
class EyeSetup:
    """Per-character iris / sclera / cornea spec.

    Cornea IOR is fixed at the human anatomical value
    (1.376) by default; Galka and beastman archetypes can
    override.
    """
    sclera_color_hex: str = "#f6efe2"
    iris_color_hex: str = "#3a4f2c"
    cornea_ior: float = 1.376
    sclera_blood_amount: float = 0.12  # 0..1


@dataclasses.dataclass(frozen=True)
class ToothSetup:
    enamel_color_hex: str = "#f1ead7"
    crowding_factor: float = 0.0  # 0..1 (FFXI Galka tusks > 0)
    plaque_amount: float = 0.05


@dataclasses.dataclass(frozen=True)
class CostumeLayer:
    """One layer of clothing / armour. Layers stack outward —
    skin → undershirt → tabard → cuirass → cape — and the
    physics solver respects the order.
    """
    layer_id: str
    name: str
    material_uri: str
    sort_order: int  # 0 = innermost


@dataclasses.dataclass(frozen=True)
class MeshLODSet:
    """Four LODs, one URI per kind. None means the kind isn't
    authored — falls back to the next-coarser LOD.
    """
    nanite_dense_uri: str
    nanite_mid_uri: str
    card_billboard_uri: str
    impostor_uri: str


@dataclasses.dataclass(frozen=True)
class MaterialSet:
    """The PBR material set keyed by surface. Skin uses
    subsurface; eye uses cornea/iris layered shader; teeth
    use the dental-translucent shader; hair_groom uses the
    Niagara strand shader.
    """
    skin_uri: str
    eye_uri: str
    teeth_uri: str
    hair_groom_uri: str


@dataclasses.dataclass(frozen=True)
class CharacterEntry:
    char_id: str
    display_name: str
    archetype: Archetype
    home_zone_id: str
    mesh_lod_set: MeshLODSet
    material_set: MaterialSet
    costume_layers: tuple[CostumeLayer, ...]
    scar_decals: tuple[str, ...]
    eye_setup: EyeSetup
    tooth_setup: ToothSetup
    hair_groom_kind: HairGroomKind
    hair_groom_uri: str
    hair_card_count: int  # 0 for groom_strands, >0 for cards
    metahuman_link: t.Optional[str] = None
    notes: str = ""


# ----------------------------------------------------------------
# Built-in Bastok Markets demo roster.
# Eleven entries — Volker, Cid, Iron Eater, Naji, Romaa Mihgo,
# Cornelia, Lhe Lhangavo plus four generic race templates.
# ----------------------------------------------------------------
def _lods(name: str) -> MeshLODSet:
    base = f"assets/chars/{name}"
    return MeshLODSet(
        nanite_dense_uri=f"{base}/lod0_nanite.uasset",
        nanite_mid_uri=f"{base}/lod1_nanite.uasset",
        card_billboard_uri=f"{base}/lod2_card.uasset",
        impostor_uri=f"{base}/lod3_impostor.uasset",
    )


def _mats(name: str) -> MaterialSet:
    base = f"assets/chars/{name}/mats"
    return MaterialSet(
        skin_uri=f"{base}/skin.uasset",
        eye_uri=f"{base}/eye.uasset",
        teeth_uri=f"{base}/teeth.uasset",
        hair_groom_uri=f"{base}/hair_groom.uasset",
    )


def _costume(*layers: tuple[str, str, int]) -> tuple[CostumeLayer, ...]:
    return tuple(
        CostumeLayer(
            layer_id=lid,
            name=name,
            material_uri=f"assets/costumes/{lid}.uasset",
            sort_order=order,
        )
        for lid, name, order in layers
    )


BUILTIN_BASTOK_DEMO: tuple[CharacterEntry, ...] = (
    CharacterEntry(
        char_id="volker",
        display_name="Captain Volker",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("volker"),
        material_set=_mats("volker"),
        costume_layers=_costume(
            ("vol_undershirt", "Hume Undershirt", 0),
            ("vol_musketeer_tabard", "Musketeer Tabard", 1),
            ("vol_belt", "Captain's Belt", 2),
            ("vol_pauldron", "Mythril Pauldron", 3),
        ),
        scar_decals=(
            "decal/scar_left_brow.uasset",
            "decal/scar_jaw.uasset",
        ),
        eye_setup=EyeSetup(
            iris_color_hex="#5b3a18",
            sclera_blood_amount=0.18,
        ),
        tooth_setup=ToothSetup(plaque_amount=0.10),
        hair_groom_kind=HairGroomKind.GROOM_STRANDS,
        hair_groom_uri="assets/grooms/volker_short.uasset",
        hair_card_count=0,
        metahuman_link="mh_volker_v2",
    ),
    CharacterEntry(
        char_id="cid",
        display_name="Cid",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("cid"),
        material_set=_mats("cid"),
        costume_layers=_costume(
            ("cid_workshirt", "Engineer Workshirt", 0),
            ("cid_apron", "Soot-stained Apron", 1),
            ("cid_glove_left", "Forge Glove L", 2),
            ("cid_goggles", "Brass Goggles", 3),
        ),
        scar_decals=("decal/burn_left_forearm.uasset",),
        eye_setup=EyeSetup(iris_color_hex="#3a3327"),
        tooth_setup=ToothSetup(plaque_amount=0.07),
        hair_groom_kind=HairGroomKind.GROOM_STRANDS,
        hair_groom_uri="assets/grooms/cid_balding.uasset",
        hair_card_count=0,
        metahuman_link="mh_cid_v2",
    ),
    CharacterEntry(
        char_id="iron_eater",
        display_name="Iron Eater",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("iron_eater"),
        material_set=_mats("iron_eater"),
        costume_layers=_costume(
            ("ie_loincloth", "Iron Loincloth", 0),
            ("ie_tribal_belt", "Galka Tribal Belt", 1),
            ("ie_axe_strap", "Greataxe Strap", 2),
        ),
        scar_decals=(
            "decal/galka_chest_brand.uasset",
            "decal/galka_neck_scar.uasset",
        ),
        eye_setup=EyeSetup(
            iris_color_hex="#a02c20",
            sclera_color_hex="#e4d7be",
            cornea_ior=1.40,  # Galka cornea slightly thicker
            sclera_blood_amount=0.32,
        ),
        tooth_setup=ToothSetup(
            enamel_color_hex="#dccfa3",
            crowding_factor=0.45,  # Galka tusks
            plaque_amount=0.18,
        ),
        hair_groom_kind=HairGroomKind.GROOM_STRANDS,
        hair_groom_uri="assets/grooms/galka_topknot.uasset",
        hair_card_count=0,
        metahuman_link="mh_iron_eater_v1",
    ),
    CharacterEntry(
        char_id="naji",
        display_name="Naji",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("naji"),
        material_set=_mats("naji"),
        costume_layers=_costume(
            ("naji_shirt", "Linen Shirt", 0),
            ("naji_vest", "Mercenary Vest", 1),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#274a2f"),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/naji_cards.uasset",
        hair_card_count=180,
    ),
    CharacterEntry(
        char_id="romaa_mihgo",
        display_name="Romaa Mihgo",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("romaa_mihgo"),
        material_set=_mats("romaa_mihgo"),
        costume_layers=_costume(
            ("romaa_top", "Mithra Cropped Top", 0),
            ("romaa_belt", "Treasure Hunter Belt", 1),
            ("romaa_dagger_sheath", "Dagger Sheath", 2),
        ),
        scar_decals=("decal/mithra_paw_nick.uasset",),
        eye_setup=EyeSetup(
            iris_color_hex="#d4a017",
            sclera_blood_amount=0.10,
        ),
        tooth_setup=ToothSetup(crowding_factor=0.10),
        hair_groom_kind=HairGroomKind.GROOM_STRANDS,
        hair_groom_uri="assets/grooms/mithra_long.uasset",
        hair_card_count=0,
        metahuman_link="mh_romaa_v1",
    ),
    CharacterEntry(
        char_id="cornelia",
        display_name="Cornelia",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("cornelia"),
        material_set=_mats("cornelia"),
        costume_layers=_costume(
            ("cornelia_dress", "Markets Sundress", 0),
            ("cornelia_apron", "Vendor Apron", 1),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#264653"),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.GROOM_STRANDS,
        hair_groom_uri="assets/grooms/cornelia_braid.uasset",
        hair_card_count=0,
    ),
    CharacterEntry(
        char_id="lhe_lhangavo",
        display_name="Lhe Lhangavo",
        archetype=Archetype.FLAGSHIP_NPC,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("lhe_lhangavo"),
        material_set=_mats("lhe_lhangavo"),
        costume_layers=_costume(
            ("lhe_robe", "Mithran Vendor Robe", 0),
            ("lhe_shawl", "Pelt Shawl", 1),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#7d8a3a"),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/mithra_short_cards.uasset",
        hair_card_count=140,
    ),
    # Generic background crowd templates.
    CharacterEntry(
        char_id="generic_galka_smith",
        display_name="Galka Smith (Generic)",
        archetype=Archetype.GENERIC_BASTOK,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("generic_galka_smith"),
        material_set=_mats("generic_galka_smith"),
        costume_layers=_costume(
            ("gen_smith_apron", "Smith Apron", 0),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(
            iris_color_hex="#742a1c",
            cornea_ior=1.40,
            sclera_blood_amount=0.28,
        ),
        tooth_setup=ToothSetup(crowding_factor=0.40),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/galka_short_cards.uasset",
        hair_card_count=80,
    ),
    CharacterEntry(
        char_id="generic_hume_engineer",
        display_name="Hume Engineer (Generic)",
        archetype=Archetype.GENERIC_BASTOK,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("generic_hume_engineer"),
        material_set=_mats("generic_hume_engineer"),
        costume_layers=_costume(
            ("gen_eng_overalls", "Engineer Overalls", 0),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/hume_short_cards.uasset",
        hair_card_count=120,
    ),
    CharacterEntry(
        char_id="generic_mithra_musketeer",
        display_name="Mithra Musketeer (Generic)",
        archetype=Archetype.GENERIC_BASTOK,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("generic_mithra_musketeer"),
        material_set=_mats("generic_mithra_musketeer"),
        costume_layers=_costume(
            ("gen_must_tabard", "Musketeer Tabard", 0),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#c48a25"),
        tooth_setup=ToothSetup(crowding_factor=0.10),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/mithra_long_cards.uasset",
        hair_card_count=160,
    ),
    CharacterEntry(
        char_id="generic_taru_apprentice",
        display_name="Tarutaru Apprentice (Generic)",
        archetype=Archetype.GENERIC_BASTOK,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("generic_taru_apprentice"),
        material_set=_mats("generic_taru_apprentice"),
        costume_layers=_costume(
            ("gen_taru_robe", "Apprentice Robe", 0),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#3a5e8a"),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/taru_pigtails_cards.uasset",
        hair_card_count=90,
    ),
    CharacterEntry(
        char_id="generic_elvaan_visitor",
        display_name="Elvaan Visitor (Generic)",
        archetype=Archetype.GENERIC_SANDORIA,
        home_zone_id="bastok_markets",
        mesh_lod_set=_lods("generic_elvaan_visitor"),
        material_set=_mats("generic_elvaan_visitor"),
        costume_layers=_costume(
            ("gen_elv_tunic", "Elvaan Tunic", 0),
        ),
        scar_decals=(),
        eye_setup=EyeSetup(iris_color_hex="#314a7c"),
        tooth_setup=ToothSetup(),
        hair_groom_kind=HairGroomKind.HAIR_CARDS,
        hair_groom_uri="assets/grooms/elvaan_long_cards.uasset",
        hair_card_count=200,
    ),
)


# ----------------------------------------------------------------
# Library
# ----------------------------------------------------------------
@dataclasses.dataclass
class CharacterModelLibrary:
    """Per-character catalog. Mutable registration; immutable
    entries.
    """
    _entries: dict[str, CharacterEntry] = dataclasses.field(
        default_factory=dict,
    )

    @classmethod
    def with_bastok_demo(cls) -> "CharacterModelLibrary":
        lib = cls()
        for entry in BUILTIN_BASTOK_DEMO:
            lib.register_character(entry)
        return lib

    def register_character(
        self, entry: CharacterEntry,
    ) -> CharacterEntry:
        if not entry.char_id:
            raise ValueError("char_id required")
        if entry.char_id in self._entries:
            raise ValueError(
                f"char_id already registered: {entry.char_id}",
            )
        if (
            entry.hair_groom_kind == HairGroomKind.GROOM_STRANDS
            and entry.hair_card_count != 0
        ):
            raise ValueError(
                "groom_strands hair must have card_count == 0",
            )
        if (
            entry.hair_groom_kind == HairGroomKind.HAIR_CARDS
            and entry.hair_card_count <= 0
        ):
            raise ValueError(
                "hair_cards must have card_count > 0",
            )
        self._entries[entry.char_id] = entry
        return entry

    def lookup(self, char_id: str) -> CharacterEntry:
        if char_id not in self._entries:
            raise KeyError(f"unknown char_id: {char_id}")
        return self._entries[char_id]

    def has(self, char_id: str) -> bool:
        return char_id in self._entries

    def all_characters(self) -> tuple[CharacterEntry, ...]:
        return tuple(self._entries.values())

    def characters_for_zone(
        self, zone_id: str,
    ) -> tuple[CharacterEntry, ...]:
        return tuple(
            e for e in self._entries.values()
            if e.home_zone_id == zone_id
        )

    def characters_with_archetype(
        self, archetype: Archetype,
    ) -> tuple[CharacterEntry, ...]:
        return tuple(
            e for e in self._entries.values()
            if e.archetype == archetype
        )

    def demo_roster(self) -> tuple[CharacterEntry, ...]:
        """Bastok-Markets demo roster.

        Returns the eleven flagship + generic crowd templates
        the showcase needs.
        """
        wanted = {e.char_id for e in BUILTIN_BASTOK_DEMO}
        return tuple(
            self._entries[cid] for cid in
            (e.char_id for e in BUILTIN_BASTOK_DEMO)
            if cid in self._entries
        ) if wanted else ()

    def lod_for(
        self, char_id: str, distance_meters: float,
    ) -> tuple[LODKind, str]:
        """Pick the right LOD URI for the camera distance."""
        if distance_meters < 0:
            raise ValueError(
                "distance_meters must be >= 0",
            )
        entry = self.lookup(char_id)
        if distance_meters < 15.0:
            return (
                LODKind.NANITE_DENSE,
                entry.mesh_lod_set.nanite_dense_uri,
            )
        if distance_meters < 50.0:
            return (
                LODKind.NANITE_MID,
                entry.mesh_lod_set.nanite_mid_uri,
            )
        if distance_meters < 150.0:
            return (
                LODKind.CARD_BILLBOARD,
                entry.mesh_lod_set.card_billboard_uri,
            )
        return (
            LODKind.IMPOSTOR,
            entry.mesh_lod_set.impostor_uri,
        )

    def costume_layer_count(self, char_id: str) -> int:
        return len(self.lookup(char_id).costume_layers)

    def linked_to_metahuman(
        self,
    ) -> tuple[CharacterEntry, ...]:
        return tuple(
            e for e in self._entries.values()
            if e.metahuman_link
        )


__all__ = [
    "Archetype", "LODKind", "HairGroomKind",
    "EyeSetup", "ToothSetup", "CostumeLayer",
    "MeshLODSet", "MaterialSet", "CharacterEntry",
    "CharacterModelLibrary",
    "BUILTIN_BASTOK_DEMO",
]
