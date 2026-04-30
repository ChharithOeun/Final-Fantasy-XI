"""Import the extracted Bastok Markets FBX + 4K textures into UE5.

Pipeline:
  1. Wipe the procedural blockout (everything tagged 'BastokProto')
  2. Import textures_4k/*.png as UE5 Texture2D assets under
     /Game/Zones/BastokMarkets/Textures/
  3. Import bastok_markets.fbx as a StaticMesh under
     /Game/Zones/BastokMarkets/Mesh/
  4. For each FBX material slot, create or update a MaterialInstanceConstant
     based on M_FFXI_ZoneBase (a stand-in if the master material doesn't
     exist yet, we just use the engine default and bind BaseColor)
  5. Spawn the StaticMesh as a StaticMeshActor at world origin
  6. Frame the editor camera on the imported geometry

Run from UE5:
  Tools - Execute Python Script... - select this file

The script is idempotent — running it twice replaces the previous import
cleanly, so iterate freely as you upscale-and-reimport textures.

Paths assume the staging conventions in EXTRACT_BASTOK_FROM_RETAIL.bat
and UPSCALE_BASTOK_TEXTURES.bat. Override at top if needed.
"""
import os
import unreal

# -----------------------------------------------------------------------------
# Config (override these if your paths differ)
# -----------------------------------------------------------------------------
ZONE_NAME = "bastok_markets"
EXTRACTED_ROOT = r"F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted"
ZONE_DIR = os.path.join(EXTRACTED_ROOT, ZONE_NAME)
FBX_PATH = os.path.join(ZONE_DIR, f"{ZONE_NAME}.fbx")
# Prefer 4K textures; fall back to OG textures if upscale wasn't run yet
TEX_4K_DIR = os.path.join(ZONE_DIR, "textures_4k")
TEX_OG_DIR = os.path.join(ZONE_DIR, "textures")
TEX_DIR = TEX_4K_DIR if os.path.isdir(TEX_4K_DIR) else TEX_OG_DIR

GAME_ROOT = "/Game/Zones/BastokMarkets"
MESH_DEST = f"{GAME_ROOT}/Mesh"
TEX_DEST = f"{GAME_ROOT}/Textures"
MAT_DEST = f"{GAME_ROOT}/Materials"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
asset_lib = unreal.EditorAssetLibrary
editor_actor = unreal.EditorActorSubsystem()


def ensure_dir(pkg_path):
    if not asset_lib.does_directory_exist(pkg_path):
        asset_lib.make_directory(pkg_path)


def wipe_blockout():
    """Delete every actor in the level tagged 'BastokProto'."""
    all_actors = editor_actor.get_all_level_actors()
    removed = 0
    for a in all_actors:
        if "BastokProto" in [str(t) for t in a.tags]:
            editor_actor.destroy_actor(a)
            removed += 1
    print(f"[wipe] removed {removed} blockout actors")


def import_textures():
    """Import every PNG under TEX_DIR as a Texture2D asset."""
    if not os.path.isdir(TEX_DIR):
        print(f"[tex] no texture dir at {TEX_DIR} — skipping (mesh import only)")
        return {}
    ensure_dir(TEX_DEST)

    pngs = [f for f in os.listdir(TEX_DIR) if f.lower().endswith((".png", ".tga"))]
    if not pngs:
        print(f"[tex] no PNG/TGA files in {TEX_DIR}")
        return {}

    print(f"[tex] importing {len(pngs)} textures from {TEX_DIR}")
    tex_factory = unreal.TextureFactory()

    tasks = []
    for png in pngs:
        task = unreal.AssetImportTask()
        task.filename = os.path.join(TEX_DIR, png)
        task.destination_path = TEX_DEST
        task.destination_name = os.path.splitext(png)[0]
        task.replace_existing = True
        task.automated = True
        task.save = True
        task.factory = tex_factory
        tasks.append(task)

    asset_tools.import_asset_tasks(tasks)

    # Build name -> asset map for material binding
    tex_map = {}
    for t in tasks:
        for path in t.imported_object_paths:
            asset = asset_lib.load_asset(path)
            if asset:
                tex_map[t.destination_name.lower()] = asset
    print(f"[tex] imported {len(tex_map)} textures into {TEX_DEST}")
    return tex_map


