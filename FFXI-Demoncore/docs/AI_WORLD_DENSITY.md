# AI_WORLD_DENSITY.md

The world is full of brains. Not "scripted NPCs that wander a 5-meter
loop" — actual autonomous agents with memory, plans, opinions about the
player, and lives that continue when nobody's looking.

This is the doctrine: by ship date, **every entity bigger than a
particle has some degree of autonomous behavior**. The fish in the
harbor school. The rats in the alley flee at footsteps. The drunk at
the tavern starts fights when a Galkan warrior walks in. The vendor
restocks based on what sold last week. The Shadow Lord remembers which
party member tagged him last and adjusts his opening skill chain.

Density is the brand. FFXI's original world felt empty between mob
camps. Demoncore's world feels *crowded* — even in safe zones.

---

## The four AI tiers

We can't run a 70B-param LLM on every chicken. We tier by importance.

### Tier 0 — REACTIVE (millions, ~free per agent)

Pure reflex behaviors. No memory. No plan. Trigger → response.

- Fish school avoidance (Boids-style)
- Birds startle when a sword draws nearby
- Rats flee footstep sound
- Banners flap when AoE detonates within radius
- Lanterns flicker when a player hits them with a basic attack
- Wildlife hops out of the way of mounted players

**Implementation:** UE5 native Behavior Trees + simple state machines.
Runs client-side per zone. Cost ≈ 0.

### Tier 1 — SCRIPTED+BARK (thousands, ~$0 per agent)

Daily-loop NPCs with hand-authored schedules and a small bark library.
Each NPC has a list of 5-10 location/time pairs and 10-30 contextual
chat lines.

- Bastok crowd NPCs (the soldiers patrolling, citizens crossing the
  plaza, kids running past)
- Mob spawns that follow a patrol route
- Vendors who close shop at night and reopen at sunrise
- Random street performers who rotate through Bastok / Sandy / Windy

**Implementation:** Lua scripts on the LSB server (this is what FFXI's
original NPC system already does, just with more variety). Bark text
authored in spreadsheets. Cost ≈ 0.

### Tier 2 — SCRIPTED + LLM REFLECTION (hundreds, $0.0001 per agent)

Named NPCs with light personalities. Run a small local LLM (Llama 3
8B-Instruct on Ollama) once an hour to "reflect" on what happened to
them, update a one-sentence memory, and adjust their bark library.

- Vendors with personalities (snarky vegetable seller, lonely fisherman)
- Quest-giver NPCs whose attitude reflects past player interactions
- Tavern regulars who get drunker as the night progresses
- Apprentices who level up in their craft and eventually open their own
  shops

Each agent has a small profile:
```
{
  "name": "Zaldon",
  "role": "fish vendor in Bastok Markets",
  "personality": "blunt, proud of his catch, hates beastmen",
  "memory_summary": "I sold a frostfish to a Galkan warrior yesterday, he was kind",
  "current_mood": "content",
  "bark_pool": ["Fresh from the harbor!", ...],
}
```

