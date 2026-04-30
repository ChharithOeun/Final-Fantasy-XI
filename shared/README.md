# shared/

> Infrastructure both FFXI-Server and FFXI-Hardcore use. One implementation, two consumers.

This directory is the agreement between the two projects. Anything that needs to be the same on both sides — chharbot, Discord auth, code-graph indexing — lives here.

## What's shared

### chharbot (the agent)

chharbot is a Python MCP server that does ops for both projects. Its source lives upstream at [`mcp-graphify-autotrigger`](https://github.com/ChharithOeun/mcp-graphify-autotrigger); this directory pulls it in via documentation and configuration. Both `FFXI-Server/` and `FFXI-Hardcore/` invoke chharbot tools through the same MCP interface.

Tools chharbot exposes (the ones both projects use):

- `delegate_shell(argv)` — full-autonomy shell on the user's box, audit-logged
- `bash(command)` — string-cmd shell
- `read_file`, `write_file`, `edit_file` — file ops with size caps + audit log
- `glob_files`, `grep_files` — search, ripgrep-backed
- `graphify_query`, `graphify_build`, `graphify_preflight` — code-graph lookups across the whole monorepo
- `skill_dispatch(name)` — load any Claude Code skill from `~/.claude/skills/`
- `cleanup_session` — close stale windows, clear screenshots, recycle artifacts
- `tools_status` — health check

Project-specific chharbot tools (e.g., voice synthesis, NPC tick, fomor spawn) live with their project — not here.

### Discord OAuth + moderation

The Discord OAuth flow described in `FFXI-Hardcore/docs/AUTH_DISCORD.md` is implemented once and used by both projects:

- **FFXI-Hardcore**: Discord OAuth replaces PlayOnline as the login. A verified Discord identity → an LSB account token → the UE5 client authenticates with that token.
- **FFXI-Server**: the live server still uses the Ashita launcher with traditional creds, but Discord auth gates membership in the community Discord that the launcher links to. Bans propagate.

Both projects defer moderation decisions to chharbot. See `docs/DISCORD_MODERATION.md`.

### graphify (code knowledge graph)

[`safishamsi/graphify`](https://github.com/safishamsi/graphify) indexes the entire `F:\ffxi\` tree into `F:\ffxi\graphify-out\graph.json`. Both projects query it through chharbot's `graphify_query` tool. The graph is rebuilt on a schedule (chharbot's `graphify watch` daemon).

This means a refactor in `shared/` is visible to both projects when they ask code-structural questions. If we rename a chharbot tool, the graph reflects it the next tick.

### Common documentation

| Doc | What it covers |
|-----|----------------|
| `docs/CHHARBOT_TOOLS.md` | The MCP tool reference both projects share |
| `docs/DISCORD_MODERATION.md` | chharbot's moderation policies, /override flow, audit log format |
| `docs/GRAPHIFY_USAGE.md` | How to drive graphify from inside either project |
| `docs/PROTOCOL_NOTES.md` | Any non-stock LSB protocol modifications (single source of truth, both projects respect) |

## What's NOT shared

- Game logic (lives in FFXI-Server)
- Client rendering (lives in FFXI-Hardcore)
- Asset extraction pipelines (FFXI-Hardcore-specific)
- Voice synthesis (FFXI-Hardcore-specific)
- Live-server ops scripts (FFXI-Server-specific)

## Build / runtime model

`shared/` is **documentation-first**. The actual runtime artifacts live elsewhere:

- chharbot binary: `F:\ChharithOeun\mcp-graphify-autotrigger\` (cloned upstream, installed via pip)
- Discord OAuth implementation: lives next to chharbot's MCP server module
- graphify CLI: globally installed via pip (`graphifyy` package)
- graph database: `F:\ffxi\graphify-out\graph.json`

`shared/` here in the monorepo is the *contract* — what both projects can rely on existing and behaving consistently. Changes to the contract are documented here; changes to the implementation happen upstream.

## When to add something to `shared/`

A piece of infrastructure belongs in `shared/` when **both projects depend on it being the same**. If only one project uses it, it lives with that project.

Examples:

- "Both projects need chharbot to read Discord roles the same way" → `shared/`
- "Hardcore needs voice synthesis" → `FFXI-Hardcore/`, not shared
- "We're standardizing JSON log format across the whole stack" → `shared/`
- "We want a CLI to backup the live server's MariaDB" → `FFXI-Server/`, not shared
