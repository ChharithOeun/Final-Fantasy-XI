# LAYERED_COMPOSITION.md

How we direct a Demoncore scene like a film. Five depth layers, each owned
by a different tool/asset class, composited into one shot. This is the same
grammar Mandalorian StageCraft uses: don't build a "level," build a stage.

---

## The five layers (far → near)

```
   [1] SKY                     volumetric clouds, sun, atmosphere, weather
            ↓
   [2] FAR BACKGROUND          distant mountains, far city silhouettes (Megascans, parallax)
            ↓
   [3] MID BACKGROUND          canonical zone geometry pulled from retail (extracted FBX)
            ↓
   [4] FOREGROUND PROPS        Megascans + hand-placed: stalls, barrels, lanterns, banners
            ↓
   [5] HERO ACTORS             player + NPCs (skeletal mesh + KawaiiPhysics + AI4Animation)
```

Each layer has its own owner and ships independently. You can swap the sky
without touching props, swap the midground (re-extract a zone with a higher
LOD) without touching the actors, etc. This is what "film directing" means:
the camera composes layers; the layers don't all live in one monolithic
mesh.

---

## Layer 1 — SKY

**Goal:** every Demoncore zone has the same volumetric, time-of-day-aware
sky. Bastok at sunset is unmistakably Bastok-at-sunset.

**Tools (all UE5 built-in):**
- `SkyAtmosphere` — physical atmospheric scattering. Time of day = changing
  sun rotation. Free, real-time.
- `VolumetricCloud` — actual 3D clouds (not skybox texture). Casts shadows
  on the ground.
- `ExponentialHeightFog` — distance haze, color-tinted per zone (Bastok =
  warm orange, Sandy = cold gray-blue, Windurst = green-tinted).
- `DirectionalLight` — the sun. Tagged per-zone with its mood preset.
- `SkyLight` — captures the sky for ambient bounce.

**Per-zone presets** live in `data/zone_atmosphere.json`:

```json
{
  "bastok_markets": {
    "sun_pitch": -25, "sun_yaw": -45,
    "sun_color": [1.0, 0.78, 0.55],
    "sun_intensity": 7.5,
    "fog_color": [0.85, 0.55, 0.35],
    "fog_density": 0.04,
    "cloud_coverage": 0.4
  },
  "windurst_woods": {
    "sun_pitch": -50, "sun_yaw": 90,
    "sun_color": [1.0, 1.0, 0.95],
    "sun_intensity": 5.0,
    "fog_color": [0.7, 0.85, 0.6],
    "fog_density": 0.02,
    "cloud_coverage": 0.7
  }
}
```

The sky layer Python script reads this and applies it. One file change =
new mood.

---

## Layer 2 — FAR BACKGROUND

**Goal:** parallax depth without polygon cost. Distant cliffs, mountains,
nation skylines visible from the city outskirts.

**Tools:**
- **Quixel Megascans** (free tier integrated with UE5) — the cliff/rock
  packs. We pick 3-5 hero geometry sets per region.
- **UE5 Nanite** — handles the Megascans poly count for free, even at
  100km+ draw distance.
- **HeightFog inscatter** — color matches the sky, makes far geo recede.

**Composition rule:** far background never has detail you can read at
ground level. It's silhouette + tone. If the player can walk to it, it's
not far background — it's midground.

For Bastok: distant Gusgen-Mines mountain ridge to the north, the Zeruhn
Mines smokestacks rising through the haze to the west.

---

## Layer 3 — MID BACKGROUND

**Goal:** the actual zone you walk through. This is where the canonical
retail geometry lives.

**Tool:** the extraction pipeline in `ZONE_EXTRACTION_PIPELINE.md`:
NoesisFFXI extracts → Real-ESRGAN x4 upscales textures → UE5 import script
brings it in as a `StaticMesh` with `MaterialInstanceConstant` per slot.

**Why we don't rebuild this from scratch:** 22 years of player muscle
memory. The exact geometry is the brand. Swapping it for "modernized"
geometry is exactly the wrong move — it would make the game feel less
like FFXI, not more.

**What we CAN modernize without rebuilding:**
- 4K textures (Real-ESRGAN), same UVs
- Lumen GI replacing baked vertex lighting
- Nanite on the imported mesh (high-poly retail meshes were already
  near-Nanite-friendly poly counts; tessellation is a nice-to-have)
- Decals — drop dirt/grime/blood/rust decals to break up texture tiling

---

## Layer 4 — FOREGROUND PROPS

**Goal:** the stuff you can walk up to and touch. Stalls, barrels,
lanterns, banners, fruit baskets, smithy anvils. This is where "AAA detail"
lives.

