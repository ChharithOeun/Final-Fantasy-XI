# FFXI Hardcore

> An AI-engineered HD/4K remake of Final Fantasy XI, built on top of LandSandBoat (LSB) and Unreal Engine 5.

This is the experimental/research arm of the existing private LSB stack. The goal: take the 2002 FFXI client+server architecture, lift the world geometry into modern engines, regenerate animation / textures / music with AI pipelines, and deliver a faithful but visually-modern client that talks to the same LSB server.

This project lives inside the `Final-Fantasy-XI` umbrella monorepo at `ChharithOeun/Final-Fantasy-XI/FFXI-Hardcore`.

## Status

Early ideation — repo is being scaffolded. Vision and architecture docs land in `docs/`. Code lands in `src/`. Upstream toolkits we'll engineer against are cloned into `repos/` (manifest in `MANIFEST.md`).

## Layout

```
FFXI-Hardcore/
├── README.md                  # this file
├── MANIFEST.md                # upstream repos + pinned commits
├── docs/
│   ├── VISION.md              # what we're building, why
│   ├── ARCHITECTURE.md        # the moving parts
│   └── MUSIC_PIPELINE.md      # ACE-Step driven HD music recreation
├── repos/                     # upstream tools (gitignored)
│   ├── _ue/                   # UE5 + AI tooling for Unreal
│   │   ├── unreal-engine-mcp/        (flopperam)
│   │   ├── chongdashu-unreal-mcp/    (chongdashu)
│   │   ├── kvick-UnrealMCP/          (kvick-games)
│   │   └── KawaiiPhysics/            (pafuhana1213, jiggle physics)
│   ├── _navmesh/              # zone geometry extraction
│   │   ├── Pathfinder/               (xathei)
│   │   └── FFXI-NavMesh-Builder/     (LandSandBoat)
│   ├── _animation/            # AI-driven character motion
│   │   ├── ai4animationpy/           (facebookresearch)
│   │   └── motion-diffusion-model/   (GuyTevet, MDM)
│   ├── _visual/               # textures + 4K upscaling
│   │   ├── Real-ESRGAN/              (xinntao)
│   │   └── ComfyUI/                  (comfyanonymous)
│   └── _music/                # HD music recreation
│       └── ACE-Step-1.5/             (ace-step)
├── src/                       # our remake code
├── assets/                    # 3D meshes, textures, audio, model ckpts (gitignored)
└── scripts/
    ├── CLONE_REPOS.bat        # double-click to refresh upstream clones
    └── PUBLISH_TO_GITHUB.bat  # commit + push to the parent monorepo
```

## Upstream toolkits, by pipeline stage

### Zone geometry → 3D mesh