When the player approaches, the agent picks a bark weighted by current
mood + memory. Once an hour, the local LLM rewrites `memory_summary`
based on the day's events (`an outlaw broke a barrel near my stall, my
mood is down`).

**Implementation:** Stanford Generative Agents architecture
(`repos/_agents/generative_agents/`) running against Ollama. State
serialized to MariaDB.

### Tier 3 — FULL GENERATIVE AGENT (dozens, $0.001 per turn)

Hero NPCs (Cid, Volker, Cornelia, Cardinal Mildaurion). Full memory
streams, daily reflections, planning. They have opinions, friendships,
goals, and they pursue those goals across in-game days even when no
player is watching.

- Cid is working on a new airship; goes into the workshop at 8am, has
  lunch with his daughter, talks to Volker about politics in the
  evening
- Volker checks the mines, holds court at noon, drills the Bastok
  guard at 4pm
- Periodically writes journal entries that drive procedurally-generated
  side quests

**Implementation:** Generative Agents (Stanford) with full memory
stream + reflection. Hosted on a separate Ollama instance, model size
8B-13B per agent (Mixtral or Llama 3). Snapshots every 5 game-minutes.
~50 hero agents server-wide.

### Tier 4 — COMBAT RL POLICY (per mob class, batch-trained)

Mobs and NMs use a learned combat policy, not a script. Each mob class
(Goblin Pickpocket, Quadav Roundshield, Shadow Lord) has a trained
policy that takes a state vector (player party comp, party HP, recent
spells cast, terrain) and outputs an action distribution (attack /
ability / move / use environment).

Policies are trained offline using PettingZoo + Neural MMO 2.0 (both
already cloned in `repos/_combat_rl/`). One mob class trains for a
week against synthetic players, exports an ONNX policy, and that ONNX
ships with the mob. At runtime, the policy runs in <1 ms per inference
on UE5's NNE plugin.

This makes combat feel different per mob: a Quadav remembers your
wing-aimed-attack, a Goblin Pickpocket steals when nobody's targeting
him, the Shadow Lord opens with the same WS that previously killed a
party member.

**Bonus tier — boss-level critic LLM**: NMs and final-floor bosses get
a critic LLM that watches the encounter every 30 seconds and *adjusts*
the boss's policy on the fly. The critic reads the combat log and says
"the party is over-relying on a Black Mage; have the boss switch to
silence-AOE next phase". This is what makes a Demoncore boss feel like
it's playing *with* you.

---

## Density targets (what we're shipping)

Per zone, in active play hours:

| Tier              | Bastok Markets | South Gustaberg | Castle Oztroja  |
| ----------------- | -------------- | --------------- | --------------- |
| 0 — Reactive      | ~200           | ~500 (wildlife) | ~50             |
| 1 — Scripted+Bark | ~80 NPCs       | ~30 mobs        | ~150 mobs       |
| 2 — Reflection    | ~25            | ~3              | ~5              |
| 3 — Full agent    | 4 (Cid+co)     | 0               | 1 (Maat fight)  |
| 4 — RL policy     | 0              | 30 mobs         | 150 mobs        |

The "world full of AI" target: across Vana'diel, ~50 Tier-3 agents,
~5,000 Tier-2, ~50,000 Tier-1, and uncounted Tier-0. Tier-4 is per-class
not per-instance, so 200ish unique mob classes have learned policies
shipping with the game.

---

## Compute budget (server-side)

The server-side AI runs on:
- **chharbot** orchestrator process (Python, manages agent lifecycles)
- **Ollama** instances pinned per tier (8B for Tier 2, 13B for Tier 3)
- **MariaDB** for state persistence
- **Redis** for hot-cache of recent agent decisions (so we don't re-LLM
  the same vendor's bark on every player click)

Estimated cost per concurrent player:
- Tier 0/1: ~0 (already in the LSB cost envelope)
- Tier 2: ~0.5 LLM tokens per second / 10 players → 1 8B-Q4_K_M instance
  serves ~30 active Tier-2 NPCs
- Tier 3: 1 reflection per agent per 5 game-minutes ≈ trivial. The big
  cost is initial setup, not steady-state
- Tier 4: pre-trained policies → ~zero runtime cost; one A100 hour per
  mob class for training

A single rented dedicated server (32 GB RAM, 12-core CPU, RTX 4090 for
Ollama) handles ~200 concurrent players with full AI density. Hosting
budget per month: ~$300.

---

## Player-facing AI quality bar

We pass the bar when:

1. **A player walks through Bastok Markets and notices someone** — a
   cleaning lady, a pickpocket trailing a rich-looking player, a
   street musician — that they didn't notice yesterday because that
   NPC has a daily life
2. **A vendor remembers you** — a Tier-2 vendor you bought from yesterday
   gives you a slightly different bark today ("back already?")
3. **A boss adapts** — a player who beats the Shadow Lord with a
   black-mage cheese strategy on day 1 finds the Shadow Lord casts
   silence first on day 30 (because the critic LLM noticed the meta)
4. **You can't tell which NPCs are scripted vs LLM-driven** without
   talking to them three times

This is the test. If a player can fingerprint a Tier-2 NPC as
LLM-driven on the first interaction, the personality prompt is too
literal. They should just feel like *people*.

---

## Authoring pipeline (how new NPCs get added)

A junior designer adds a new Tier-2 NPC by writing one row:

```yaml
- name: Pellah
  zone: bastok_markets
  position: [-2300, 1200, 100]
  role: aged carpenter who repairs city structures
  personality: gentle, slow-spoken, secretly an exiled Tarutaru sage
  starting_memory: "I helped rebuild the West Gate after the Quadav raid"
  voice_profile: voice_pellah.wav   # 30-sec sample for Higgs Audio cloning
  bark_pool:
    - "Mind the splinters."
    - "Wood remembers, you know."
    - "If you see Cid, tell him I'll have the brace done by Lightsday."
```

Server reads this, instantiates a Generative Agent profile, clones
Pellah's voice via Higgs Audio v2, places the actor in the zone. Done.
Five minutes from "I want a new vendor" to "Pellah is in the world".

For a Tier-3 hero NPC, the YAML grows to include daily schedules,
relationships, and goals. ~30 minutes of authoring vs the 4 hours a
hand-scripted hero NPC takes in the original FFXI codebase.

---

## Cross-references

- Combat RL details → `docs/AI_ORCHESTRATION.md`
- Voice cloning per NPC → `docs/VOICE_PIPELINE.md`
- NPC progression / vendor levelling → `docs/NPC_PROGRESSION.md`
- Reactive world (NPCs reacting to player damage / events) → `docs/REACTIVE_WORLD.md`
- LSB damage broker (feeds Tier-0 reactive responses) → `DAMAGE_PHYSICS_HEALING.md`
- Layered composition (where in the scene each tier lives) → `LAYERED_COMPOSITION.md`

---

## Status and open work

- [x] Design doc (this file)
- [x] Generative Agents cloned (`repos/_agents/generative_agents/`)
- [x] PettingZoo + Neural MMO cloned (`repos/_combat_rl/`)
- [x] Voice stack cloned (`repos/_voice/`)
- [ ] chharbot agent orchestrator (manages Tier 2/3 lifecycles)
- [ ] Tier-2 YAML schema + ingestion pipeline
- [ ] First Tier-2 NPC live in Bastok (Zaldon — full-loop test)
- [ ] First Tier-3 hero NPC live (Cid daily-life-loop)
- [ ] First Tier-4 trained policy (Goblin Pickpocket — most contained
      training scenario)
- [ ] Boss critic LLM hooked into Maat fight (smallest scope to prove
      the pattern)
- [ ] Density-tuning pass on Bastok Markets so the city *feels*
      crowded with autonomous beings, not just NPCs in T-poses
