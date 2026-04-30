"""Bastok Markets — five-layer film-style scene composition.

Builds the scene as five depth layers per docs/LAYERED_COMPOSITION.md:

    [1] SKY                  volumetric clouds + sun + atmosphere + fog
    [2] FAR BACKGROUND       distant ridges (placeholder cubes for now;
                             swap for Megascans cliffs later)
    [3] MID BACKGROUND       canonical zone geometry (uses extracted FBX
                             if present, falls back to procedural blockout)
    [4] FOREGROUND PROPS     stalls, barrels, lanterns, banners (placeholder
                             cubes/cylinders for now; swap for Megascans
                             props later)
    [5] HERO ACTORS          NPC anchor markers (placeholder cylinders;
                             SkeletalMesh + KawaiiPhysics later)

Each layer organizes its actors into a folder in the World Outliner so you
can show/hide entire layers like film comp passes.

Run from UE5:  Tools - Execute Python Script... - select this file.

Re-running is safe: every layer wipes its own actors first by tag.

Designed to evolve. Each layer function is replaceable:
- Layer 1 reads atmosphere preset from inline dict (move to JSON later)
- Layer 3 auto-detects extracted FBX; falls through to procedural otherwise
- Layer 5 reads NPC coords from inline list (move to LSB SQL pull later)
"""
import os
import unreal

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

ZONE_NAME = "bastok_markets"
EXTRACTED_FBX = (
    rf"F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\{ZONE_NAME}"
    rf"\{ZONE_NAME}.fbx"
)

# Bastok atmosphere preset — warm orange industrial sunset
ATMOSPHERE = {
    "sun_pitch": -25.0,
    "sun_yaw": -45.0,
    "sun_color": (1.0, 0.78, 0.55),
    "sun_intensity": 7.5,
    "fog_color": (0.85, 0.55, 0.35),
    "fog_density": 0.04,
    "fog_height_falloff": 0.2,
    "cloud_coverage": 0.4,
}

# NPC anchor coords (world cm). Sourced from FFXI memory + LSB stalls.
# These are roughly placed inside the procedural-blockout layout; once
# canonical extraction is in place, swap for the LSB npc_list table dump.
NPC_ANCHORS = [
    ("Zaldon",          -2500, -2500,  120, "Fish vendor"),
    ("FishingTackle",   -1250, -2500,  120, "Tackle vendor"),
    ("GeneralGoods",        0, -2500,  120, "General goods"),
    ("VegetableVendor",  1250, -2500,  120, "Vegetables"),
    ("BeverageVendor",   2500, -2500,  120, "Beverages"),
    ("WeaponShop",      -2800, -1500,  120, "Weapons merchant"),
    ("ArmorShop",       -2800,     0,  120, "Armor merchant"),
    ("Smithy",          -2800,  1500,  120, "Smithy"),
    ("Cid",              3000,  2200,  150, "Cid (Metalworks entry)"),
    ("Volker",              0,     0,  100, "Volker (plaza center)"),
]

# -----------------------------------------------------------------------------
# UE5 helpers
# -----------------------------------------------------------------------------

eas = unreal.EditorActorSubsystem()
asset_lib = unreal.EditorAssetLibrary

CUBE = asset_lib.load_asset("/Engine/BasicShapes/Cube.Cube")
CYL = asset_lib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
SPHERE = asset_lib.load_asset("/Engine/BasicShapes/Sphere.Sphere")


def wipe_by_tag(tag):
    """Destroy every actor in the level that carries the given tag."""
    n = 0
    for a in eas.get_all_level_actors():
        if tag in [str(t) for t in a.tags]:
            eas.destroy_actor(a)
            n += 1
    if n:
        print(f"     - wiped {n} actors with tag '{tag}'")


def spawn_static_mesh(mesh, location, rotation=(0, 0, 0), scale=(1, 1, 1),
                      label="actor", folder=None, tags=None):
    """Spawn a StaticMeshActor with all the labeling/folder/tag plumbing."""
    actor = eas.spawn_actor_from_object(
        mesh,
        unreal.Vector(*location),
        unreal.Rotator(*rotation),
    )
    if not actor:
        return None
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_actor_label(label)
    if folder:
        actor.set_folder_path(folder)
    if tags:
        actor.tags = tags
    return actor


def spawn_class(cls, location=(0, 0, 0), rotation=(0, 0, 0),
                label=None, folder=None, tags=None):
    actor = eas.spawn_actor_from_class(
        cls, unreal.Vector(*location), unreal.Rotator(*rotation)
    )
    if not actor:
        return None
    if label:
        actor.set_actor_label(label)
    if folder:
        actor.set_folder_path(folder)
    if tags:
        actor.tags = tags
    return actor


# -----------------------------------------------------------------------------
# LAYER 1 — SKY
# -----------------------------------------------------------------------------

