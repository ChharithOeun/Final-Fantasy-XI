"""Bastok Markets blockout — procedural placeholder geometry.

Generates a recognizable Bastok Markets layout from memory:
  - Stone perimeter (raised walls bounding the city block)
  - Central pillar (the elevator going up to Metalworks)
  - Vendor stalls along the south edge (fish market vibe)
  - Stalls along the west arc (weapons / armor merchants)
  - A raised walkway suggestion on the north side
  - Atmospheric haze placeholder (mb fog particle later)

This is BLOCKOUT only — every shape is a UE5 BasicShape (cube/cylinder)
with default materials. The point is silhouette + footprint, not detail.
Final geometry comes from Pathfinder/FFXI-NavMesh-Builder extraction later.

Run from UE5:
  Tools → Python → Execute Python Script... → select this file

OR paste into the Python tab of the Output Log panel.

Spawned actors are tagged 'BastokProto' so you can select all + delete cleanly:
  Outliner → search "BastokProto" → Ctrl+A → Delete

Coordinates use UE5 cm-units (1 cm = 1 unit). The whole layout is
sized to feel like Bastok Markets at human scale: ~80m × 80m playable area.
"""
import unreal

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

CUBE = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
CYLINDER = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
SPHERE = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere.Sphere")

# Default cube is 100x100x100 cm. Cylinder is r=50 cm, h=100 cm. We scale.

editor_actor = unreal.EditorActorSubsystem()


def spawn(mesh, location, rotation=(0, 0, 0), scale=(1, 1, 1), label="block"):
    """Spawn a StaticMeshActor at the given transform with a label + tag."""
    rot = unreal.Rotator(*rotation)
    loc = unreal.Vector(*location)
    sca = unreal.Vector(*scale)

    actor = editor_actor.spawn_actor_from_object(mesh, loc, rot)
    if not actor:
        return None
    actor.set_actor_scale3d(sca)
    actor.set_actor_label(label)
    actor.tags = ["BastokProto"]
    return actor


def cube(location, scale=(1, 1, 1), rotation=(0, 0, 0), label="block"):
    return spawn(CUBE, location, rotation, scale, label)


def cylinder(location, scale=(1, 1, 1), rotation=(0, 0, 0), label="pillar"):
    return spawn(CYLINDER, location, rotation, scale, label)


# -----------------------------------------------------------------------------
# Bastok Markets layout
# -----------------------------------------------------------------------------
# Coordinate system: X = east, Y = north, Z = up.
# Origin at the center of the plaza floor.
# All units in cm (UE default).

print("=== Generating Bastok Markets blockout ===")

# 1. Perimeter walls. South side (along x-axis), 80m wide, 5m tall, 1m thick.
print("[1/6] Perimeter walls...")

# South wall (the gate to Bastok Mines)
cube(location=(0, -4000, 250), scale=(80, 1, 5), label="Wall_South")

# North wall (towards South Gate to Bastok Markets→South Gustaberg)
cube(location=(0, 4000, 250), scale=(80, 1, 5), label="Wall_North")

# West wall (water side, fish market faces this)
cube(location=(-4000, 0, 250), scale=(1, 80, 5), label="Wall_West")

# East wall (path up to Metalworks side)
cube(location=(4000, 0, 250), scale=(1, 80, 5), label="Wall_East")


# 2. Central pillar — the elevator up to Metalworks
print("[2/6] Central pillar (Metalworks elevator)...")
cylinder(
    location=(0, 0, 600),
    scale=(8, 8, 12),  # 4m radius, 12m tall — dominates the plaza
    label="Pillar_MetalworksElevator",
)


# 3. Raised walkway on north side (the Bastok Markets staircase to upper level)
print("[3/6] Raised walkway (north)...")

# The walkway itself
cube(location=(0, 1500, 200), scale=(60, 8, 0.4), label="Walkway_North")

# Support pillars under it
for x_off in (-2500, -1000, 1000, 2500):
    cube(location=(x_off, 1500, 100), scale=(0.6, 0.6, 2), label="WalkwaySupport")


# 4. Vendor stalls along the south edge — 5 stalls
print("[4/6] South vendor stalls (fish market + general goods)...")

stall_y = -2500  # just inside the south wall
for i, (x_offset, name) in enumerate([
    (-2500, "Stall_Fish_Zaldon"),
    (-1250, "Stall_FishingTackle"),
    (   0, "Stall_GeneralGoods"),
    ( 1250, "Stall_Vegetables"),
    ( 2500, "Stall_Beverages"),
]):
    # Counter
    cube(location=(x_offset, stall_y, 60), scale=(2, 0.8, 1.2), label=f"{name}_counter")
    # Awning support posts
    cube(location=(x_offset - 90, stall_y - 40, 150), scale=(0.1, 0.1, 3), label="StallPost")
    cube(location=(x_offset + 90, stall_y - 40, 150), scale=(0.1, 0.1, 3), label="StallPost")
    # Awning roof
    cube(location=(x_offset, stall_y - 40, 300), scale=(2.4, 1, 0.1), label="StallAwning")


# 5. Western arc — weapons + armor merchants (3 larger shop fronts)
print("[5/6] Western shops (weapons + armor)...")
shop_x = -2800
for j, (y_offset, name) in enumerate([
    (-1500, "Shop_Weapons"),
    (    0, "Shop_Armor"),
    ( 1500, "Shop_Smithy"),
]):
    # Shop building (stone block)
    cube(location=(shop_x, y_offset, 250), scale=(8, 12, 5), label=name)
    # Doorway suggestion (a darker recessed cube — we just place a smaller one in front)
    cube(location=(shop_x + 410, y_offset, 100), scale=(0.4, 2, 2), label=f"{name}_door")


