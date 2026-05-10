"""Tests for character_model_library."""
from __future__ import annotations

import pytest

from server.character_model_library import (
    Archetype,
    BUILTIN_BASTOK_DEMO,
    CharacterEntry,
    CharacterModelLibrary,
    CostumeLayer,
    EyeSetup,
    HairGroomKind,
    LODKind,
    MaterialSet,
    MeshLODSet,
    ToothSetup,
)


def _entry(
    char_id: str = "tester",
    archetype: Archetype = Archetype.HERO,
    hair_kind: HairGroomKind = HairGroomKind.GROOM_STRANDS,
    hair_cards: int = 0,
) -> CharacterEntry:
    return CharacterEntry(
        char_id=char_id,
        display_name="Tester",
        archetype=archetype,
        home_zone_id="bastok_markets",
        mesh_lod_set=MeshLODSet(
            nanite_dense_uri="a.uasset",
            nanite_mid_uri="b.uasset",
            card_billboard_uri="c.uasset",
            impostor_uri="d.uasset",
        ),
        material_set=MaterialSet(
            skin_uri="s.uasset",
            eye_uri="e.uasset",
            teeth_uri="t.uasset",
            hair_groom_uri="h.uasset",
        ),
        costume_layers=(),
        scar_decals=(),
        eye_setup=EyeSetup(),
        tooth_setup=ToothSetup(),
        hair_groom_kind=hair_kind,
        hair_groom_uri="h.uasset",
        hair_card_count=hair_cards,
    )


# ---- Builtin roster ----

def test_demo_roster_has_at_least_11_entries():
    assert len(BUILTIN_BASTOK_DEMO) >= 11


def test_demo_includes_volker():
    ids = [e.char_id for e in BUILTIN_BASTOK_DEMO]
    assert "volker" in ids


def test_demo_includes_cid():
    ids = [e.char_id for e in BUILTIN_BASTOK_DEMO]
    assert "cid" in ids


def test_demo_includes_iron_eater():
    ids = [e.char_id for e in BUILTIN_BASTOK_DEMO]
    assert "iron_eater" in ids


def test_demo_includes_naji_romaa_cornelia_lhe():
    ids = {e.char_id for e in BUILTIN_BASTOK_DEMO}
    for cid in (
        "naji", "romaa_mihgo", "cornelia", "lhe_lhangavo",
    ):
        assert cid in ids


def test_demo_has_generic_archetypes_for_each_race():
    ids = {e.char_id for e in BUILTIN_BASTOK_DEMO}
    assert "generic_galka_smith" in ids
    assert "generic_hume_engineer" in ids
    assert "generic_mithra_musketeer" in ids
    assert "generic_taru_apprentice" in ids


def test_demo_ids_unique():
    ids = [e.char_id for e in BUILTIN_BASTOK_DEMO]
    assert len(set(ids)) == len(ids)


def test_with_bastok_demo_loads_all():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert (
        len(lib.all_characters()) == len(BUILTIN_BASTOK_DEMO)
    )


# ---- Registration ----

def test_register_character_returns_entry():
    lib = CharacterModelLibrary()
    out = lib.register_character(_entry("x"))
    assert out.char_id == "x"


def test_register_duplicate_raises():
    lib = CharacterModelLibrary()
    lib.register_character(_entry("x"))
    with pytest.raises(ValueError):
        lib.register_character(_entry("x"))


def test_register_empty_id_raises():
    lib = CharacterModelLibrary()
    with pytest.raises(ValueError):
        lib.register_character(_entry(""))


def test_register_groom_with_cards_raises():
    lib = CharacterModelLibrary()
    with pytest.raises(ValueError):
        lib.register_character(
            _entry(hair_kind=HairGroomKind.GROOM_STRANDS,
                   hair_cards=120),
        )


def test_register_cards_with_zero_count_raises():
    lib = CharacterModelLibrary()
    with pytest.raises(ValueError):
        lib.register_character(
            _entry(hair_kind=HairGroomKind.HAIR_CARDS,
                   hair_cards=0),
        )


# ---- Lookup ----

def test_lookup_existing():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert lib.lookup("volker").display_name == "Captain Volker"


def test_lookup_unknown_raises():
    lib = CharacterModelLibrary()
    with pytest.raises(KeyError):
        lib.lookup("nope")


def test_has_existing():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert lib.has("cid")


def test_has_unknown():
    lib = CharacterModelLibrary()
    assert not lib.has("nope")


