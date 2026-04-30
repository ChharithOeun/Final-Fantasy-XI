# ZONE_EXTRACTION_PIPELINE.md

How we pull canonical zone geometry out of the retail FFXI client and bring it
into UE5 as 4K static meshes — for every zone in the game.

This is the *real* asset path. The procedural blockout in
`ue5_scripts/bastok_markets_blockout.py` is a placeholder so you can see a
silhouette tonight; this pipeline is what we ship.

---

## Why pull, not rebuild

FFXI shipped in 2002. Every zone — meshes, collision, UVs, NPC anchor points,
spawn boxes, music triggers — is already on disk in the retail client. The
geometry is *canonical*: 22-year players remember where every alcove, stair,
and vendor stall sits. Rebuilding from scratch would be slower, less faithful,
and harder to keep in sync with LSB's NPC coordinate tables (which reference
the retail world coordinates).

The compute-cheap, faithful move is: extract the OG geometry, keep the UVs,
upscale the textures ~4-8x, and let UE5's Lumen + Nanite + post FX do the
work of making it look modern.

---

## The DAT file layout (what's actually on disk)

Retail client lives at `F:\ffxi\client\FINAL FANTASY XI\`. Inside:

```
FINAL FANTASY XI/
├── FFXiMain.dll       <- contains zone-id -> DAT-path lookup table
├── FTABLE.DAT         <- file table; maps logical IDs to ROM/x/y.DAT paths
├── ROM/
│   ├── 0/
│   │   ├── 0.DAT
│   │   ├── 1.DAT
│   │   └── ...
│   ├── 1/
│   └── ... (numbered subdirs 0-N)
├── ROM2/   <- expansion: Rise of the Zilart and later
├── ROM3/   <- Chains of Promathia
├── ROM4/   <- Treasures of Aht Urhgan
├── ROM5/   <- Wings of the Goddess
├── ROM6/   <- Abyssea / SoA additions
├── ROM7/   <- later updates
├── ROM8/   <- later updates
└── ROM9/   <- Rhapsodies / final retail updates
```

Each `.DAT` is a custom binary container holding one or more of:
- vertex / index buffers (positions, normals, UVs, vertex colors)
- collision mesh (separate from render mesh)
- texture chunks (DXT-compressed, 256x256 typical)
- NPC placement records (zone-relative xyz coords, model id, name, dialog ids)
- region triggers (zone transitions, music change zones, weather zones)
- mob spawn anchors

The format isn't documented by SE but has been fully reverse-engineered by
atom0s, Windower, and FFXI Classic communities over 15+ years. We don't
implement a parser — we use existing tools.

---

## Tool chain (what does the actual extraction)

We have several mature, free tools. We pick by capability:

### 1. NoesisFFXI (Rich Whitehouse's Noesis + FFXI plugin)
- **Best for**: render mesh + texture extraction → FBX/OBJ
- **Output**: `.fbx` with UVs, materials referencing PNG textures
- **CLI**: yes — `noesis.exe ?cmode <input.DAT> <output.fbx>`
- **Where**: standalone exe from richwhitehouse.com; FFXI plugin is `fmt_ffxi.py`
- **Notes**: ships as a single zip, no installer

### 2. atom0s/Pathfinder
- **Best for**: collision mesh + walkable surfaces (for navmesh)
- **Output**: `.obj` of collision geometry only
- **CLI**: yes
- **Where**: github.com/atom0s/Pathfinder
- **Notes**: this is the source of the navmesh data LSB uses today

### 3. Windower/FFXI-NavMesh-Builder
- **Best for**: Recast/Detour navmesh (.bin) for in-game pathing
- **Output**: `.bin` navmesh consumed by LSB server-side AI
- **Where**: github.com/Windower/FFXI-NavMesh-Builder
- **Notes**: chains downstream of Pathfinder

### 4. POLUtils (legacy)
- **Best for**: NPC dialog tables, item DB extraction, music conversion
- **Output**: text files, BGW/SCD music
- **Where**: SourceForge / various mirrors
- **Notes**: stale UI but still works; useful for non-mesh content

### Decision matrix per zone

| Need                           | Tool                       | Output              |
| ------------------------------ | -------------------------- | ------------------- |
| Render mesh + UVs + textures   | NoesisFFXI                 | `.fbx` + `.png`     |
| Collision mesh                 | Pathfinder                 | `_collision.obj`    |
| Server-side navmesh            | FFXI-NavMesh-Builder       | `.bin`              |
| NPC placements + dialog        | POLUtils or LSB SQL tables | `.csv` / SQL dump   |
| Music + ambient SFX            | POLUtils                   | `.bgw` → `.wav`     |

---

## The Bastok Markets pull (worked example)

Bastok Markets is **zone 235** (0xEB). Its DATs live across ROM/ subdirs;
NoesisFFXI's plugin reads `FTABLE.DAT` to resolve zone-id → DAT paths
automatically, so we don't manually figure out which numbered files contain
the zone.

### Step 1 — extract mesh + textures

```
EXTRACT_BASTOK_FROM_RETAIL.bat
```

Internally:
1. Locate Noesis (download to `F:\tools\noesis\` if missing — single 6 MB exe)
2. Locate the FFXI Noesis plugin (`fmt_ffxi.py`); download from a known mirror
3. Run Noesis with the FFXI client path + zone ID 235
4. Outputs land in `F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\bastok_markets\`:
   - `bastok_markets.fbx`               — render mesh
   - `bastok_markets_collision.obj`     — collision (via Pathfinder)
   - `textures/*.png`                   — every material at 256x256

### Step 2 — upscale textures 4x with Real-ESRGAN

```
UPSCALE_BASTOK_TEXTURES.bat
```

Walks `extracted/bastok_markets/textures/`, runs each PNG through
Real-ESRGAN x4 (or x8 if VRAM allows), writes `_4k/` sibling dir. Same
filename, same UV layout — UE5 just sees higher-res versions.

For DirectML on AMD GPU: Real-ESRGAN-AMDGPU fork or `realesrgan-ncnn-vulkan`
binary. Both already in the GPU compatibility doc.

### Step 3 — import to UE5

```
ue5_scripts/bastok_import_extracted.py
```

In the demoncore project:
1. `unreal.AssetTools.import_asset_tasks` on the `.fbx` → spawns a
   `StaticMesh` asset in `/Game/Zones/BastokMarkets/`
2. Imports each PNG from `_4k/` as a `Texture2D`
3. Auto-creates `Material` instances binding texture slot names from the
   FBX material slots → same materials, just 4K
4. Spawns the imported StaticMesh as a `StaticMeshActor` at world origin
5. Replaces the procedural blockout (deletes everything tagged
   `BastokProto`)

You now have **canonical Bastok Markets geometry, 4K textures, in UE5**.

---

## Repeating for other zones

The pipeline is parameterized by zone id. Adding South Gustaberg:

```
EXTRACT_ZONE.bat 105     -- South Gustaberg = 0x69 = 105
```

The .bat reads `zones.json` (a small lookup we populate from LSB's
`zone_settings` SQL table — already in `lsb-repo/sql/zone_settings.sql`):

```json
{
  "100": {"name": "south_gustaberg",  "filename_safe": "south_gustaberg"},
  "235": {"name": "bastok_markets",   "filename_safe": "bastok_markets"},
  "236": {"name": "bastok_mines",     "filename_safe": "bastok_mines"},
  "237": {"name": "metalworks",       "filename_safe": "metalworks"}
}
```

Once we have all 200+ zones extracted, upscaling is a single overnight
batch job (a few seconds per texture × ~50 textures per zone × 200 zones
≈ 10-15 hours on the user's GPU).

---

## What still needs human eyes

The pipeline is mostly automatic but a few zones need attention:

1. **Zones with vertex animation** (e.g. Tavnazian Safehold's banner cloth)
   need a manual hand-fix — Noesis exports the rest pose; the animation
   can be re-authored in UE5 with KawaiiPhysics or stripped.
2. **Water surfaces** (Selbina, Mhaura, Rabao) get extracted as flat planes;
   replace with UE5's water plugin for refraction + buoyancy.
3. **Sky domes / fog volumes** are best replaced with UE5 SkyAtmosphere +
   ExponentialHeightFog — we don't import the OG sky textures.
4. **Lighting** — OG zones bake light into vertex colors. We strip vertex
   colors on import and let Lumen handle GI.

---

## Status

- [x] Procedural blockout for tonight (`bastok_markets_blockout.py`)
- [ ] Noesis + FFXI plugin staged at `F:\tools\noesis\`
- [ ] `EXTRACT_BASTOK_FROM_RETAIL.bat` smoke test
- [ ] Real-ESRGAN texture upscale pass
- [ ] UE5 import script with material binding
- [ ] All-zones overnight batch
- [ ] Texture upscale overnight batch (200+ zones)

Bastok Markets is the canonical first zone — it touches all the moving parts
(buildings, raised walkway, smokestack, vendor stalls, central elevator)
without being so vast (Beaucedine, Boyahda) that a single-zone test
balloons. Once Bastok extracts cleanly, the loop generalizes.