def build_layer_1_sky():
    print("[Layer 1/5] Sky — volumetric clouds + sun + atmosphere + fog")
    folder = "Demoncore/Layer_1_Sky"
    tag = "Demoncore_Sky"
    wipe_by_tag(tag)

    actors = eas.get_all_level_actors()

    # Sun — find existing or spawn
    sun = next((a for a in actors if isinstance(a, unreal.DirectionalLight)), None)
    if sun is None:
        sun = spawn_class(
            unreal.DirectionalLight,
            location=(0, 0, 1500),
            rotation=(ATMOSPHERE["sun_pitch"], ATMOSPHERE["sun_yaw"], 0),
            label="Sun_Bastok",
            folder=folder,
            tags=[tag],
        )
    else:
        sun.set_actor_rotation(
            unreal.Rotator(ATMOSPHERE["sun_pitch"], ATMOSPHERE["sun_yaw"], 0),
            False,
        )
        sun.set_actor_label("Sun_Bastok")
        sun.set_folder_path(folder)
        sun.tags = [tag]

    try:
        c = sun.get_component_by_class(unreal.DirectionalLightComponent)
        if c:
            r, g, b = ATMOSPHERE["sun_color"]
            c.set_light_color(unreal.LinearColor(r, g, b, 1.0))
            c.set_intensity(ATMOSPHERE["sun_intensity"])
            c.set_editor_property("atmosphere_sun_light", True)
    except Exception as e:
        print(f"     (warn) couldn't tint sun: {e}")

    # SkyAtmosphere
    if not any(isinstance(a, unreal.SkyAtmosphere) for a in actors):
        spawn_class(unreal.SkyAtmosphere, label="SkyAtmosphere",
                    folder=folder, tags=[tag])

    # SkyLight
    if not any(isinstance(a, unreal.SkyLight) for a in actors):
        spawn_class(unreal.SkyLight, location=(0, 0, 200),
                    label="SkyLight_Ambient", folder=folder, tags=[tag])

    # VolumetricCloud (built-in actor, requires VolumetricCloud component)
    has_clouds = any(
        type(a).__name__ == "VolumetricCloud" for a in actors
    )
    if not has_clouds:
        try:
            cls = unreal.load_class(None, "/Script/Engine.VolumetricCloud")
            if cls:
                spawn_class(cls, label="VolumetricClouds",
                            folder=folder, tags=[tag])
        except Exception as e:
            print(f"     (warn) couldn't spawn VolumetricCloud: {e}")

    # ExponentialHeightFog
    fog = next((a for a in actors if isinstance(a, unreal.ExponentialHeightFog)), None)
    if fog is None:
        fog = spawn_class(unreal.ExponentialHeightFog, label="Fog_BastokIndustrial",
                          folder=folder, tags=[tag])
    else:
        fog.set_actor_label("Fog_BastokIndustrial")
        fog.set_folder_path(folder)
        fog.tags = [tag]

    try:
        fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        if fc:
            fc.set_editor_property("fog_density", ATMOSPHERE["fog_density"])
            fc.set_editor_property("fog_height_falloff", ATMOSPHERE["fog_height_falloff"])
            r, g, b = ATMOSPHERE["fog_color"]
            fc.set_editor_property(
                "fog_inscattering_color", unreal.LinearColor(r, g, b, 1.0)
            )
            fc.set_editor_property("volumetric_fog", True)
    except Exception as e:
        print(f"     (warn) couldn't configure fog: {e}")

    print("     OK — sky is dressed")


# -----------------------------------------------------------------------------
# LAYER 2 — FAR BACKGROUND
# -----------------------------------------------------------------------------

def build_layer_2_far_bg():
    print("[Layer 2/5] Far Background — distant ridges (placeholder)")
    folder = "Demoncore/Layer_2_FarBackground"
    tag = "Demoncore_FarBG"
    wipe_by_tag(tag)

    # Distant mountain silhouettes — large dark cubes well outside the
    # playable bounds. Far enough that fog buries detail.
    ridges = [
        # (x,         y,         z,    sx,  sy,  sz, label)
        (-30000,      0,    2000,  10,  60,  40, "Ridge_GusgenWest"),
        ( 30000,      0,    2000,  10,  60,  35, "Ridge_East"),
        (     0,  30000,    2000,  60,  10,  45, "Ridge_North"),
        (     0, -30000,    2200,  60,  10,  55, "Ridge_KonschtatSouth"),
        (-25000,  25000,    2500,  20,  20,  60, "Ridge_NW_Mountain"),
        ( 25000, -25000,    2400,  20,  20,  55, "Ridge_SE_Mountain"),
    ]
    for x, y, z, sx, sy, sz, name in ridges:
        spawn_static_mesh(
            CUBE, (x, y, z), scale=(sx, sy, sz),
            label=name, folder=folder, tags=[tag],
        )

    # Distant Zeruhn smokestack silhouette
    spawn_static_mesh(
        CYL, (15000, 18000, 4000), scale=(8, 8, 80),
        label="Smokestack_ZeruhnDistant", folder=folder, tags=[tag],
    )

    print(f"     OK — {len(ridges) + 1} far-background hero shapes placed")