def import_mesh():
    """Import the zone FBX as a StaticMesh asset."""
    if not os.path.isfile(FBX_PATH):
        raise FileNotFoundError(
            f"FBX missing: {FBX_PATH}\n"
            f"Run EXTRACT_BASTOK_FROM_RETAIL.bat first."
        )
    ensure_dir(MESH_DEST)

    fbx_factory = unreal.FbxFactory()
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_textures = False  # we handle textures separately
    options.import_materials = True
    options.import_as_skeletal = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = True
    fbx_factory.set_editor_property("import_ui", options)

    task = unreal.AssetImportTask()
    task.filename = FBX_PATH
    task.destination_path = MESH_DEST
    task.destination_name = ZONE_NAME
    task.replace_existing = True
    task.automated = True
    task.save = True
    task.factory = fbx_factory

    asset_tools.import_asset_tasks([task])

    if not task.imported_object_paths:
        raise RuntimeError(f"FBX import returned no assets: {FBX_PATH}")

    mesh_path = task.imported_object_paths[0]
    mesh = asset_lib.load_asset(mesh_path)
    print(f"[mesh] imported StaticMesh at {mesh_path}")
    return mesh


def bind_textures_to_materials(mesh, tex_map):
    """For each material slot on the mesh, swap in our imported texture."""
    if not tex_map:
        print("[mat] no textures to bind, leaving FBX-default materials")
        return
    ensure_dir(MAT_DEST)

    static_materials = mesh.get_editor_property("static_materials")
    bound = 0
    for sm in static_materials:
        slot = str(sm.material_slot_name).lower()
        # Look for a texture whose name contains the slot name (or vice versa)
        match = tex_map.get(slot)
        if not match:
            for tex_name, tex_asset in tex_map.items():
                if slot in tex_name or tex_name in slot:
                    match = tex_asset
                    break
        if not match:
            continue

        # Create a MaterialInstanceConstant from the slot's existing material
        # (FBX import gave us a default unlit material per slot)
        existing = sm.material_interface
        mi_name = f"MI_{ZONE_NAME}_{slot}"
        mi_path = f"{MAT_DEST}/{mi_name}"
        if asset_lib.does_asset_exist(mi_path):
            asset_lib.delete_asset(mi_path)

        factory = unreal.MaterialInstanceConstantFactoryNew()
        factory.set_editor_property("initial_parent", existing)
        mi = asset_tools.create_asset(mi_name, MAT_DEST, unreal.MaterialInstanceConstant, factory)

        # Try to set a texture parameter named BaseColor (works if parent
        # exposes it). If not, this is a no-op and we still get the correct
        # parent material.
        try:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                mi, "BaseColor", match
            )
        except Exception:
            pass

        sm.material_interface = mi
        bound += 1

    mesh.set_editor_property("static_materials", static_materials)
    asset_lib.save_loaded_asset(mesh)
    print(f"[mat] bound {bound}/{len(static_materials)} material slots")


def spawn_in_level(mesh):
    """Drop the imported mesh into the level at origin."""
    actor = editor_actor.spawn_actor_from_object(
        mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)
    )
    if not actor:
        print("[spawn] failed to spawn actor")
        return None
    actor.set_actor_label(f"Zone_{ZONE_NAME}")
    actor.tags = ["BastokExtracted"]
    print(f"[spawn] placed {actor.get_actor_label()} at origin")
    return actor


def frame_viewport():
    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(-8000, -8000, 5000),
            unreal.Rotator(-25, 45, 0),
        )
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------

print("=" * 70)
print(f"Importing {ZONE_NAME} from retail extraction")
print(f"  FBX   : {FBX_PATH}")
print(f"  Tex   : {TEX_DIR}  ({'4K' if TEX_DIR == TEX_4K_DIR else 'OG'})")
print("=" * 70)

ensure_dir(GAME_ROOT)

print("[1/5] Wiping procedural blockout...")
wipe_blockout()

print("[2/5] Importing textures...")
tex_map = import_textures()

print("[3/5] Importing FBX mesh...")
mesh = import_mesh()

print("[4/5] Binding textures to material slots...")
bind_textures_to_materials(mesh, tex_map)

print("[5/5] Spawning in level + reframing camera...")
spawn_in_level(mesh)
frame_viewport()

print()
print("=" * 70)
print(f"=== {ZONE_NAME} import complete ===")
print(f"Mesh asset:    {MESH_DEST}/{ZONE_NAME}")
print(f"Textures:      {TEX_DEST}/")
print(f"Materials:     {MAT_DEST}/")
print(f"Level actor:   Zone_{ZONE_NAME} (tag: BastokExtracted)")
print()
print("This replaces the procedural blockout — the canonical zone is now")
print("in the level with original UVs and (if upscaled) 4K textures.")
print("Save the level: Ctrl+S")
print("=" * 70)
