# FFXI-Server

> The live FFXI private server we run today. LandSandBoat-based. Production-grade.

This is the running server. Players have characters here. Their data is here. We do not break this.

## What lives where

The actual server source code is at **`F:\ffxi\lsb-repo\`** on the production box — too large and too actively-mutated to live in this monorepo. What lives here in `FFXI-Server/` is everything *around* the server:

- Operational documentation (deployment, restoration, version-sync playbooks)
- Configuration playbooks
- Scripts that wrap LSB operations (deploy, restart, smoke-test)
- The bridge between LSB and the shared infrastructure (chharbot, Discord auth)

Think of `FFXI-Server/` as the ops layer. The runtime layer lives at `F:\ffxi\lsb-repo\`.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  Players (Ashita / Windower)                     │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ FFXI wire protocol
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              LSB SERVER  (F:\ffxi\lsb-repo)                      │
│   - login server, world server, map server, search server        │
│   - LandSandBoat upstream + local mods                            │
│   - lsb_version_sync keeps it in step with retail FFXI            │
└──────┬──────────────────────────────────────┬────────────────────┘
       │                                      │
       │ HTTP                                 │ ZMQ
       ▼                                      ▼
┌─────────────────────────┐    ┌──────────────────────────────────┐
│  lsb_admin_api          │    │  ai_bridge (Ashita add-on)       │
│  read-only sidecar      │    │  in-client chharbot UI surface   │
│  exposes server state   │    │  routes player /ai commands       │
└─────────────────────────┘    └──────────────────────────────────┘
       │                                      │
       └──────────────────┬───────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│   chharbot (shared/, upstream at mcp-graphify-autotrigger)       │
│   - MCP server with delegate_shell, bash, read/write/edit, ...   │
│   - reads server state, drives admin commands, moderates Discord │
└──────────────────────────────────────────────────────────────────┘
```

## Major components (already shipped)

| Component | Location | Purpose |
|-----------|----------|---------|
| LSB core | `F:\ffxi\lsb-repo\` | The actual game server |
| `lsb_admin_api` | `F:\ffxi\lsb-repo\sidecar\lsb_admin_api\` | Read-only HTTP sidecar exposing server state |
| `lsb_version_sync` | `F:\ffxi\lsb-repo\lsb_version_sync\` | Detect retail FFXI version + patch LSB to match |
| `ai_bridge` (Ashita addon) | `F:\ffxi\lsb-repo\client\ai_bridge\` | In-client chharbot UI |
| `chharbot` agent + tools | `F:\ChharithOeun\mcp-graphify-autotrigger\` (upstream) + `F:\ffxi\lsb-repo\chharbot\` (live integration) | Agent loop driving the server |
| `RUN.bat` / `deploy-full-stack.ps1` | `F:\ffxi\lsb-repo\` | One-shot deploy + smoke test |

## Operational docs (to be written here, pulling from past Lessons-Learned)

- **`docs/DEPLOYMENT.md`** — how the deploy pipeline works end-to-end (`RUN.bat`, what it does, when to use which mode).
- **`docs/ADMIN_API.md`** — every endpoint the `lsb_admin_api` sidecar exposes, with example curls.
- **`docs/AI_BRIDGE.md`** — the Ashita addon ↔ chharbot protocol (the v3 rewrite that finally landed).
- **`docs/PLAYBOOK.md`** — ops runbooks: how to restart cleanly, how to roll back a bad deploy, how to recover from FFXI-3331 version mismatches, how to verify the version-sync subsystem.

These docs cross-reference the AAR/Lessons-Learned files in `F:\ffxi\lsb-repo\AAR\reports\`. The monorepo doc is the *summary*; the detailed history stays in the AAR archive.

## Relationship to FFXI-Hardcore

FFXI-Hardcore (the HD remake project, sibling to this) targets *the same backend*. When the UE5 client connects, it speaks LSB's wire protocol (or a translation shim that bridges UE5-native networking to LSB's expected packets). All character data, inventory, mission progress, etc. lives in the same MariaDB the live server uses.

This means changes to LSB schema or wire protocol affect both projects. We coordinate via:

- A shared `shared/docs/PROTOCOL_NOTES.md` documenting any non-stock LSB modifications.
- A test environment (a second LSB instance on a non-production port) where Hardcore can break things without affecting live players.

## Relationship to `shared/`

- chharbot is shared — same agent runs ops for both projects.
- Discord auth is shared — same OAuth flow gates entry to both servers (live uses Ashita with a token-sidecar; Hardcore uses Discord-OAuth-as-login natively).
- Moderation policy is shared — chharbot's moderation rules apply across the whole community Discord, regardless of which game server a player is on.

## Where to start (for someone joining this project)

1. Read `F:\ffxi\lsb-repo\README.md` for the actual server source.
2. Read `docs/DEPLOYMENT.md` here for how we ship it.
3. Read the AAR archive at `F:\ffxi\lsb-repo\AAR\reports\` for the painful lessons we've already learned.
4. `F:\ChharithOeun\mcp-graphify-autotrigger\README.md` for chharbot's tool surface.