# -----------------------------------------------------------------------------
# LAYER 3 — MID BACKGROUND (canonical zone geometry OR procedural blockout)
# -----------------------------------------------------------------------------

def build_layer_3_mid_bg():
    print("[Layer 3/5] Mid Background — zone geometry")
    folder = "Demoncore/Layer_3_MidBackground"
    tag = "Demoncore_MidBG"
    wipe_by_tag(tag)
    # Also wipe old blockout & extracted tags from the legacy scripts so
    # this single script becomes the canonical scene assembler.
    wipe_by_tag("BastokProto")
    wipe_by_tag("BastokExtracted")

    if os.path.isfile(EXTRACTED_FBX):
        print(f"     [canonical] importing extracted FBX: {EXTRACTED_FBX}")
        return _layer3_from_extracted(folder, tag)

    print("     [procedural] no extracted FBX yet — building blockout")
    return _layer3_procedural(folder, tag)


def _layer3_from_extracted(folder, tag):
    """Use the FBX produced by EXTRACT_BASTOK_FROM_RETAIL.bat."""
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    dest_pkg = "/Game/Zones/BastokMarkets/Mesh"
    if not asset_lib.does_directory_exist(dest_pkg):
        asset_lib.make_directory(dest_pkg)

    factory = unreal.FbxFactory()
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_textures = False
    options.import_materials = True
    options.import_as_skeletal = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = True
    factory.set_editor_property("import_ui", options)

    task = unreal.AssetImportTask()
    task.filename = EXTRACTED_FBX
    task.destination_path = dest_pkg
    task.destination_name = ZONE_NAME
    task.replace_existing = True
    task.automated = True
    task.save = True
    task.factory = factory
    asset_tools.import_asset_tasks([task])

    if not task.imported_object_paths:
        print("     (warn) FBX import returned no assets — falling back to procedural")
        return _layer3_procedural(folder, tag)

    mesh = asset_lib.load_asset(task.imported_object_paths[0])
    actor = eas.spawn_actor_from_object(
        mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)
    )
    if actor:
        actor.set_actor_label(f"Zone_{ZONE_NAME}")
        actor.set_folder_path(folder)
        actor.tags = [tag]
    print(f"     OK — canonical zone in level at /Game/Zones/BastokMarkets/")


def _layer3_procedural(folder, tag):
    """Stand-in blockout while extraction isn't done yet."""
    # Floor slab
    spawn_static_mesh(CUBE, (0, 0, -25), scale=(100, 100, 0.5),
                      label="Floor_BastokPlaza", folder=folder, tags=[tag])

    # Perimeter walls (80m × 80m playable area, 5m tall)
    walls = [
        (   0, -4000, 250, 80,  1, 5, "Wall_South"),
        (   0,  4000, 250, 80,  1, 5, "Wall_North"),
        (-4000,    0, 250,  1, 80, 5, "Wall_West"),
        ( 4000,    0, 250,  1, 80, 5, "Wall_East"),
    ]
    for x, y, z, sx, sy, sz, name in walls:
        spawn_static_mesh(CUBE, (x, y, z), scale=(sx, sy, sz),
                          label=name, folder=folder, tags=[tag])

    # Central elevator pillar
    spawn_static_mesh(CYL, (0, 0, 600), scale=(8, 8, 12),
                      label="Pillar_MetalworksElevator", folder=folder, tags=[tag])

    # Raised walkway + supports
    spawn_static_mesh(CUBE, (0, 1500, 200), scale=(60, 8, 0.4),
                      label="Walkway_North", folder=folder, tags=[tag])
    for x_off in (-2500, -1000, 1000, 2500):
        spawn_static_mesh(CUBE, (x_off, 1500, 100), scale=(0.6, 0.6, 2),
                          label="WalkwaySupport", folder=folder, tags=[tag])

    # West shop fronts
    for y_off, name in [(-1500, "Shop_Weapons"), (0, "Shop_Armor"), (1500, "Shop_Smithy")]:
        spawn_static_mesh(CUBE, (-2800, y_off, 250), scale=(8, 12, 5),
                          label=name, folder=folder, tags=[tag])

    # Smokestack + forge silhouette
    spawn_static_mesh(CYL, (3000, 3000, 1200), scale=(3, 3, 24),
                      label="Smokestack_ForgeStack", folder=folder, tags=[tag])
    spawn_static_mesh(CUBE, (3000, 2200, 200), scale=(10, 10, 4),
                      label="Forge_NE", folder=folder, tags=[tag])

    print("     OK — procedural blockout built (replace via EXTRACT + import)")


