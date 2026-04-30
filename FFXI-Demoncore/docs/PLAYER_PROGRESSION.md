# PLAYER_PROGRESSION.md

How a Demoncore player grows from level 1 to endgame — and what
they actually unlock along the way. The systems we've designed
(visible health, weight, skillchains, intervention, hand signs,
audible callouts) need a progression path that **introduces them
gradually** so a new player doesn't drown.

This is the player-side mirror to `NPC_PROGRESSION.md`.

---

## Three-axis progression

A player progresses on three independent axes. None is a "level"
in the FFXI sense — they're separate growth dimensions that
combine to define your character.

### 1. Job Level (familiar)
Vanilla FFXI levels 1-99 per job. Hardcore-death (per
`HARDCORE_DEATH.md`) means death at lvl 99 is permanent.
Capped at 99 per job; secondary job at half level (lvl 99 main +
lvl 49 sub).

### 2. Skill Mastery (NEW)
Per-spell, per-weapon-skill, per-ability mastery. Tracks how well
you actually USE the skill. Levels 0-5 per skill.

Skill mastery is gained through use:
- Casting a spell at the right moment (during MB window): +1 mastery exp
- Closing a skillchain perfectly (within 0.3s of optimal): +2 mastery exp
- Surviving a round at low HP without using a defensive cooldown: +1 mastery exp on your tank skills
- Successfully intervening: +3 mastery exp on the cure/buff/debuff family

Mastery 5 unlocks:
- Skill animation gets visibly more refined (less wobble, more
  decisive form)
- 10% reduced cast time on that specific spell
- Audible "veteran" voice variant for callouts (more confident
  delivery)

Mastery is **tied to YOU**, not your gear. A WHM can transfer
to RDM and bring their Cure-mastery with them — they just can't
cast WHM-only spells until they level RDM.

### 3. Reputation + Honor (familiar)
Per-nation, per-NPC. Already designed in `HONOR_REPUTATION.md`.
Affects who sells what, who teleports who, what quests open.

---

## Unlock cadence (the gentle introduction)

Demoncore's systems are heavy. A first-day player would drown if
all of them were active at once. The progression **introduces
each system at a specific level**:

| Level | System unlock                                            |
| ----- | -------------------------------------------------------- |
| 1     | Visual health (no HP bars; learn to read posture)        |
| 1     | Weight (you can see your weight; movement reflects it)   |
| 5     | /check command works (vague descriptor only)             |
| 8     | First weapon skill — chain marker visual + audible       |
| 12    | First skillchain (Level 1) tutorial in Bastok Mines      |
| 15    | First boss test (lvl-15 Korroloka fomor; min boss recipe)|
| 18    | Magic Burst window awareness (visible halo introduced)   |
| 20    | First reveal skill — Scan or Drain (player chooses job)  |
| 25    | THF/Mug introduction (if THF — reveals tied to job)      |
| 30    | Hand signs for NIN (full sign-system unlocks)            |
| 40    | Tier-2 skillchain (Fusion/Distortion/Fragmentation/      |
|       |   Gravitation) — tutorial in Crawler's Nest              |
| 45    | Intervention MB window awareness (defensive twin opens)  |
| 50    | Genkai 1 — Maat fight unlocks                            |
| 55    | Tier-3 skillchain (Light/Darkness) — taught by NM hint    |
| 60    | Boss critic LLM unlocks for Genkai-tier bosses           |
| 65    | Dual-cast unlock starts becoming reliable                |
| 70    | Outlaw bounty + cross-faction PvP unlocks                |
| 75    | Endgame BCNM/Limbus content                              |
| 85    | Mythic boss-tier (Promathia) unlocks                     |
| 99    | Hardcore-death penalty active (1hr permadeath timer)     |

Each unlock is preceded by a **tutorial NPC encounter** (per
`AI_WORLD_DENSITY.md` Tier 2-3) that teaches the new mechanic
through a quest, dialogue, or combat scenario. Players don't
read patch notes. They learn from Cid, Volker, Maat, etc.

