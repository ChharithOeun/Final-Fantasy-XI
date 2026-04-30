# TUTORIAL_BASTOK_MINES.md

The first 90 minutes of a Demoncore player's life. Where they
learn the visible/audible/weight grammar without a single tooltip.

This doc is the level designer's contract for **Bastok Mines as
the tutorial zone**. The zone is deliberately small, controlled,
and choreographed so each system unlock from
`PLAYER_PROGRESSION.md` is taught by encounter, not by text.

The player's experience: dropped into a working mining city,
hands them a tool, and the city itself shows them how everything
works.

---

## Why Bastok Mines (the zone choice)

Bastok Mines is canonical FFXI's first lvl 1-15 zone for hume
players. We use it as the universal tutorial regardless of which
nation the player picks (other nations get a brief "mining
exchange visit" intro instead of starting from scratch). Reasons:

- **Bounded vertical space** — the elevator + mine shafts + smithy
  give natural scene boundaries to teach individual mechanics
- **Industrial ambient sound** — perfect cover for the audible
  callout introduction
- **Existing iconic NPCs** — Cid, Pellah, Bondrak, Volker, Mavi
  the pickpocket are all already authored with full tier-2/3
  agent profiles
- **Multiple structure types** — wood crates, stone walls, metal
  forges teach the damage-physics system per
  `DAMAGE_PHYSICS_HEALING.md`

---

## The choreographed first 90 minutes

### Minute 0-3: Arrival cinematic
- Player created character spawns at Bastok Mines elevator landing
- Cinematic: Cid greets them. "Apprentice. Glad you made it."
  Voice-cloned, mood `content`.
- No HP bar shown to player. They look at Cid; they read his
  posture. He's healthy. Visible-health system is implicit.
- A pigeon flies across the plaza (Tier-0 ambient agent, audible
  flapping) — establishes "the world is alive even before you
  do anything"

### Minute 3-10: First weight + movement lesson
- Cid hands the player a **Bronze Sword (weight 3)**. The
  character's posture lifts ~1cm (visible scale change).
- Quest: "Bring this hammer to Pellah at the carpenter shop."
- Hammer weighs 12. Player notices their character moves slower
  while carrying it. The HUD shows their weight number.
- Pellah greets them, hands back a Cotton Doublet (weight 4).
  Tutorial cue: equipping vs carrying — equipped weight matters
  for combat, carry-weight matters for movement.

### Minute 10-25: First weapon skill + skillchain marker
- Cid sends them to fight a Goblin Pickpocket near the south
  gate (level 1, very weak — designed to be hit, but to land a
  weapon skill at low TP)
- The fight is the first audible-grunt teaching moment. Player's
  character grunts on each swing. Goblin grunts back.
- Visible-health stage transitions: goblin goes scuffed →
  bloodied → wounded → broken across the fight. The player can
  see his blood, his limp, his desperate posture.
- Player's first weapon skill lands. Chain marker (white flash)
  on the goblin. Player audibly shouts "Skillchain open!" without
  knowing what that means yet.
- Cid (watching) shouts "Close it!" with mood `mischievous`. The
  player has 8 seconds to cast a second WS. They miss the window
  this time. Cid: "...next time."
- This teaches: chain marker, audible callout, the close window
  exists.

### Minute 25-40: First reveal-skill (job-dependent)
- Player chooses primary job at this point. The job determines
  which reveal skill they're handed:
  - WHM → Scan (free Cure spell first; Scan unlocks at lvl 20)
  - BLM → Drain
  - THF → Mug (introduced at lvl 25, used in tutorial early)
  - WAR/PLD → /check command
- Quest: "Find an old fomor in the mine shafts. Tell me what
  you can about it."
- Player descends, encounters a fomor (sleeping; non-aggro). Uses
  their reveal skill. Sees vague descriptor — "Tough; (looks
  furious); (slightly hurt)". This teaches:
  - HP isn't a number — it's words.
  - Mood is part of the world.
  - Damage state is also a word.

### Minute 40-55: First intervention preview
- Quest: "A miner is wounded — get him a Cure from the apothecary."
- Player buys Cure I from a vendor, returns to find the miner
  visibly bloodied (slumped, bleeding decals).
- They cast Cure I. The miner audibly grunts in relief, posture
  straightens, decals fade.
- This teaches: cures heal visibly. There's no number. The miner
  *looks* better.