# -----------------------------------------------------------------------------
# LAYER 4 — FOREGROUND PROPS
# -----------------------------------------------------------------------------

def build_layer_4_props():
    print("[Layer 4/5] Foreground Props — stalls, barrels, lanterns, banners")
    folder = "Demoncore/Layer_4_Props"
    tag = "Demoncore_Prop"
    wipe_by_tag(tag)

    n = 0

    # 5 vendor stalls along the south edge — counter + posts + awning
    for i, x_off in enumerate((-2500, -1250, 0, 1250, 2500)):
        y = -2500
        # Counter
        spawn_static_mesh(CUBE, (x_off, y, 60), scale=(2, 0.8, 1.2),
                          label=f"Stall{i}_Counter", folder=folder, tags=[tag])
        # Awning posts
        spawn_static_mesh(CUBE, (x_off - 90, y - 40, 150), scale=(0.1, 0.1, 3),
                          label=f"Stall{i}_Post_L", folder=folder, tags=[tag])
        spawn_static_mesh(CUBE, (x_off + 90, y - 40, 150), scale=(0.1, 0.1, 3),
                          label=f"Stall{i}_Post_R", folder=folder, tags=[tag])
        # Awning roof
        spawn_static_mesh(CUBE, (x_off, y - 40, 300), scale=(2.4, 1, 0.1),
                          label=f"Stall{i}_Awning", folder=folder, tags=[tag])
        # Barrel stack next to each stall (Megascans replacement target)
        spawn_static_mesh(CYL, (x_off + 130, y + 50, 50), scale=(0.4, 0.4, 1),
                          label=f"Stall{i}_Barrel_A", folder=folder, tags=[tag])
        spawn_static_mesh(CYL, (x_off + 130, y + 50, 150), scale=(0.4, 0.4, 1),
                          label=f"Stall{i}_Barrel_B", folder=folder, tags=[tag])
        n += 6

    # Lantern posts between stall pairs (lanterns will be Niagara point lights later)
    for x_off in (-1875, -625, 625, 1875):
        spawn_static_mesh(CYL, (x_off, -2400, 200), scale=(0.15, 0.15, 4),
                          label="LanternPost", folder=folder, tags=[tag])
        spawn_static_mesh(SPHERE, (x_off, -2400, 380), scale=(0.4, 0.4, 0.4),
                          label="Lantern_Bulb", folder=folder, tags=[tag])
        # Actual point light
        pl = spawn_class(unreal.PointLight, location=(x_off, -2400, 380),
                         label="Lantern_Light", folder=folder, tags=[tag])
        try:
            lc = pl.get_component_by_class(unreal.PointLightComponent)
            if lc:
                lc.set_light_color(unreal.LinearColor(1.0, 0.7, 0.4, 1.0))
                lc.set_intensity(2500.0)
                lc.set_attenuation_radius(800.0)
        except Exception:
            pass
        n += 3

    # Banner/cloth hangs above the central plaza (KawaiiPhysics target later)
    spawn_static_mesh(CUBE, (0, 0, 1100), scale=(20, 0.05, 4),
                      label="Banner_BastokRepublic", folder=folder, tags=[tag])
    n += 1

    print(f"     OK — {n} foreground props placed")


# -----------------------------------------------------------------------------
# LAYER 5 — HERO ACTORS (NPC anchor markers)
# -----------------------------------------------------------------------------

def build_layer_5_actors():
    print("[Layer 5/5] Hero Actors — NPC anchor markers (placeholder)")
    folder = "Demoncore/Layer_5_HeroActors"
    tag = "Demoncore_NPC_Anchor"
    wipe_by_tag(tag)

    n = 0
    for name, x, y, z, role in NPC_ANCHORS:
        # Cylinder = body, sphere = head, rough humanoid silhouette
        spawn_static_mesh(CYL, (x, y, z), scale=(0.4, 0.4, 1.8),
                          label=f"NPC_{name}_Body", folder=folder,
                          tags=[tag, f"NPC_{name}", role])
        spawn_static_mesh(SPHERE, (x, y, z + 200), scale=(0.5, 0.5, 0.5),
                          label=f"NPC_{name}_Head", folder=folder,
                          tags=[tag, f"NPC_{name}"])
        n += 2

    # Player spawn marker
    spawn_static_mesh(SPHERE, (0, -3500, 100), scale=(0.6, 0.6, 0.6),
                      label="PlayerStart_Marker", folder=folder, tags=[tag])

    # Real PlayerStart actor
    if not any(isinstance(a, unreal.PlayerStart)
               for a in eas.get_all_level_actors()):
        spawn_class(unreal.PlayerStart, location=(0, -3500, 100),
                    label="PlayerStart", folder=folder, tags=[tag])

    print(f"     OK — {len(NPC_ANCHORS)} NPC anchors + player spawn placed")
    print("     Replace with SkeletalMesh actors + KawaiiPhysics + AI4Animation")


