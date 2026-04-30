# Architecture

This is the moving-parts view of FFXI Hardcore. It complements [`VISION.md`](./VISION.md), which says *what* we're building. This doc says *how the pieces fit*.

## High-level

```
┌─────────────────────────────────────────────────────────────────┐
│                    LSB SERVER (unchanged)                       │
│  F:\ffxi\lsb-repo\  — game logic, zones, mobs, items, missions  │
│  + lsb_admin_api    — HTTP sidecar for chharbot read access     │
└─────────────────────────────────────────────────────────────────┘
                  │                 │
   collision data │                 │ network protocol
   (per zone)     │                 │ (the existing FFXI client wire)
                  ▼                 │
┌──────────────────────────┐        │
│ FFXI-NavMesh-Builder /   │        │
│ Pathfinder               │        │
│  → zone OBJ + navmesh    │        │
└──────────────────────────┘        │
                  │                 │
                  │ OBJ + nav       │
                  ▼                 │
┌──────────────────────────┐        │
│ Unreal Engine 5 project  │        │
│  - imports zones         │        │
│  - PBR materials, GI     │ ◄───── unreal-engine-mcp
│  - actors per mob/NPC    │       (LLM drives editor)
│  - locomotion graph      │
└──────────────────────────┘        │
                  ▲                 │
                  │ skeleton +      │
                  │ animation       │
┌──────────────────────────┐        │
│ ai4animationpy           │        │
│  - mode-adaptive NN      │        │
│  - locomotion / combat   │        │
│  - per-character idle    │        │
└──────────────────────────┘        │
                                    │
                  ┌─────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FFXI HARDCORE CLIENT (UE5)                      │
│  packets in/out talk to LSB exactly like the 2002 client did    │
│  rendering, animation, audio are all 2026                        │
└─────────────────────────────────────────────────────────────────┘
```

## The four upstream toolkits, in detail

### 1. `xathei/Pathfinder`
- **What**: C# app + libraries that load FFXI client DAT files (or LSB collision data) and emit OBJ + navmesh.
- **Used for**: bulk extraction of zone geometry from a running FFXI install.
- **Where it sits**: pre-engine. Output is the input to UE5.
- **Risk**: opaque DAT parsing — likely needs the original retail client files present on disk.

### 2. `LandSandBoat/FFXI-NavMesh-Builder`
- **What**: C# app that consumes LSB collision JSON / binary and produces OBJ files + Recast/Detour navmeshes.
- **Used for**: same idea as Pathfinder, but tuned to the LSB server we already host. Closer to "from our data" than "from retail data."
- **Where it sits**: same stage as Pathfinder. We'll likely use both — Pathfinder for zones LSB doesn't have collision for yet, NavMesh-Builder for everything LSB does have.
- **Hooks**: probably wraps `recastnavigation/recastnavigation` under the hood (same as Pathfinder).

### 3. `flopperam/unreal-engine-mcp`
- **What**: an MCP server exposing Unreal Engine 5 editor + runtime as tool calls (spawn actor, set transform, import asset, run blueprint, etc.).
- **Used for**: scripting the UE5 side of the pipeline. Instead of clicking through the editor to import 200 zones, an LLM does it.
- **Where it sits**: across the whole pipeline. Gets called by chharbot / Cowork-Claude / Claude Code at any step.
- **Hooks**: registered as an MCP server in our existing chharbot tool surface (the same registry that already holds `delegate_shell`, `bash`, `graphify_query`, `read_file`).

### 4. `facebookresearch/ai4animationpy`
- **What**: Python framework implementing mode-adaptive neural networks for character animation. Trained on motion-capture data; produces locomotion / combat / interaction motion that adapts to terrain and intent.
- **Used for**: replacing the static animation clips a 2002 game shipped with. Idle, walk, run, jump, swim, combat — generated procedurally per character.
- **Where it sits**: post-zone-import. Once we have UE5 actors with skeletons, we wire ai4animationpy as the motion source.
- **Risk**: models trained on Western humanoid data may not match FFXI character proportions / styles. Likely need a fine-tune pass with FFXI-style motion data.

## chharbot's role

The whole pipeline above runs through chharbot's MCP server (the one we shipped in `mcp-graphify-autotrigger v0.3.0`). Concretely:

| Action | chharbot tool used |
|---|---|
| "Show me what zones LSB has collision data for" | `graphify_query` against `F:\ffxi\lsb-repo` |
| "Run Pathfinder on every zone" | `delegate_shell` running `dotnet run --project Pathfinder` |
| "Verify the OBJ files landed" | `glob_files` + `read_file` on the output dir |
| "Import zone XYZ into UE5" | `unreal-engine-mcp` tool call (loaded as a sibling MCP) |
| "Train ai4animationpy on this skeleton" | `bash` running `python -m ai4animationpy.train` |
| "Commit and push the latest manifest" | `bash` running `git add … && git commit && git push` |

Every step is tool-driven. No "open the editor and click through these menus" loops.

## Repository topology

This repo (`F:\ffxi\hardcore`) is **the project**. The `repos/` dir holds upstream clones we didn't write — kept gitignored so we don't fork them by accident, refreshed via `scripts\CLONE_REPOS.bat`. Pinned commits live in `MANIFEST.md`.

`src/` is where our own code goes — pipeline glue, UE5 plugins, asset-conversion utilities, ML training configs. Eventually `src/` will be its own importable Python package (or two).

`assets/` is large-binary territory and is gitignored end-to-end. Source dumps from FFXI live in `assets/source/`. Generated meshes in `assets/meshes/`. Generated textures in `assets/textures/`. None of this should ever be committed; we'll publish links to download bundles separately if/when we share assets.

`docs/` carries the always-current writeups: this file, `VISION.md`, and a per-stage doc once that stage is being actively engineered.

## Next concrete steps

1. **Run `scripts\CLONE_REPOS.bat`** — get all 4 upstreams locally with pinned SHAs in MANIFEST.md.
2. **Stand up Pathfinder + FFXI-NavMesh-Builder against an LSB zone** — pick a small one (Mhaura, Selbina). Get one OBJ out.
3. **Open it in UE5** — does it import cleanly? Is the scale right? Is the navmesh aligned?
4. **Wire `unreal-engine-mcp`** — register it in our MCP catalog so chharbot can drive it.
5. **Smallest viable AI animation slice** — one humanoid, one idle loop generated by ai4animationpy, attached in UE5.

After step 5 we have proof that all four toolkits can be chained. Everything past that is scaling and quality.
