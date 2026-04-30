# AI Orchestration Layer

The thing that makes Vana'diel feel alive. NPCs run their daily lives, monsters learn how to fight, fomors carry the memory of fallen players. All of it driven by a few orchestration pieces that talk to LSB through chharbot's MCP server.

## Three classes of AI agent

| Agent class | Driven by | Cadence | Memory |
|-------------|-----------|---------|--------|
| **Civilian NPCs** (shopkeepers, quest-givers, ambient townfolk) | LLM with daily-routine + reflection loop (Stanford "generative agents" pattern) | Tick every game-hour, replan every game-day | Long-term memory of player interactions, town events, economy state |
| **Combat agents** (regular mobs, NMs, fomors) | Multi-agent reinforcement learning trained against each other and player replays | Tick every 1-2 game-seconds in combat, idle behavior tree out of combat | Per-fight episodic memory; population-level learned policy |
| **Boss agents** | Hybrid LLM + scripted core mechanics + RL combat tactics | Tick every 1 game-second in combat | Persistent — bosses remember every fight they survived |

## Tooling stack

### Civilian NPCs — the generative-agents foundation

[`joonspk-research/generative_agents`](https://github.com/joonspk-research/generative_agents) (Stanford Smallville) is the seminal paper + reference impl. Each agent has:

- A **memory stream** (everything they've observed, time-stamped)
- A **reflection module** that periodically synthesizes memories into higher-level conclusions
- A **planning module** that turns reflections + immediate context into action plans
- A **retrieval system** (importance × recency × relevance)

We adopt that architecture wholesale. The integrations we need:

- Persist memory to a SQLite DB per NPC (not the original's in-memory store) so chharbot can restart without losing world state
- Action vocabulary maps to LSB game commands: `walk_to(x, y, z)`, `equip_shop(items)`, `say(text)`, `give_quest(player, quest_id)`, `react_to_event(event)`
- A daily replan triggered at Vana'diel midnight; lighter "what should I do next hour" replans hourly

A shopkeeper in Bastok wakes up, walks to their stall, checks last night's sales, decides whether to mark up gysahl greens because three caravans got attacked between Bastok and Sandy yesterday, opens shop, complains to their cousin about it. None of that is hand-scripted — it falls out of the loop running over a real economy state.

### Combat agents — multi-agent RL

We need agents that learn to fight by fighting. Two pieces of upstream do most of the work:

- [`Farama-Foundation/PettingZoo`](https://github.com/Farama-Foundation/PettingZoo) — the multi-agent gym standard; defines the env interface our LSB combat sim implements.
- [`openai/neural-mmo`](https://github.com/openai/neural-mmo) (Neural MMO 2.0) — a massively multi-agent MMO research environment with combat / skilling / market. Used as both training environment and a model architecture donor.

Our pipeline:

1. **Replay capture.** Every player vs. mob fight on the production LSB server is logged (positions, abilities used, damage taken, outcome). 
2. **Sim env build.** A simplified LSB combat env wired through PettingZoo. Mobs, players, abilities, MP/TP/HP — match the real game's math.
3. **RL training.** PPO or similar on Neural MMO 2.0–style architectures. Agents train against each other and against captured player replays.
4. **Distillation.** The trained policy is exported as a fast inference graph. Production fomor / NM AI calls the inference graph for action selection.

We do NOT run RL training in production. The trained policy is what the live server uses; training happens offline on the same box during low-traffic windows.

### Boss agents — hybrid

Bosses keep their scripted mechanics (the things that make the fight a fight — Promyvion's spike flails, Absolute Virtue's astral flow). But moment-to-moment tactics — who to target, when to use a 2hr, when to heal — is RL-driven.

A boss also gets an **LLM critic** that runs every ~10 game-seconds, looking at the fight state and writing high-level intent ("this party is glass — focus the WHM, ignore the tank"). The critic's intent feeds the RL policy as a goal token. This is where the "boss learns how to fight players" feeling comes from: the LLM critic remembers what worked last fight, against this LS, against this composition.

### NPC dialogue + in-engine driver

For the UE5 client side, the LLM that drives NPC speech and the API that turns LLM intent into in-game actions live in:

- [`prajwalshettydev/UnrealGenAISupport`](https://github.com/prajwalshettydev/UnrealGenAISupport) — UE5 plugin with first-class support for OpenAI / Claude / Gemini / Ollama / local models, MCP-compatible, exposes NPC dialogue + 3D gen + TTS. This is the in-engine adapter; it talks to chharbot's MCP server for actual NPC reasoning and to a TTS service for voice.
- [`Conv-AI/Convai-UnrealEngine-SDK`](https://github.com/Conv-AI/Convai-UnrealEngine-SDK) — an alternative dialogue plugin used for prototyping. Works with the Convai backend (commercial) but its action-grammar design is a useful reference for our open-source path.

The plugin handles the UE side: lip-sync, animation triggers from intent tags, camera framing. Reasoning and memory live in chharbot.

## How the layers fit

```
┌──────────────────────────────────────────────────────────┐
│              LSB SERVER (existing, modified)             │
│                                                          │
│  - normal mob/NPC tick loops                             │
│  - new event hooks: onPlayerDeath, fomorSpawnTick,       │
│    npcKilled, questDemandShift, dynamicEcoStep           │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP + ZMQ via lsb_admin_api +
                     │ ai_bridge (already shipped)
                     ▼
┌──────────────────────────────────────────────────────────┐
│        chharbot MCP server (the orchestration brain)     │
│                                                          │
│  ┌─────────────────────┐  ┌──────────────────────────┐   │
│  │ Generative-agents   │  │ RL combat policy server  │   │
│  │ engine              │  │  - PPO inference         │   │
│  │  - per-NPC memory   │  │  - matched per agent     │   │
│  │  - daily replan     │  │    class (mob/NM/fomor)  │   │
│  │  - LLM via Ollama   │  └──────────────────────────┘   │
│  └─────────────────────┘                                 │
│  ┌─────────────────────┐  ┌──────────────────────────┐   │
│  │ Boss LLM critic     │  │ Reactive-world simulator │   │
│  │  - per-fight memory │  │  - economy state tick    │   │
│  │  - intent tokens    │  │  - quest-demand engine   │   │
│  │    fed to RL policy │  │  - NPC respawn timers    │   │
│  └─────────────────────┘  └──────────────────────────┘   │
└──────────────────────┬───────────────────────────────────┘
                       │ MCP tool calls + LLM context
                       ▼
┌──────────────────────────────────────────────────────────┐
│          UE5 client (FFXI HD, AI-augmented)              │
│  - UnrealGenAISupport plugin handles NPC dialogue        │
│  - lip-sync + anim triggers from intent tags             │
│  - in-engine MCP server lets chharbot drive editor too   │
└──────────────────────────────────────────────────────────┘
```

## Hardware footprint (rough)

- **LLM inference for NPCs**: Ollama running a 7B–13B model is enough. ~6 GB VRAM. The user already has Ollama running for chharbot.
- **RL inference for combat**: tiny — a trained PPO policy is a few MB. CPU is fine.
- **RL training (offline)**: this is the heavy bit. Neural MMO 2.0 training runs comfortably on the user's box but takes hours per generation. We schedule training during nighttime / low-traffic windows.
- **Boss LLM critic**: a frontier-quality model (Sonnet/Opus tier) called every ~10 seconds during boss fights. ~1k tokens per call. Cost-controllable.

## Where chharbot fits

chharbot is the orchestrator. It already has the MCP tools to:

- Read game state via `lsb_admin_api` (existing)
- Drive shell commands via `delegate_shell`
- Read/write files via `read_file`/`write_file`/`edit_file`
- Run graphify queries to navigate the LSB codebase
- Dispatch arbitrary Claude Code skills via `skill_dispatch`

We add a few category-specific MCP tools next to those:

- `npc_step(npc_id)` — tick one civilian NPC, return its action
- `combat_action(mob_id, observation)` — RL policy inference for one combat tick
- `boss_critic(fight_state)` — LLM critic for a boss fight, returns intent tokens
- `world_tick()` — advance the reactive-world simulator one step
- `fomor_spawn(zone_id)` — request fomor spawns for a zone

Each lives in `mcp_server/` next to `agent_tools.py` and follows the same audit-log + size-cap pattern.

## Open questions

- **Sentience-of-NPCs cap.** How smart is too smart? An NPC that beats a player at riddles is fun once and infuriating twice. Calibrate.
- **Determinism for raid bosses.** Raid leaders want to learn fights. If the boss policy is non-deterministic the strategy meta becomes opaque. Compromise: bosses have a *bag* of policies, sampled at fight start, fixed for the duration. So a strategy applies to a fight but the long-term meta evolves.
- **Anti-cheat collisions.** Players will accuse the AI of cheating. Mitigation: every AI action is logged with rationale; transparency dashboard available.
- **Cost control.** LLM calls add up. Tier the system: civilian NPC LLM on a cheap local model, boss critic on a better model, reflection passes batched.

## Implementation order

1. **Civilian NPCs first** — easier to get right, lowest stakes if it goes weird. Stand up generative-agents on a single zone (Bastok Markets) with maybe 10 NPCs.
2. **Mob combat RL** — replay-capture pipeline, then offline training.
3. **Fomor AI** — composition of (1) + (2). Generative agents pattern for personality + RL policy for combat.
4. **Boss LLM critic + RL hybrid** — last because it's hardest and most visible.

Each step is independently shippable; dependent only on the LSB hooks landing.