### Minute 55-75: First skillchain success
- Cid sets up a controlled training fight. He partners with the
  player against a designed dummy mob (a mining cart automaton —
  no aggro, no death penalty).
- Cid opens a chain. The chain marker appears. Cid shouts:
  "Closing — Liquefaction!" — but he stops short. He says
  (post-fight): "You close it next time. Same setup tomorrow."
- The player practices the timing in a sandboxed scenario. After
  3-5 successful chain closes, they audibly shout
  "Distortion!" themselves. The voice clip plays through their
  cloned voice.
- This is the first **emotional payoff moment**. The player
  closed a chain, by themselves, and heard their character call
  it out. They made the world act.

### Minute 75-90: First boss-grade encounter
- Tier-1 boss: a Goblin Smithy (level 5, but with the boss recipe
  per `BOSS_GRAMMAR.md` minimum: 4 attacks, 3 phases, no critic).
- Cinematic entrance: 4 seconds. Goblin Smithy reveals from a
  side tunnel, swings hammer.
- The fight teaches phase transition. Goblin starts pristine,
  goes scuffed, then wounded, then broken. At each phase the
  goblin's posture and breathing change. Player reads the fight
  by sight.
- Goblin Smithy has one named attack: Hammer Slam (cone
  telegraph, 1.5s cast). The first cast hits the player. The
  next two casts the player sidesteps. Audible victory grunt.
- Defeat cinematic: Goblin collapses, drops a small piece of
  Bronze Ore. Cid: "That's mining work, kid. Welcome."

After 90 minutes the player has been taught:
1. No HP bars; read posture (`VISUAL_HEALTH_SYSTEM.md`)
2. Weight matters (`WEIGHT_PHYSICS.md`)
3. Skillchain markers + audible callouts (`SKILLCHAIN_SYSTEM.md`,
   `AUDIBLE_CALLOUTS.md`)
4. Reveal skills are limited (`VISUAL_HEALTH_SYSTEM.md`)
5. The world has tone (`MOOD_SYSTEM.md`)
6. Bosses have phases (`BOSS_GRAMMAR.md`)

Without reading a single tutorial popup. Without watching a
single text wall. The mining city taught them.

---

## Tutorial agents (already authored)

Per `agents/`:
- `cid.yaml` — quest-giver and chain-closing partner
- `pellah.yaml` — carpenter quest hand-off
- `volker.yaml` — appears at minute 75-ish for the boss intro
- `vendor_zaldon.yaml` — south-gate vendor (incidental)
- `pickpocket_lurking_near.yaml` — first combat target (lvl 1
  goblin variant — actually mob_class goblin not the Mavi NPC)

Each NPC's existing schedule/personality drives the tutorial
flow naturally. No special-case "tutorial logic" code needed —
the orchestrator already runs them as live tier-2/3 agents.

---

## Tutorial-specific tags in bastok_layered_scene.py

When the layered scene script runs, NPCs that are tutorial-active
get a `Tutorial:gate_<n>` tag so the LSB tutorial logic can hook
into their event stream:

- `Tutorial:gate_arrival` — Cid (minute 0)
- `Tutorial:gate_weight` — Pellah (minute 10)
- `Tutorial:gate_first_combat` — first goblin (minute 15)
- `Tutorial:gate_reveal_skill` — fomor in mine shafts (minute 25)
- `Tutorial:gate_intervention` — wounded miner (minute 40)
- `Tutorial:gate_chain` — Cid (minute 55)
- `Tutorial:gate_boss` — goblin smithy (minute 75)

These tags are inert except during the first 90 minutes of a new
character. After that they age out (or the player has already
moved past them).

---

## Status

- [x] Design doc (this file)
- [ ] Tutorial Goblin Pickpocket (lvl 1 variant) mob_class entry
- [ ] Tutorial Goblin Smithy (lvl 5 boss-recipe) full YAML
- [ ] Cinematic sequencer for arrival (3 min)
- [ ] Cinematic sequencer for first chain (Cid partner)
- [ ] Cinematic sequencer for boss (Goblin Smithy entrance + defeat)
- [ ] Wounded Miner NPC (incidental Tier-1 actor for the intervention preview)
- [ ] Tutorial gate tags in bastok_layered_scene.py
- [ ] First playtest: fresh character, time-to-90 minutes, every gate hits