# ---- Filters ----

def test_characters_for_zone():
    lib = CharacterModelLibrary.with_bastok_demo()
    in_markets = lib.characters_for_zone("bastok_markets")
    assert len(in_markets) == len(BUILTIN_BASTOK_DEMO)
    out_zone = lib.characters_for_zone("windurst_woods")
    assert out_zone == ()


def test_characters_with_archetype():
    lib = CharacterModelLibrary.with_bastok_demo()
    flagship = lib.characters_with_archetype(
        Archetype.FLAGSHIP_NPC,
    )
    assert len(flagship) >= 7  # 7 flagship characters
    cids = {e.char_id for e in flagship}
    assert "volker" in cids
    assert "cid" in cids
    assert "iron_eater" in cids


def test_characters_with_archetype_generic_bastok():
    lib = CharacterModelLibrary.with_bastok_demo()
    gen = lib.characters_with_archetype(
        Archetype.GENERIC_BASTOK,
    )
    assert len(gen) >= 4


def test_demo_roster_returns_full_set():
    lib = CharacterModelLibrary.with_bastok_demo()
    roster = lib.demo_roster()
    assert len(roster) == len(BUILTIN_BASTOK_DEMO)


# ---- LOD selection ----

def test_lod_for_close():
    lib = CharacterModelLibrary.with_bastok_demo()
    kind, uri = lib.lod_for("volker", 5.0)
    assert kind == LODKind.NANITE_DENSE
    assert uri.endswith("lod0_nanite.uasset")


def test_lod_for_mid():
    lib = CharacterModelLibrary.with_bastok_demo()
    kind, _ = lib.lod_for("volker", 30.0)
    assert kind == LODKind.NANITE_MID


def test_lod_for_card():
    lib = CharacterModelLibrary.with_bastok_demo()
    kind, _ = lib.lod_for("volker", 100.0)
    assert kind == LODKind.CARD_BILLBOARD


def test_lod_for_impostor():
    lib = CharacterModelLibrary.with_bastok_demo()
    kind, _ = lib.lod_for("volker", 300.0)
    assert kind == LODKind.IMPOSTOR


def test_lod_for_negative_raises():
    lib = CharacterModelLibrary.with_bastok_demo()
    with pytest.raises(ValueError):
        lib.lod_for("volker", -1.0)


def test_lod_for_unknown_char_raises():
    lib = CharacterModelLibrary()
    with pytest.raises(KeyError):
        lib.lod_for("nope", 5.0)


# ---- Costume / metahuman cross-ref ----

def test_costume_layer_count():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert lib.costume_layer_count("volker") >= 4


def test_costume_layers_sort_order_present():
    lib = CharacterModelLibrary.with_bastok_demo()
    layers = lib.lookup("volker").costume_layers
    orders = [l.sort_order for l in layers]
    assert orders == sorted(orders)
    assert orders[0] == 0


def test_metahuman_link_optional():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert lib.lookup("volker").metahuman_link == "mh_volker_v2"
    assert lib.lookup("cornelia").metahuman_link is None


def test_linked_to_metahuman_filters():
    lib = CharacterModelLibrary.with_bastok_demo()
    linked = lib.linked_to_metahuman()
    cids = {e.char_id for e in linked}
    assert "volker" in cids
    assert "cid" in cids
    assert "cornelia" not in cids


# ---- Eye / tooth biology ----

def test_galka_eye_has_thicker_cornea():
    lib = CharacterModelLibrary.with_bastok_demo()
    iron_eater = lib.lookup("iron_eater")
    assert iron_eater.eye_setup.cornea_ior > 1.376


def test_galka_teeth_have_crowding():
    lib = CharacterModelLibrary.with_bastok_demo()
    iron_eater = lib.lookup("iron_eater")
    assert iron_eater.tooth_setup.crowding_factor > 0.0


def test_human_default_cornea_ior():
    lib = CharacterModelLibrary.with_bastok_demo()
    cid = lib.lookup("cid")
    assert abs(cid.eye_setup.cornea_ior - 1.376) < 1e-6


def test_volker_has_scar_decals():
    lib = CharacterModelLibrary.with_bastok_demo()
    assert len(lib.lookup("volker").scar_decals) >= 1


def test_eye_default_sclera_blood_in_range():
    e = EyeSetup()
    assert 0.0 <= e.sclera_blood_amount <= 1.0