# -----------------------------------------------------------------------------
# SYSTEM A — DAMAGE PHYSICS + HEALING STRUCTURES
# -----------------------------------------------------------------------------
# This is a CROSS-CUTTING system, not a layer. Tags actors that should be
# treated as destructible-and-self-healing. The HP / heal_rate metadata
# rides as actor tags so a Blueprint or Python sweep can wire up the real
# BPC_HealingStructure later (see DAMAGE_PHYSICS_HEALING.md for the spec).
#
# Tag format: "HS:<structure_kind>:<hp_max>:<heal_rate>:<heal_delay_s>"
# Example:    "HS:wood:100:5:8"   = wood barrel, 100 HP, 5 HP/sec, 8s delay
#
# A future BP setup script does:
#   for actor in level:
#       if any tag.startswith("HS:"):
#           parse → attach BPC_HealingStructure with those parameters

DESTRUCTIBLE_PRESETS = {
    "barrel":            ("wood",            100,    5.0, 8.0),
    "crate":             ("wood",            200,    5.0, 8.0),
    "lantern_post":      ("wood",             80,    4.0, 6.0),
    "stall_awning":      ("cloth_banner",    300,    3.0, 10.0),
    "wood_palisade":     ("wood",          2_000,    8.0, 12.0),
    "stone_wall_section":("stone_brick",  50_000,   30.0, 15.0),
    "city_gate":         ("stone_carved",200_000,   50.0, 20.0),
    "metalwork_pillar":  ("metal_industrial", 5_000, 12.0, 10.0),
}


def hs_tag(preset_name):
    """Build an 'HS:...' tag string from a preset name."""
    kind, hp, rate, delay = DESTRUCTIBLE_PRESETS[preset_name]
    return f"HS:{kind}:{int(hp)}:{rate:g}:{delay:g}"


def build_system_a_damage_healing():
    print("[System A] Damage Physics + Healing Structures")
    folder = "Demoncore/System_A_Destructibles"
    tag = "Demoncore_Destructible"
    wipe_by_tag(tag)

    n = 0

    # Mark every existing barrel / lantern post / wall in the layered
    # scene as destructible. We don't move them — we add tags so a future
    # BP setup pass can attach BPC_HealingStructure and convert to
    # GeometryCollectionActor.
    barrel_tag = hs_tag("barrel")
    lantern_tag = hs_tag("lantern_post")
    awning_tag = hs_tag("stall_awning")
    palisade_tag = hs_tag("wood_palisade")
    pillar_tag = hs_tag("metalwork_pillar")
    gate_tag = hs_tag("city_gate")

    # Walk the level and tag-up matching props
    for actor in eas.get_all_level_actors():
        label = actor.get_actor_label()
        existing = [str(t) for t in actor.tags]
        new_tags = list(existing) + [tag]
        if "Barrel" in label and barrel_tag not in existing:
            new_tags.append(barrel_tag)
            n += 1
        elif "LanternPost" in label and lantern_tag not in existing:
            new_tags.append(lantern_tag)
            n += 1
        elif "Awning" in label and awning_tag not in existing:
            new_tags.append(awning_tag)
            n += 1
        elif "Pillar_Metalworks" in label and pillar_tag not in existing:
            new_tags.append(pillar_tag)
            n += 1
        elif "Wall_" in label and gate_tag not in existing:
            new_tags.append(gate_tag)
            n += 1
        else:
            continue
        actor.tags = new_tags

    # Drop a few demo destructibles in front of the player spawn so the
    # damage system has obvious targets to test on
    demo_destructibles = [
        # (offset_x, offset_y, scale, label, preset)
        (-300, -3000, (0.6, 0.6, 1),  "DemoBarrel_A", "barrel"),
        (-150, -3000, (0.6, 0.6, 1),  "DemoBarrel_B", "barrel"),
        (   0, -3000, (0.8, 0.8, 1),  "DemoCrate",    "crate"),
        ( 200, -3000, (0.5, 0.5, 4),  "DemoLanternPost", "lantern_post"),
        ( 500, -3000, (3,   0.5, 4),  "DemoPalisade",    "wood_palisade"),
    ]
    for x, y, scale, label, preset in demo_destructibles:
        cls = CYL if preset in ("barrel", "lantern_post") else CUBE
        actor = spawn_static_mesh(
            cls, (x, y, 100), scale=scale,
            label=label, folder=folder,
            tags=[tag, "Demoncore_Destructible_Demo", hs_tag(preset)],
        )
        if actor:
            n += 1

    print(f"     OK — {n} actors marked as destructible+healing")
    print("     Each carries an 'HS:<kind>:<hp>:<heal_rate>:<delay>' tag.")
    print("     A future BP pass attaches BPC_HealingStructure using those tags.")


