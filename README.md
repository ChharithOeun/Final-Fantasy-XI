# Final Fantasy XI

> Umbrella monorepo for ChharithOeun's Final Fantasy XI work — server, client, AI tooling, HD remake research.

This repo collects everything that builds or extends a private Final Fantasy XI ecosystem. Each top-level directory is a standalone project with its own README, but they share a common toolchain (chharbot's MCP server, the graphify code-knowledge graph, the LSB private server) so they live together for easier cross-project work.

## Projects

| Directory | What it is | Status |
|-----------|------------|--------|
| [`FFXI-Hardcore/`](./FFXI-Hardcore) | AI-engineered HD/4K remake on top of LSB + Unreal Engine 5 | Early ideation |

More projects will land here over time (LSB sidecars, Ashita/Windower addons, AI-driven multi-box tooling, retail patch sync utilities, etc.). For now FFXI-Hardcore is the active project.

## Why a monorepo

The pieces of an FFXI private-server ecosystem aren't actually independent: collision data the server emits is the input to the navmesh tool which is the input to the UE5 zone import which is the input to the AI animation pipeline. Keeping all of it in one repo means a single `git clone` reproduces the entire stack at a known-good state, and cross-project refactors don't fragment.

Heavy binary assets (3D meshes, textures, model checkpoints) are gitignored end-to-end. Each project carries its own `assets/` and `repos/` (upstream clones) that are regenerated locally via per-project scripts.

## Layout convention

Every project under this monorepo follows the same shape:

```
<Project>/
├── README.md            # what this project is
├── MANIFEST.md          # pinned upstream commits, if any
├── docs/                # vision, architecture, per-feature docs
├── src/                 # our code
├── assets/              # heavy binaries (gitignored)
├── repos/               # upstream clones (gitignored)
└── scripts/             # build / clone / publish .bat files
```

## Toolchain shared across projects

- **chharbot** ([github.com/ChharithOeun/mcp-graphify-autotrigger](https://github.com/ChharithOeun/mcp-graphify-autotrigger)) — MCP server with `delegate_shell`, `bash`, `read_file`, `glob_files`, `grep_files`, `graphify_query`, `skill_dispatch`, `cleanup_session`. Drives every project here.
- **graphify** ([github.com/safishamsi/graphify](https://github.com/safishamsi/graphify)) — code knowledge graph. The `F:\ffxi\graphify-out\` knowledge graph indexes every project in this monorepo.
- **LandSandBoat** ([github.com/LandSandBoat/server](https://github.com/LandSandBoat/server)) — the upstream FFXI private server. Our FFXI-Hardcore client targets it.

## Where to start

Open the project you want to work on (currently just `FFXI-Hardcore/`) and read its README. Each project is self-contained; the monorepo root just holds shared docs and the umbrella .gitignore.
