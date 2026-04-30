# Final Fantasy XI

> Umbrella monorepo for ChharithOeun's Final Fantasy XI work. Two sibling projects, one shared infrastructure layer.

This monorepo holds all FFXI-related engineering. The two projects are deliberately separate — they have different goals, different release cadences, different audiences — but they share the same toolchain, the same Discord, the same chharbot.

## The two projects

### `FFXI-Server/` — the live private server

The production-grade FFXI private server we already run. LandSandBoat-based, retail-version-synced via `lsb_version_sync`, exposed to chharbot via the `lsb_admin_api` and `ai_bridge` sidecars. Players use the existing FFXI client (Ashita / Windower) to play. This is where the actual playerbase lives day-to-day.

The runtime source for this project lives at `F:\ffxi\lsb-repo` (the LSB working tree is too large and too mutable to live in this monorepo). What's in `FFXI-Server/` here is documentation, deployment scripts, configuration playbooks, and the bridge between LSB and the shared infrastructure.

### `FFXI-Hardcore/` — the AI-engineered HD remake

The research arm. UE5 client, AI-driven NPCs, LLM-orchestrated world, permadeath-becomes-fomor mechanic, Discord-OAuth login, ACE-Step regenerated music, 4K extracted-and-upscaled visuals, voice-acted everyone. Talks to the SAME LSB server backend (after a translation shim — the wire protocol is the unknown).

This is where the "what does FFXI look like in 2026" questions get answered. None of this ships to the live server until it's been hammered in isolation.

### `shared/` — the infrastructure both projects use

- **chharbot** — the MCP server with `delegate_shell`, `bash`, `read_file`, `glob_files`, `grep_files`, `graphify_query`, `skill_dispatch`, `cleanup_session`. Lives at `F:\ChharithOeun\mcp-graphify-autotrigger` upstream; this monorepo references it.
- **graphify** — code knowledge graph, indexes the whole tree at `F:\ffxi\graphify-out\`.
- **Discord auth + moderation** — the OAuth flow that replaces PlayOnline (in FFXI-Hardcore) and gates access to the live server's Discord (in FFXI-Server). One implementation, both sides use it.
- **Common docs** — anything that applies to both projects: chharbot tool usage, Discord moderation policy, deployment playbooks.

## Why split them

A live private server and an experimental UE5 remake answer to fundamentally different release pressures:

- The live server cannot break. Players are logged in. Test changes in a dev branch, deploy via `RUN.bat`, watch for regressions.
- The HD remake is allowed to break daily. We're prototyping, scrapping, rewriting. The UE5 project file might not even open on the next pull.

Putting them in the same project would force one cadence onto the other. Splitting them — but keeping them under one umbrella with shared tooling — preserves the velocity of both.

## Layout

```
Final-Fantasy-XI/
├── README.md                    # this file
├── .gitignore                   # umbrella ignore (large binaries, repos/, assets/, secrets)
│
├── FFXI-Server/
│   ├── README.md                # what this project is
│   ├── docs/
│   │   ├── DEPLOYMENT.md        # how RUN.bat / deploy-full-stack.ps1 work
│   │   ├── ADMIN_API.md         # the lsb_admin_api sidecar surface
│   │   ├── AI_BRIDGE.md         # how Ashita talks to chharbot
│   │   └── PLAYBOOK.md          # ops runbooks (restart, restore, version-sync)
│   ├── config/                  # environment configs (encrypted secrets stay out)
│   └── scripts/                 # deployment + maintenance scripts
│
├── FFXI-Hardcore/
│   ├── README.md
│   ├── MANIFEST.md              # pinned upstream commits for repos/
│   ├── docs/
│   │   ├── VISION.md
│   │   ├── ARCHITECTURE.md
│   │   ├── ASSETS.md            # asset sourcing strategy
│   │   ├── VOICE_PIPELINE.md    # voice synthesis stack
│   │   ├── MUSIC_PIPELINE.md    # ACE-Step driven HD music
│   │   ├── AI_ORCHESTRATION.md  # LLM NPCs + RL combat + boss critic
│   │   ├── HARDCORE_DEATH.md    # 1hr permadeath → fomor mechanic
│   │   ├── REACTIVE_WORLD.md    # cause/effect quest demands, NPC permadeath
│   │   ├── AUTH_DISCORD.md      # PlayOnline killshot
│   │   └── UI_CHAT.md           # bubble-chat UX (TBD)
│   ├── src/                     # our code
│   ├── assets/                  # gitignored — extracted + generated art
│   ├── repos/                   # gitignored — upstream tools
│   └── scripts/
│
└── shared/
    ├── README.md                # what shared is, how the projects use it
    ├── chharbot/                # references the upstream chharbot install
    ├── auth-discord/            # Discord OAuth implementation
    └── docs/
        ├── CHHARBOT_TOOLS.md    # MCP tool reference for both projects
        ├── DISCORD_MODERATION.md # how chharbot moderates the Discord
        └── GRAPHIFY_USAGE.md    # how to query the code graph
```

## Toolchain shared across projects

- [`mcp-graphify-autotrigger`](https://github.com/ChharithOeun/mcp-graphify-autotrigger) — chharbot's MCP server
- [`safishamsi/graphify`](https://github.com/safishamsi/graphify) — code knowledge graph
- [`LandSandBoat/server`](https://github.com/LandSandBoat/server) — upstream FFXI private server (consumed by FFXI-Server, targeted by FFXI-Hardcore)

## Where to start

- Working on the live private server: `FFXI-Server/README.md`
- Working on the HD remake: `FFXI-Hardcore/README.md`
- Working on infrastructure both use: `shared/README.md`

The two projects don't touch each other directly. They both touch shared/.