# -----------------------------------------------------------------------------
# SYSTEM B — AI WORLD DENSITY
# -----------------------------------------------------------------------------
# Spawn ambient agents at every AI tier. Tag format:
#   "AI:<tier>:<role>"   tier in {0_reactive, 1_scripted, 2_reflection, 3_hero, 4_rl}
# A future server-side ingestion pass reads these tags + transform and
# instantiates the corresponding agent profile.

# Ambient agent placements — tier, role, x, y, z, label, color hint
AMBIENT_AGENTS = [
    # Tier 0 — reactive wildlife
    ("0_reactive", "rat",            -3500, -3000,  20, "Rat_Alley_1",        "vermin"),
    ("0_reactive", "rat",            -3450, -3050,  20, "Rat_Alley_2",        "vermin"),
    ("0_reactive", "rat",             3500,  3500,  20, "Rat_NearForge",      "vermin"),
    ("0_reactive", "bird_pigeon",        0,     0, 800, "Pigeon_Plaza_1",     "pigeon"),
    ("0_reactive", "bird_pigeon",      300,   100, 850, "Pigeon_Plaza_2",     "pigeon"),
    ("0_reactive", "bird_pigeon",     -200,   200, 820, "Pigeon_Plaza_3",     "pigeon"),
    ("0_reactive", "stray_cat",      -2200, -2300,  40, "Cat_NearStalls",     "cat"),

    # Tier 1 — scripted+bark crowd NPCs
    ("1_scripted", "soldier_patrol",  1500,    0, 100, "Soldier_Patrol_E",   "guard"),
    ("1_scripted", "soldier_patrol", -1500,    0, 100, "Soldier_Patrol_W",   "guard"),
    ("1_scripted", "citizen_walker", -1000,  500, 100, "Citizen_Walking_1",  "civilian"),
    ("1_scripted", "citizen_walker",  1000, -500, 100, "Citizen_Walking_2",  "civilian"),
    ("1_scripted", "child_running",   -500,  800, 100, "Child_Running",      "child"),
    ("1_scripted", "delivery_boy",   -2500, -1000, 100, "DeliveryBoy_Bastok", "delivery"),

    # Tier 2 — scripted + LLM reflection
    # (these match the NPC anchors but with a richer marker)
    ("2_reflection", "vendor_zaldon", -2400, -2400, 130, "Reflective_Zaldon", "vendor"),
    ("2_reflection", "tavern_drunk",   2500,  1500, 100, "TavernDrunk_NEcorner", "drunk"),
    ("2_reflection", "street_musician", 0, -1500, 100, "Musician_PlazaCenter", "musician"),
    ("2_reflection", "beggar",        -2700, -3500, 100, "Beggar_GateSide",    "beggar"),
    ("2_reflection", "pickpocket",    -1800, -2000, 100, "Pickpocket_LurkingNear", "pickpocket"),
    ("2_reflection", "old_carpenter", -2300,  1200, 100, "Pellah_Carpenter",   "repair_npc"),

    # Tier 3 — full generative agents (hero NPCs)
    ("3_hero", "Cid",                 3000,  2200, 150, "Hero_Cid",           "hero"),
    ("3_hero", "Volker",                 0,     0, 130, "Hero_Volker",        "hero"),
    ("3_hero", "Cornelia",            -2700,  -100, 130, "Hero_Cornelia",     "hero"),

    # Tier 4 — RL-policy mob (for the gate at night when beastmen attack)
    ("4_rl", "goblin_pickpocket",      0, -4500, 100, "Goblin_RLDemo_Spawn",  "rl_mob"),
]