# 6. Industrial atmosphere — smokestack and forge silhouette in the northeast corner
print("[6/6] Smokestack + forge (industrial corner)...")
# Smokestack
cylinder(
    location=(3000, 3000, 1200),
    scale=(3, 3, 24),
    label="Smokestack",
)
# Forge building
cube(
    location=(3000, 2200, 200),
    scale=(10, 10, 4),
    label="Forge_NE",
)


# -----------------------------------------------------------------------------
# 7. Ground floor — make sure actors don't float in a void
# -----------------------------------------------------------------------------
# A 100m × 100m floor at z=-50 (so the cubes sit "on" the ground at z=0).
# Default cube is 100cm; scaling to 100×100×0.5 = 100m × 100m × 50cm slab.
print("[7/9] Ground floor slab...")
cube(location=(0, 0, -25), scale=(100, 100, 0.5), label="Floor_BastokPlaza")


# -----------------------------------------------------------------------------
# 8. Cinematic lighting — warm Bastok sunset, fog, sky
# -----------------------------------------------------------------------------
# We don't replace existing lights wholesale; we tag what we spawn so it can be
# selected/removed cleanly. If a DirectionalLight already exists in the level
# (Basic / Third Person template both ship with one), we rotate it to a warm
# sunset angle and tint it slightly orange. Otherwise we spawn one.
print("[8/9] Cinematic lighting (warm Bastok sunset)...")

eas = unreal.EditorActorSubsystem()
all_actors = eas.get_all_level_actors()

dirlight = next((a for a in all_actors if isinstance(a, unreal.DirectionalLight)), None)
if dirlight is None:
    dirlight = eas.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0, 0, 1500), unreal.Rotator(-25, -45, 0)
    )
    if dirlight:
        dirlight.set_actor_label("Sun_BastokSunset")
        dirlight.tags = ["BastokProto"]
else:
    # Rotate to warm low-angle sunset: pitch -25 (low sun), yaw -45 (NE forge cast)
    dirlight.set_actor_rotation(unreal.Rotator(-25, -45, 0), False)
    dirlight.set_actor_label("Sun_BastokSunset")

# Tint the sun warm. light_component.set_light_color expects unreal.LinearColor.
try:
    light_comp = dirlight.get_component_by_class(unreal.DirectionalLightComponent)
    if light_comp:
        light_comp.set_light_color(unreal.LinearColor(1.0, 0.78, 0.55, 1.0))
        light_comp.set_intensity(7.5)
except Exception as e:
    print(f"     (warning) couldn't tint sun: {e}")

# Sky atmosphere — only spawn if missing
if not any(isinstance(a, unreal.SkyAtmosphere) for a in all_actors):
    sky = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    if sky:
        sky.set_actor_label("SkyAtmosphere_Bastok")
        sky.tags = ["BastokProto"]
        print("     + spawned SkyAtmosphere")

# SkyLight for ambient fill — only spawn if missing
if not any(isinstance(a, unreal.SkyLight) for a in all_actors):
    skylight = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 200))
    if skylight:
        skylight.set_actor_label("SkyLight_BastokAmbient")
        skylight.tags = ["BastokProto"]
        print("     + spawned SkyLight")

# Exponential height fog — industrial smokestack haze
if not any(isinstance(a, unreal.ExponentialHeightFog) for a in all_actors):
    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    if fog:
        fog.set_actor_label("Fog_IndustrialHaze")
        fog.tags = ["BastokProto"]
        try:
            fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if fog_comp:
                fog_comp.set_editor_property("fog_density", 0.04)
                fog_comp.set_editor_property("fog_height_falloff", 0.2)
                fog_comp.set_editor_property(
                    "fog_inscattering_color", unreal.LinearColor(0.85, 0.55, 0.35, 1.0)
                )
        except Exception as e:
            print(f"     (warning) couldn't configure fog: {e}")
        print("     + spawned ExponentialHeightFog (warm haze)")


# -----------------------------------------------------------------------------
# 9. Frame the camera + nudge the editor viewport so user sees the result
# -----------------------------------------------------------------------------
print("[9/9] Framing editor viewport on plaza...")
try:
    # Pull the camera back/up/over for a nice 3/4 establishing angle
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(-6500, -6500, 4500),
        unreal.Rotator(-25, 45, 0),
    )
except Exception as e:
    print(f"     (warning) couldn't reframe viewport: {e}")


# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
print()
print("=== Bastok Markets blockout complete ===")
print("Spawned ~35 actors (geometry + floor + lighting), all tagged 'BastokProto'.")
print("To remove: Outliner → search 'BastokProto' → select all → Delete.")
print()
print("What you should see:")
print("  - Walled plaza (~80m square) with a tall central elevator pillar")
print("  - 5 vendor stalls along the south side, 3 shop fronts on the west")
print("  - Raised walkway on the north")
print("  - Smokestack + forge silhouette in the NE corner")
print("  - Warm sunset sun + industrial haze fog tinted orange")
print()
print("Suggested next steps:")
print("  - Drag the Third Person mannequin near the south stalls to test human scale")
print("  - File → Save All so the level keeps the scene")
print("  - Take a screenshot (High-Resolution Screenshot in Window → menu)")