---

## Genkai (limit break) - the rite-of-passage tests

FFXI's Genkai system is preserved exactly. Demoncore expands the
boss recipe per `BOSS_GRAMMAR.md` so each Genkai is genuinely a
test of every skill the player should have learned by that level:

- **Genkai 1** (lvl 50 → 55 cap): Maat fight. Tests skillchain
  reading + intervention timing + visible-health stage reading.
- **Genkai 2** (lvl 55 → 60): NM in Konschtat Highlands. Tests
  weight-cycling + AOE telegraph dodging.
- **Genkai 3** (lvl 60 → 65): NM in Pashhow Marshlands. Tests
  the 3x ailment-MB stack mechanic.
- **Genkai 4** (lvl 65 → 70): NM in Tahrongi Canyon. Tests
  Tier-2 skillchains + audible coordination.
- **Genkai 5** (lvl 70 → 75): Maat rematch (much harder). Tests
  *everything*. Maat's mood is `gruff` (he remembers the first
  fight, expects more this time).

Each Genkai is a **forced solo encounter**. No party allowed.
This is the pure test of the player's skill, with no carry from
group play. Players who can't solo Maat at 70 don't progress.

---

## Death and the hardcore penalty

Per `HARDCORE_DEATH.md`:
- Levels 1-89: normal death = level loss + minor XP penalty
- Levels 90-98: death = level loss + 2-day Reraise lockout
- Level 99: death = **1-hour permadeath timer**, then your
  character becomes an AI-controlled Fomor in the world

This is the difficulty pillar that makes mastery actually matter.
A level 99 player who dies sloppily doesn't get to retry — they
become a fomor in the world that other players might encounter
and (briefly) recognize.

The threat of permadeath at the apex is what makes endgame players
**actually use** the intervention timing, the weight-cycling, the
audible callouts. There is no autopilot.

---

## Skill mastery exemplars (worked examples)

### A new WHM at lvl 5
- Cure I mastery: 1
- Reads HP bands of party members from posture (no HP bars)
- /check tells them "Easy Prey, slightly hurt" — they cast Cure I
- Audible callout: their own untrained voice, "Cure!" (no
  "Magic Burst" yet because they don't know what that is)

### Same WHM at lvl 50, mastery 4 in Cure IV
- Cure IV mastery: 4
- Cast time reduced 10% (from 3.5s to 3.15s)
- Successful intervention timing: ~50% in pristine, lower in
  chaotic phases
- Voice callout: "Magic Burst — Cure IV!" with more confident
  delivery
- Has earned the right to wear Cure-coral gear (visible aesthetic
  reward)

### Endgame WHM at lvl 99, mastery 5 across all Cures
- Quick Magic + Stoneskin-QM-cooldown rotation enables Cure V
  intervention on Light skillchains
- 90%+ intervention success rate
- Voice callout audibly authoritative ("Magic Burst — Cure V!")
- Other players hear that voice and know they're with a
  veteran. Reputation ripples forward.

---

## What this enables

Player progression in Demoncore isn't a stat bar — it's a series
of capability unlocks each tested by a real combat scenario, and
a mastery layer that makes the same player's casts genuinely
better than a fresh-rolled alt.

The unlock cadence ensures the systems we designed don't drown
new players. The mastery axis ensures veterans have a long, real
growth runway. The hardcore penalty at the apex ensures the
mastery actually matters.

---

## Status

- [x] Design doc (this file)
- [ ] LSB skill_mastery table + per-cast event hooks
- [ ] Mastery exp formula per skill family
- [ ] Tutorial NPC quests for each unlock level (~25 quests)
- [ ] Mastery-5 audio variants (refined voice for ~58 lines per character)
- [ ] Mastery-5 animation variants (less wobble, more decisive form)
- [ ] Genkai boss redesign per the 5 tests above
- [ ] First playtest: WHM Mastery curve from 1-5