def build_system_b_ai_density():
    print("[System B] AI World Density — agents at every tier")
    folder = "Demoncore/System_B_AI_Density"
    tag = "Demoncore_AI"
    wipe_by_tag(tag)

    # Color hint per role for the placeholder material (not actually
    # applied since we're using BasicShapes; saved for downstream BP
    # marker pass)
    n = 0
    by_tier = {"0_reactive": 0, "1_scripted": 0, "2_reflection": 0,
               "3_hero": 0, "4_rl": 0}

    for tier, role, x, y, z, label, color_hint in AMBIENT_AGENTS:
        # All ambient agents render as small cylinders for now; future
        # pass swaps for SkeletalMesh actors with the correct character.
        # Different proportions per tier so they're identifiable in the
        # editor outliner.
        if tier == "0_reactive":
            scale = (0.2, 0.2, 0.4)   # tiny — rats, birds, cats
        elif tier == "1_scripted":
            scale = (0.4, 0.4, 1.7)   # human silhouette
        elif tier == "2_reflection":
            scale = (0.45, 0.45, 1.8) # slightly bigger — they have memory
        elif tier == "3_hero":
            scale = (0.5, 0.5, 1.9)   # the biggest — hero NPCs
        else:  # 4_rl
            scale = (0.5, 0.5, 1.6)

        actor = spawn_static_mesh(
            CYL, (x, y, z), scale=scale,
            label=label,
            folder=folder,
            tags=[tag, f"AI:{tier}:{role}", f"AIRole:{role}", f"AIColor:{color_hint}"],
        )
        if actor:
            n += 1
            by_tier[tier] += 1

    print(f"     OK — {n} ambient agents placed")
    print(f"     Tier breakdown:")
    for t, c in by_tier.items():
        print(f"       {t:14s}: {c}")
    print("     Each agent carries an 'AI:<tier>:<role>' tag.")
    print("     A future server pass instantiates the agent profile per tag.")


# -----------------------------------------------------------------------------
# SYSTEM C — VISIBLE HEALTH (no HP/MP bars; physical damage + ailment cues)
# -----------------------------------------------------------------------------
# Per VISUAL_HEALTH_SYSTEM.md: every entity tagged with VH:<archetype>
# gets a BPC_VisibleHealthState component attached by the downstream BP
# setup pass. The component renders 7 damage stages via material decals
# + idle anim blends + KawaiiPhysics damping, plus 16 status ailments
# via particle systems and skin-tone shifts.
#
# Tag format: "VH:<archetype>"
#   archetype is one of:
#     hume_m, hume_f, elvaan_m, elvaan_f, tarutaru_m, tarutaru_f,
#     mithra_f, galka_m, mob_quadav, mob_yagudo, mob_goblin, mob_orc,
#     mob_dragon, mob_slime, mob_worm, wildlife_small, wildlife_bird
# These map onto pre-authored decal sets and Niagara FX libraries.

ARCHETYPE_BY_RACE_GENDER = {
    ("hume", "m"):       "hume_m",
    ("hume", "f"):       "hume_f",
    ("elvaan", "m"):     "elvaan_m",
    ("elvaan", "f"):     "elvaan_f",
    ("tarutaru", "m"):   "tarutaru_m",
    ("tarutaru", "f"):   "tarutaru_f",
    ("mithra", "f"):     "mithra_f",
    ("galka", "m"):      "galka_m",
    ("galka", "f"):      "galka_m",  # rare — fallback
}

ROLE_TO_MOB_ARCHETYPE = {
    "rl_mob":       "mob_goblin",  # default for our placed Tier-4 mob
    "rat":          "wildlife_small",
    "stray_cat":    "wildlife_small",
    "pigeon":       "wildlife_bird",
}


def _archetype_for_npc(profile_tags: list[str]) -> str:
    """Pick the visual-health archetype based on AIRole/AIColor tags."""
    role = None
    for t in profile_tags:
        if t.startswith("AIRole:"):
            role = t.split(":", 1)[1]
            break
    if role in ROLE_TO_MOB_ARCHETYPE:
        return ROLE_TO_MOB_ARCHETYPE[role]
    # We don't have race/gender on the level placeholders today (only
    # in the agent YAMLs). Default to hume_m as a reasonable stand-in;
    # the server will push the correct archetype on agent spawn.
    return "hume_m"


