# Asset Sourcing Strategy

> "Are we using free UE assets? Sourcing? Pulling FFXI textures and 4K-ifying them?" — yes, in that order of priority.

This doc tells you where every piece of art in the FFXI Hardcore client comes from. The default is **extract-and-upscale**: most of what players see is the same FFXI they remember, just rendered at 2026-quality resolution. We only generate or buy assets for things FFXI never had or where extraction isn't viable.

## Three asset paths

| Path | What it covers | Source | Tooling |
|------|----------------|--------|---------|
| **A. Extract + upscale** (default) | Everything that already exists in FFXI | The user's licensed FFXI client DAT files on F:\ | Pathfinder / FFXI-NavMesh-Builder for geometry; custom DAT extractors for textures; Real-ESRGAN for upscaling |
| **B. Generate** | Things FFXI doesn't have at modern quality | AI generation pipelines | ComfyUI + Stable Diffusion XL for texture variants and supplements; Meshy / Tripo / Hunyuan3D (via UnrealGenAISupport) for 3D fillers |
| **C. Free marketplace** | Environmental fillers we'd want anyway | Quixel Megascans (free for UE projects), Unreal Marketplace freebies | UE5 plugin imports |

## Path A — extract and upscale (the default path)

This is most of the work. FFXI shipped 20+ years of assets. Pulling them out and rendering them at modern fidelity is the highest-leverage thing we can do.

### Geometry

- **Source**: FFXI client DAT files (zone meshes, character meshes, prop meshes).
- **Tools**: `xathei/Pathfinder` for zone collision → OBJ; `LandSandBoat/FFXI-NavMesh-Builder` for the LSB-flavored path; custom DAT readers for character/prop meshes.
- **Output**: per-zone OBJ files, character skeletons + meshes, prop meshes.
- **Destination**: `FFXI-Hardcore/assets/meshes/<zone_or_entity>/`.
- **Modernization pass**: re-mesh through Houdini/Blender for clean topology. Bake high-poly normals from a sculpted high-detail pass for hero characters.

### Textures

- **Source**: FFXI client DAT files (`*.dat` in the user's FFXI install). Native resolution typically 256×256 or 512×512.
- **Extractor**: existing community tools (Altana Viewer, etc.) export PNGs. We script the bulk extraction.
- **Upscale**: `xinntao/Real-ESRGAN` runs on a per-texture basis. Settings: 4× upscale, model `RealESRGAN_x4plus_anime_6B` for stylized FFXI look (better than the photorealistic default for hand-painted source material).
- **Material rebuild**: a 4K diffuse alone isn't enough. We synthesize matching normal/roughness/AO maps via ComfyUI with controlnet conditioning on the upscaled diffuse. Result: full PBR material set per surface.
- **Destination**: `FFXI-Hardcore/assets/textures/<zone_or_entity>/<material_name>/{diffuse, normal, roughness, ao}.png`.

### Audio (music)

- **Source**: FFXI BGM tracker files (`.it`, `.mod`) + the small library of OGG cutscene audio.
- **Extract**: standard tracker tools render to lossless WAV.
- **Recreate at HD**: ACE-Step v1.5 with our FFXI-soundtrack LoRA regenerates each track at 96 kHz with modern mastering. See `MUSIC_PIPELINE.md`.
- **Destination**: `FFXI-Hardcore/assets/source/audio/original/` (extracted) and `FFXI-Hardcore/assets/audio/hd/` (regenerated).

### Audio (voice)

- **Source**: the small library of voiced FFXI cutscenes (mostly post-CoP) for the few characters who already had voices.
- **Use as voice reference**: the extracted clips become the reference audio for Higgs Audio voice cloning. See `VOICE_PIPELINE.md`.
- **Destination**: `FFXI-Hardcore/assets/voice_banks/<character>/reference.wav`.

## Path B — generate (for what FFXI never had)

FFXI's water never looked great. Foliage was mostly billboards. Lighting was vertex-baked. We replace these with generated content that matches the original style.

- **Water shaders**: hand-authored UE5 shaders + foam/wake textures generated via ComfyUI.
- **Foliage**: tree/grass meshes generated via Hunyuan3D or sourced from Megascans (Path C); textures via ComfyUI img2img conditioned on FFXI screenshots so the look matches.
- **Particle effects**: ComfyUI + procedural Niagara systems in UE5. Match the silhouette of the original spell effects (Stone, Fire, Aero) at higher fidelity.
- **Modern PBR-friendly skies**: Quixel HDRIs + small custom adjustments.

Generation is **always** anchored on an FFXI reference. We don't invent new aesthetics. The brief is *make this look like 2026*, not *reimagine this*.

## Path C — free UE5 / Megascans (sparingly)

For environmental fillers we'd want regardless:

- **Quixel Megascans** — free for UE projects. Rocks, trees, ground textures we use as base layers underneath FFXI's hand-painted overlays. Particularly useful for outdoor zones where the original geometry is sparse.
- **UE Marketplace monthly freebies** — niche stuff: weather systems, crowd simulation, animation controllers we don't want to write from scratch.
- **MetaHuman** — for any custom-rigged human characters we need (cutscene supporting cast). Auto-rigs to UE5 skeleton.

The rule: Path C is for *substrates* (the ground under the grass, the rock under the moss). Anything visually distinctive — a Bastok rooftop, an Onzozo wall — comes from Path A.

## Legal / IP boundary

- This is a **private LSB server** project. Asset extraction from the user's licensed FFXI install for personal-server use is the same status as the LSB project itself: a fan effort that respects Square Enix's IP and explicitly does not commercialize.
- We do **not** ship asset bundles publicly. The `assets/` directory is gitignored end-to-end. Each player extracts from their own FFXI install via our scripts.
- We do **not** train AI models on FFXI assets and then redistribute the trained models. The Real-ESRGAN model we use is the public one; the LoRAs we train (e.g., the music LoRA) stay on the user's box.
- We do **not** use FFXI assets in commercial products, marketing materials, or anything that could be construed as competing with retail FFXI.

## Storage budget

Rough sizes:

- **Extracted FFXI assets** (raw): ~6 GB
- **4K-upscaled textures**: ~80 GB (the multiplier is brutal)
- **Generated PBR maps** (normal/roughness/AO per material): ~120 GB
- **Voice banks**: ~5 GB
- **HD music regen**: ~40 GB
- **UE5 project files**: ~50 GB

Total target: ~300 GB. F: drive has 402 GB free. Comfortable for v1; if we expand to all expansions we may need to migrate to a larger drive. Plan for it now.

## Build order

1. **Bulk-extract FFXI textures** — write the DAT extraction script. Run against the user's install. Land in `assets/source/textures/`.
2. **Real-ESRGAN smoke test** — upscale 10 representative textures (zone wall, character face, item icon). Look at them. Iterate model selection.
3. **PBR generation pipeline** — ComfyUI pipeline to synth normal/roughness/AO from upscaled diffuse. Test against 5 materials.
4. **One zone, end-to-end** — Bastok Markets. Geometry from Pathfinder, textures from extract+upscale, materials from gen pipeline, all assembled in UE5.
5. **Audio extract** — both BGM (for ACE-Step LoRA training) and voice (for cloning references).
6. **Bulk pipeline** — once the per-asset pipeline works, the rest is volume. Script it; it runs unattended overnight.

Each step is independent and ships value. We don't block the AI orchestration / hardcore-death / world-reactivity work on this — those tracks proceed in parallel. The asset pipeline is the long pole because of compute time, not because of unknowns.