**Tools:**
- **Quixel Megascans** — props pack: barrels, crates, cloth, ropes,
  weathered wood
- **Hand-placed Hero Props** — for the truly iconic stuff (Zaldon's fish
  counter, the Metalworks elevator console). Sculpted in Blender or UE5
  Modeling Mode, ~50k-200k tris each (Nanite handles).
- **Decals** — one decal pack covers grime/posters/cracks across every prop
  in every zone

**Composition rule:** foreground props are placed by hand, not procedurally.
This is where the game gets its "lived-in" feeling. We can drop a barrel
near every fish stall in the game in 2 hours of work.

For Bastok Markets specifically: 5 vendor stall stalls already exist as
canonical NPC anchor points; we drop a Megascans crate stack next to each,
hang a Megascans cloth banner above each, place a Megascans lantern post
between each pair.

---

## Layer 5 — HERO ACTORS

**Goal:** the player, NPCs, mobs, NMs, bosses. They're not part of the
"level" — they're cast members on the stage.

**Tools (the cloned ones doing actual work):**

### KawaiiPhysics — jiggle / secondary motion
Pure Blueprint UE5 plugin. Drag a KawaiiPhysics anim node onto the
character's anim graph, point at the breast/hair/cloth bones, set spring
/ damping / radius. Done. Every character in the game gets convincing
secondary motion automatically — breasts, ponytails, capes, chains, gear
straps, trinkets.

Cloned at: `repos/_visual/KawaiiPhysics/`
Installed to: `demoncore/Plugins/KawaiiPhysics/` via INSTALL_DEMONCORE_PLUGINS.bat

### AI4Animation — neural locomotion
Trains a motion model on mocap; runs at inference time to produce
context-aware animation (turning, stairs, slopes, tight spaces) without
hand-authored blendspaces. We export the trained model to ONNX, run via
UE5's NNE plugin, drive the character's anim graph.

Cloned at: `repos/_animation/ai4animationpy/`
Status: training pipeline installed; models trained on FFXI-shaped rigs
land in `demoncore/Content/Animation/AI4_Models/` as ONNX. UE5 NNE node
runs them per-frame.

### MetaHuman — hero character pipeline
Player character, key NPCs (Cid, Volker, Cornelia), and named mobs
(Maat, Shadow Lord) get the MetaHuman treatment. ~1 hour per character
in MetaHuman Creator → import as Skeletal Mesh → re-target FFXI
animations. The crowd NPCs use FFXI's original character models with
modern shaders + KawaiiPhysics.

### LiveLink + VirtualCamera — virtual production
Phone-as-camera workflow per `docs/CINEMATICS_VIRTUAL_PROD.md`. We
direct cutscenes by physically holding the phone, walking around the UE5
viewport. Mandalorian-style. Already designed; needs a 30-min wiring
session per cutscene.

### Voice — Higgs Audio v2 / F5-TTS / Bark
Per `docs/VOICE_PIPELINE.md`. Every NPC line is voiced. Subtitles
replace the chat-box dialog. The voices aren't part of the geometry
layer; they're emitted at runtime by the Hero Actors layer.

---

## Composition pipeline (per zone)

For each zone we want to ship:

1. **Sky** — pick or author the zone's atmosphere preset, drop into JSON
2. **Far background** — pick 1-3 Megascans skyline meshes, place outside
   the playable bounds
3. **Mid background** — extract canonical geometry (`EXTRACT_ZONE.bat 235`)
   → upscale (`UPSCALE_TEXTURES.bat`) → import (`bastok_import_extracted.py`)
4. **Foreground props** — hand-place a prop dressing pass; ~30 min per
   zone with the Megascans library at hand
5. **Hero actors** — spawn NPC anchors at coords from LSB SQL tables;
   each anchor instantiates a SkeletalMesh actor with KawaiiPhysics +
   AI4Animation + the NPC's voice line library

Total time per zone with the pipeline: ~2 hours of human attention,
8 hours of overnight compute (texture upscale + lighting bake).

---

## What this unlocks

- **One zone == one screenplay scene.** We can iterate on Bastok's mood
  without touching Sandy. We can re-shoot the cinematic for a quest by
  swapping the sky preset for that scene only.
- **Patch-friendly.** A texture upscale rerun replaces Layer 3 textures
  without disturbing actors or props. A KawaiiPhysics tuning pass
  replaces Layer 5 character behavior without touching the world.
- **Cinematic out of the box.** The same camera moves that work in the
  Mandalorian (slow dolly-around, low-angle hero shot, smash-cut to
  reverse) work here, because the scene is already built like a stage.

This doc is the contract. Everything we build from here points at one of
these five layers. If a deliverable doesn't fit a layer, it's
infrastructure, not content.