def build_system_c_visible_health():
    print("[System C] Visible Health — physical damage + ailment cues")
    folder = "Demoncore/System_C_VisibleHealth"
    tag = "Demoncore_VisibleHealth"
    wipe_by_tag(tag)

    n = 0
    # Walk every actor that's part of the AI density layer (System B)
    # and tag with a VH archetype. The downstream BP setup pass will
    # attach BPC_VisibleHealthState + BPC_VisibleAilmentState.
    for actor in eas.get_all_level_actors():
        actor_tags = [str(t) for t in actor.tags]
        if "Demoncore_AI" not in actor_tags:
            continue
        if any(t.startswith("VH:") for t in actor_tags):
            continue  # already tagged
        archetype = _archetype_for_npc(actor_tags)
        actor.tags = list(actor_tags) + [tag, f"VH:{archetype}"]
        n += 1

    # Drop a few demo actors near the player spawn at different damage
    # stages so the system has visible test cases right away. These
    # render as colored cylinders for now — the BP pass swaps to
    # SkeletalMesh with the right decals + idle blends.
    demo_npcs = [
        # (offset_x, offset_y, archetype, current_stage, label)
        (-600, -3300, "hume_m",      "pristine", "VH_Demo_Pristine_Hume"),
        (-300, -3300, "hume_m",      "bloodied", "VH_Demo_Bloodied_Hume"),
        (   0, -3300, "hume_m",      "wounded",  "VH_Demo_Wounded_Hume"),
        ( 300, -3300, "hume_m",      "grievous", "VH_Demo_Grievous_Hume"),
        ( 600, -3300, "hume_m",      "broken",   "VH_Demo_Broken_Hume"),
        ( 900, -3300, "mob_goblin",  "wounded",  "VH_Demo_WoundedGoblin"),
    ]
    for x, y, archetype, stage, label in demo_npcs:
        actor = spawn_static_mesh(
            CYL, (x, y, 100), scale=(0.4, 0.4, 1.7),
            label=label, folder=folder,
            tags=[tag, f"VH:{archetype}", f"VH_Stage:{stage}",
                  "Demoncore_VisibleHealth_Demo"],
        )
        if actor:
            n += 1

    # Demo a few status ailments at current_stage = pristine (so the
    # player can compare pure ailment cues vs damage cues independently)
    ailment_demos = [
        (-600, -3700, "hume_f",    "poison",   "VH_Demo_Poisoned_Hume"),
        (-300, -3700, "hume_f",    "sleep",    "VH_Demo_Sleeping_Hume"),
        (   0, -3700, "hume_f",    "paralyze", "VH_Demo_Paralyzed_Hume"),
        ( 300, -3700, "tarutaru_m","silence",  "VH_Demo_Silenced_Taru"),
        ( 600, -3700, "elvaan_m",  "petrify",  "VH_Demo_Petrified_Elvaan"),
        ( 900, -3700, "galka_m",   "doom",     "VH_Demo_Doomed_Galka"),
    ]
    for x, y, archetype, ailment, label in ailment_demos:
        actor = spawn_static_mesh(
            CYL, (x, y, 100), scale=(0.4, 0.4, 1.7),
            label=label, folder=folder,
            tags=[tag, f"VH:{archetype}", "VH_Stage:pristine",
                  f"VH_Ailment:{ailment}",
                  "Demoncore_VisibleHealth_Demo"],
        )
        if actor:
            n += 1

    print(f"     OK — {n} actors with VH:<archetype> tags")
    print("     12 demo NPCs span all 5 damage stages + 6 ailments.")
    print("     A future BP pass attaches BPC_VisibleHealthState +")
    print("     BPC_VisibleAilmentState components based on these tags.")


# -----------------------------------------------------------------------------
# Camera framing
# -----------------------------------------------------------------------------

def frame_establishing_shot():
    print("[camera] framing 3/4 establishing shot")
    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(-7000, -7000, 4500),
            unreal.Rotator(-25, 45, 0),
        )
    except Exception as e:
        print(f"     (warn) couldn't reframe viewport: {e}")


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------

print("=" * 72)
print(f"=== Bastok Markets — Layered Scene Composition ===")
print("=" * 72)

build_layer_1_sky()
build_layer_2_far_bg()
build_layer_3_mid_bg()
build_layer_4_props()
build_layer_5_actors()

# Cross-cutting systems ride on top of the layers. Run them after the
# layers exist so System A can tag existing props with HP metadata, and
# System B can place agents within the established world bounds.
build_system_a_damage_healing()
build_system_b_ai_density()
build_system_c_visible_health()

frame_establishing_shot()

print()
print("=" * 72)
print("=== Scene complete ===")
print()
print("World Outliner is organized into folders:")
print("    Demoncore/Layer_1_Sky")
print("    Demoncore/Layer_2_FarBackground")
print("    Demoncore/Layer_3_MidBackground")
print("    Demoncore/Layer_4_Props")
print("    Demoncore/Layer_5_HeroActors")
print("    Demoncore/System_A_Destructibles   <-- cross-cutting, see DAMAGE_PHYSICS_HEALING.md")
print("    Demoncore/System_B_AI_Density      <-- cross-cutting, see AI_WORLD_DENSITY.md")
print("    Demoncore/System_C_VisibleHealth   <-- cross-cutting, see VISUAL_HEALTH_SYSTEM.md")
print()
print("Toggle layers/systems like film comp passes — click the eye icon next")
print("to a folder to hide/show all actors in that layer/system at once.")
print()
print("System A actors carry tags like 'HS:wood:100:5:8' (HP/heal/delay).")
print("System B actors carry tags like 'AI:2_reflection:vendor_zaldon'.")
print("System C actors carry tags like 'VH:hume_m', 'VH_Stage:bloodied',")
print("    'VH_Ailment:poison'. NO HP/MP bars are visible at runtime —")
print("    players read the world: posture, blood, limp, breath.")
print("All formats parse cleanly so a downstream BP/server pass can wire")
print("up BPC_HealingStructure, Generative Agent profiles, and")
print("BPC_VisibleHealthState/BPC_VisibleAilmentState components.")
print()
print("Save the level: Ctrl+S")
print("=" * 72)
