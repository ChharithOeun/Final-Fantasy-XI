# FFXI Hardcore — upstream manifest

Snapshot of the upstream repos and their HEAD commits at the time we cloned them.
Re-run `scripts\CLONE_REPOS.bat` to refresh; this manifest is regenerated on every clone.

| Repo | Upstream | HEAD branch | HEAD commit | Local size |
|------|----------|-------------|-------------|------------|
| `ai4animationpy` | https://github.com/facebookresearch/ai4animationpy | `main` | `93eb009dcb71` | ~1.4 GB |
| `unreal-engine-mcp` | https://github.com/flopperam/unreal-engine-mcp | `main` | `10776882f497` | ~37 MB |
| `Pathfinder` | https://github.com/xathei/Pathfinder | `master` | `e064edd93c34` | ~18 MB |
| `FFXI-NavMesh-Builder` | https://github.com/LandSandBoat/FFXI-NavMesh-Builder | `main` | `ec953cec4650` | ~53 MB |

## What each gives us

- **`ai4animationpy`** — Python framework for character animation / locomotion using mode-adaptive neural networks. Replaces the static FFXI animation clips with AI-generated motion that adapts to terrain and intent. The 1.4 GB footprint is mostly model checkpoints and motion-capture data.
- **`unreal-engine-mcp`** — MCP server exposing Unreal Engine 5 editor and runtime as tool calls. Lets chharbot drive UE5 scene assembly, asset import, and Blueprint wiring without manual editor work.
- **`Pathfinder`** — C# app that loads FFXI client DAT files and emits OBJ + navmesh per zone. The "pull the world out as 3D mesh" half of the *Silmaril 2 — Building NavMeshes and how it works* video.
- **`FFXI-NavMesh-Builder`** — C# app that consumes LSB collision data and produces OBJ + Recast/Detour navmeshes. Same idea as Pathfinder but tuned to the LSB server we already host.

## Pinning policy

We do NOT pin commits in submodule fashion. Each entry above records what HEAD was the day we cloned it; re-cloning will move forward. If we need to lock against a specific upstream commit (e.g. for reproducibility of a generated asset bundle), we'll capture that decision in the relevant doc under `docs/` and check out the pinned SHA explicitly. The default stance is "track upstream main."