| Repo | What it does |
|------|--------------|
| [`xathei/Pathfinder`](https://github.com/xathei/Pathfinder) | Loads FFXI client DAT files and emits OBJ + navmesh per zone — pulls the world out as 3D mesh |
| [`LandSandBoat/FFXI-NavMesh-Builder`](https://github.com/LandSandBoat/FFXI-NavMesh-Builder) | Same idea but tuned for LSB collision data — direct path from `F:\ffxi\lsb-repo` to game-world geometry |

### Unreal Engine 5 — AI agent control

| Repo | What it does |
|------|--------------|
| [`flopperam/unreal-engine-mcp`](https://github.com/flopperam/unreal-engine-mcp) | The most-mature MCP server for UE5; comes with a "Flop Agent" that lives inside Unreal and plans multi-step workflows autonomously |
| [`chongdashu/unreal-mcp`](https://github.com/chongdashu/unreal-mcp) | Lighter MCP for Cursor / Windsurf / Claude Desktop driving UE5 by natural language |
| [`kvick-games/UnrealMCP`](https://github.com/kvick-games/UnrealMCP) | Plugin-style MCP exposing UE editor + runtime to external AI agents |
| [`pafuhana1213/KawaiiPhysics`](https://github.com/pafuhana1213/KawaiiPhysics) | Open-source UE 4/5 secondary-motion plugin — hair, capes, jiggle. Used in Stellar Blade / Wuthering Waves / Persona 3 Reload. Scale: industry-standard |

### Animation — AI-driven character motion

| Repo | What it does |
|------|--------------|
| [`facebookresearch/ai4animationpy`](https://github.com/facebookresearch/ai4animationpy) | Mode-adaptive neural networks for locomotion / combat / interaction motion |
| [`GuyTevet/motion-diffusion-model`](https://github.com/GuyTevet/motion-diffusion-model) | Text-to-motion diffusion (MDM) — "wave hello while looking left" → keyframes |

### Visuals — 4K textures, lighting, generative art

| Repo | What it does |
|------|--------------|
| [`xinntao/Real-ESRGAN`](https://github.com/xinntao/Real-ESRGAN) | Generative upscaling — 256×256 FFXI textures → 4K with structure preserved |
| [`comfyanonymous/ComfyUI`](https://github.com/comfyanonymous/ComfyUI) | Node-based Stable Diffusion pipeline — generate matching texture variants, modernize materials, regenerate UI art |

### Music — HD recreation of FFXI tracks

| Repo | What it does |
|------|--------------|
| [`ace-step/ACE-Step-1.5`](https://github.com/ace-step/ACE-Step-1.5) | State-of-the-art open-source music foundation model. Lyric editing, voice cloning, remixing, accompaniment generation — generates a full track in <2s on A100. Will be wrapped as a chharbot MCP tool so the agent can drive HD recreations of FFXI music end-to-end |

`scripts\CLONE_REPOS.bat` (re)clones all of the above and writes a `MANIFEST.md` with pinned commit SHAs.

## End-to-end pipeline

```
LSB collision data        ┌─────────────────────────────┐
F:\ffxi\lsb-repo\...  ──► │ FFXI-NavMesh-Builder /      │ ──► OBJ + navmesh per zone
                           │ Pathfinder                  │
                           └─────────────────────────────┘
                                          │
                                          ▼
                           ┌─────────────────────────────┐
                           │ Unreal Engine 5 project     │ ◄── unreal-engine-mcp
                           │  - PBR materials            │     chongdashu/unreal-mcp
                           │  - Lumen lighting           │     kvick UnrealMCP
                           │  - KawaiiPhysics on bones   │     (driven by chharbot)
                           └─────────────────────────────┘
                                          ▲
                ┌─────────────────────────┼──────────────────────┐
                │                         │                      │
                ▼                         ▼                      ▼
   ┌─────────────────────┐   ┌──────────────────────┐  ┌──────────────────────┐
   │ ai4animationpy +    │   │ Real-ESRGAN +        │  │ ACE-Step-1.5 +       │
   │ motion-diffusion-   │   │ ComfyUI              │  │ chharbot MCP wrapper │
   │ model               │   │  → 4K textures,      │  │  → HD recreations of │
   │  → idle / locomotion│   │    modern materials, │  │    FFXI music tracks │
   │    / combat motion  │   │    regenerated UI    │  │                      │
   └─────────────────────┘   └──────────────────────┘  └──────────────────────┘
                                          │
                                          ▼
                                FFXI HD client (talks to LSB)
```

The **MCP layer** (chharbot's `delegate_shell`, `bash`, `read_file`, `skill_dispatch`, etc. from [mcp-graphify-autotrigger](https://github.com/ChharithOeun/mcp-graphify-autotrigger)) sits across the whole pipeline so the agent can iterate on assets, scripts, and engine config without manual hand-offs.

## Disk layout on this machine

- `F:\ChharithOeun\Final-Fantasy-XI\FFXI-Hardcore\` — this project, GitHub-tracked.
- `F:\ChharithOeun\Final-Fantasy-XI\FFXI-Hardcore\repos\` — upstream clones (gitignored, ~tens of GB once everything's in).
- `F:\ChharithOeun\Final-Fantasy-XI\FFXI-Hardcore\assets\` — 3D meshes, textures, audio, ML checkpoints (gitignored).
- `F:\ffxi\lsb-repo\` — the LSB server source we already ship.
- `F:\ffxi\graphify-out\` — knowledge graph for the whole tree.

## Where to start reading

1. [`docs/VISION.md`](./docs/VISION.md) — what the remake is trying to be.
2. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — concrete moving parts, what talks to what.
3. [`docs/MUSIC_PIPELINE.md`](./docs/MUSIC_PIPELINE.md) — ACE-Step-driven HD music recreation.
4. [`MANIFEST.md`](./MANIFEST.md) — pinned upstream commits.
