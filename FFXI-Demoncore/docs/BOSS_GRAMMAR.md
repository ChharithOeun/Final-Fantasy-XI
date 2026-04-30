# BOSS_GRAMMAR.md

A boss in Demoncore is not a monster with a big HP pool. A boss is
a performance.

Every system we've built — visible health, AOE telegraphs, weight
physics, hand signs, mood, skillchains, KawaiiPhysics, generative
agents — composes into the boss encounter. The boss reads the
party. The party reads the boss. The fight is a duet of
observable behaviors, with the audience being the other side.

This doc is the recipe for building bosses that *feel*. It says
which systems compose, in what order, with what authoring
overhead.

---

## The five-layer boss recipe

Every Demoncore boss is built of five layers. Authoring happens in
roughly this order.

### Layer 1 — **The body** (mob_class + visible health archetype)

What players see when the boss spawns. SkeletalMesh + race-style
animation set + visible-health archetype + mood_axes.

Authoring time: 1-2 days for a hero boss (sculpted hero mesh + 12
seal anims if NIN-aligned + per-stage decals); 4-6 hours for a
"reskin of an existing mob class" boss.

### Layer 2 — **The repertoire** (signature attacks + AOE telegraphs)

7-12 unique attacks. Each has a wind-up animation, an AOE shape
(circle / cone / line / etc per `AOE_TELEGRAPH.md`), a damage
profile, and an element. The wind-up animations are the boss's
*tells* — the readable language a player learns over the
encounter.

A standard hero boss has:
- 3-4 small AOE attacks (~8m radius, 1.5s cast)
- 2-3 medium AOE attacks (~15m radius, 3s cast)
- 1-2 huge "ultimate" attacks (~25m radius, 5s cast, often
  arena-wide)
- 1 signature WS that closes a skillchain on the boss's side
  (rare; the boss participates in chains too)

Authoring time: ~1 hour per attack including animation, decal,
Niagara FX, sound, and damage tuning. ~10 hours per boss for the
repertoire.

### Layer 3 — **The phases** (weight + visible-health-driven
transitions)

Bosses do not have flat HP pools. As they take damage, they cross
visible-health stages (per `VISUAL_HEALTH_SYSTEM.md`) and on each
stage their behavior changes.

A boss's "phases" map directly to the visible-health stages:
- **Pristine (100-90%)**: standard repertoire, all attacks
  available
- **Scuffed (90-70%)**: opens with Hassou stance / signature
  buff. Faster wind-ups. Slightly more aggressive AOE rotation.
- **Bloodied (70-50%)**: drops one piece of armor (visible — say
  the helmet falls off) → weight drops → faster movement → faster
  attacks. Player sees the piece on the ground. Mood shifts to
  `furious`. Repertoire expands by 1-2 ultimate attacks.
- **Wounded (50-30%)**: enrages (visible: the boss roars; the
  visible-health "wing-droop" + breath-rasp gets *louder*, not
  hidden). Limited time to finish.
- **Grievous (30-10%)**: panic moves. The boss stops trying to
  finesse — drops giant arena-wide AOE every 5 seconds. Wind-up
  animations are visibly desperate (off-balance, lurching).
- **Broken (10-1%)**: the boss is *almost dead*. Stumbling,
  swaying. Some bosses kneel and accept the kill. Others go
  Berserker — one final massive attack the party must survive.

This is the visible health system at apex. Players can SEE the
boss's phase from across the arena — armor on the ground, the
slumped posture, the glow of an enrage timer in their wound. They
plan the kill window from line of sight, not from a damage meter.

Authoring time: ~30 min per phase to define which attacks unlock,
which posture+anim variants to use, what wind-up speed multiplier.
~3 hours per boss for the full phase ladder.

### Layer 4 — **The mind** (Tier-3 generative agent with critic LLM)

Hero bosses (Maat, Shadow Lord, Promathia) are full Tier-3
generative agents per `AI_WORLD_DENSITY.md`. They have:
- Full personality + backstory + journal
- Combat critic LLM that watches every 30 seconds and adjusts
  next-phase strategy
- Daily schedules that include their off-fight life (Maat
  practicing forms in his hut, Shadow Lord brooding on his throne)
- Mood propagation toward / away from the player based on the
  party's reputation, recent battle outcomes, the lore-state of
  the world

The critic LLM input includes:
- skillchain history (per `SKILLCHAIN_SYSTEM.md`)
- which players are using which spells (BLM cheesing? Silence
  next phase.)
- party's average mood (raid party visibly panicked? boss
  presses for the kill)
- recent boss-events (got Stunned mid-cast? Update strategy)

The critic outputs hints to the boss's combat AI:
```
{
  "next_phase_priority": "silence_blm" | "split_party" |
                         "stun_healer" | ...,
  "next_aoe_target": agent_id | center_of_mass,
  "should_use_ultimate": bool,
  "should_de-escalate": bool,
}
```

Authoring time: ~4-6 hours per boss for the agent profile + critic
prompt tuning. Done once; the LLM does the per-encounter
adaptation.

### Layer 5 — **The cinematic** (entrance, intro, defeat, aftermath)

Every boss has a Sequencer-driven cutscene per
`CINEMATICS_VIRTUAL_PROD.md`:
- **Entrance** (~10s): boss reveals from the environment. Camera
  slow-dollies in. Boss does a signature pose. Music swells.
- **Intro line** (~8s): voice-cloned bark in their personality.
  ("So you're the next set. Don't disappoint me.")
- **Defeat** (~12s): on death, the boss does a final pose, the
  camera respects the character (close-up, not zoom-out). They
  collapse with KawaiiPhysics-driven cloth drape.
- **Aftermath** (~8s, optional): a final soliloquy if the boss
  has lore to deliver. Mandalorian-style virtual-prod camera
  angles. Voice-cloned.

For non-hero (mid-tier) bosses, the cinematic is shorter — entrance
+ defeat only, ~6 seconds total.

Authoring time: ~4-6 hours per cinematic for hero bosses, ~1 hour
for mid-tier. Reusable Sequencer templates cut this in half on the
second-and-onward boss.

---

## Sample boss recipe — Maat

Maat is the canonical FFXI mid-game test (Genkai / Maat Fight).
Demoncore reimagines him.

**Layer 1 — Body**:
- mob_class: hume_m_master_hero (custom — sculpted hero mesh
  similar to Maat's retail look, more detail)
- visible_health archetype: hume_m
- mood_axes: [content, gruff, mischievous, furious, contemplative]
- KawaiiPhysics: cape + belt + sash all KP-driven for cinematic
  motion

**Layer 2 — Repertoire (12 attacks)**:
1. Asuran Fists (cone, 3 wide swings) — physical
2. Howling Fist (line, ~12m forward) — earth element
3. Tornado Kick (circle on Maat himself, ~6m) — wind
4. Counterstance (defensive pose; reflects player's next attack)
5. Hundred Fists (channeled, 6 fast melee swings — telegraphs the
   target with an arrow above their head ~2s before each)
6. Aura Smash (signature; AoE at target, ~10m, light element,
   3.5s cast)
7. Chi Blast (line, ~20m, dark element, 3s cast)
8. Final Heaven (ultimate — arena-wide, 5s cast, only at <50% HP)
9. Hand-to-Hand: Asuran Fists II (faster Asuran, only at <30% HP)
10. Earth-Ki Surge (donut, 6m inner / 18m outer, earth, 4s cast)
11. Quivering Palm (Single-target instant — instant-cast 1HP
    setup; if not dispelled in 10s the target dies)
12. Final Word (boss's death soliloquy attack — only fires if
    Maat is at <5% HP; one last desperate ultimate)

**Layer 3 — Phases (5 stages)**:
- Pristine (100-90%): standard four-attack rotation. Tests if
  party can hit basics.
- Scuffed (90-70%): adds Counterstance and Aura Smash. Mood goes
  `gruff` ("So you survived the warmup. Hmph.").
- Bloodied (70-50%): mood `mischievous` ("Now we're getting
  interesting!"). Drops a wrist-guard (visible armor piece on
  ground; weight drops 8 → faster attacks).
- Wounded (50-30%): enrage. Drops chest armor (weight drops 22 →
  much faster). Hundred Fists unlocks. Final Heaven becomes
  available.
- Broken (10-1%): mood `furious`. Quivering Palm available. Final
  Word ready.

**Layer 4 — Mind**:
```yaml
id: hero_maat
tier: 3_hero
role: hero_maat_test
personality: |
  Mid-fifties hume MNK, retired Bastok Mythril Musketeers Brigade
  Captain. Tests apprentice Adventurers as part of the Genkai
  ritual. Stern but never cruel; respects the attempt.
  Privately enjoys watching young fighters struggle and adapt.

backstory: |
  Survived Korroloka Tunnel during the Crystal War. Lost his
  brother in the same engagement. Now teaches because he believes
  Vana'diel's only hope is the next generation knowing how to
  fight smarter than his generation did.

goals:
  - "Test 100 apprentices this calendar year"
  - "Find one apprentice worth teaching for free"
  - "Pass on Asuran Fists technique before he's too old to demo it"

journal_seed: |
  Day 0. Three apprentices today. Two failed in pristine. One held
  out to wounded — that one I'll remember.

mood_axes: [content, gruff, mischievous, furious, contemplative]
```

The critic LLM watches:
- If the party uses BLM cheese (kiting + nuking from range), Maat's
  mood goes `gruff` and he opens with Tornado Kick to close the gap.
- If the party uses skillchains, Maat's mood goes `mischievous` and
  he uses Counterstance more often (he respects the technique).
- If a single player solos to bloodied (rare), Maat's mood goes
  `contemplative` and his attacks slow down (he's testing them
  individually now).
- Final Word at 5% only fires if Maat thinks the party "earned the
  full encounter" — Maat may yield instead and bow if the party
  has been particularly skillful.

**Layer 5 — Cinematic**:
- **Entrance**: Maat sits cross-legged in the center of the arena,
  tea cup beside him. He drinks, sets the cup down, stands without
  visible effort. "So. You're it for today."
- **Intro line**: voice-cloned Maat (Higgs Audio v2, conditioned on
  a 30s reference of an authoritative older man). "I'll go easy.
  ...At first."
- **Defeat (Maat loses)**: kneels respectfully. "...Excellent.
  You've earned the right." Hands the apprentice a Maat's Cap.
- **Defeat (party loses)**: shakes his head. "Better luck next
  time, kid." Tea cup vanishes, Maat sits back down.
- **Aftermath (rare; if the party does a Level-3 Light skillchain
  during the fight)**: Maat stands, claps slowly. "That. THAT was
  Vana'diel craft. I've not seen that in years." Mood permanently
  shifts to `content` toward this player; they get a bonus
  reputation gain.

Authoring time for Maat (full): ~3-4 weeks for one developer doing
all five layers. ~1 week with the boss being a "skin" of an existing
hero archetype.

---

## Boss difficulty curve (the player progression)

The first boss most players face is a Level-15 fomor in Korroloka
Tunnel. It uses the boss recipe at minimum:
- Body: mob_class fomor_warrior
- Repertoire: 4 attacks (one cone, one circle, one line, one
  signature WS)
- Phases: 3 (pristine / wounded / broken)
- Mind: Tier-2 (no critic LLM at this scope)
- Cinematic: 4-second entrance only

The last boss most players face (endgame Promathia) uses the
recipe at maximum:
- Body: hand-sculpted hero mesh, full visible-health
- Repertoire: 18 attacks across multiple combat schools
- Phases: 7 (pristine + 5 standard stages + a hidden 0% Resurrection
  Phase if the party survives)
- Mind: Tier-3 with full critic LLM, multi-encounter learning across
  all kills server-side (Promathia "remembers" parties that beat him)
- Cinematic: 8 separate Sequencer cuts across the encounter

Between these extremes, ~150 mid-tier bosses populate the world.
Each costs ~1 day of authoring with the recipe. The world fills out
quickly.

---

## Mood event hooks for bosses

Adding to `event_deltas.py`:

```
("boss_phase_transition", "*hero*")              -> ("alert",     +0.20)
("boss_phase_pristine_to_scuffed", "*civilian*") -> ("fearful",   +0.10)
("boss_phase_to_wounded", "*civilian*")          -> ("fearful",   +0.30)
("boss_enraged", "*civilian*")                   -> ("fearful",   +0.50)
("boss_defeated", "*hero*")                      -> ("content",   +0.40)
("boss_defeated", "*civilian*")                  -> ("content",   +0.30)
("party_wiped", "*civilian*")                    -> ("melancholy",+0.30)
("party_wiped", "*hero*")                        -> ("furious",   +0.30)
```

A city under siege from a boss-grade beastman raid has visibly
escalating panic in its civilian NPCs as the boss progresses
through phases. This is alive worldbuilding.

---

## What this composition delivers

A finished Demoncore boss fight has:

- **No HP bar** for the boss; players read his armor falling off,
  posture slumping, breathing getting ragged
- **AOE telegraphs visible only on player-cast spells**, not the
  boss's; players read his wind-up animations to dodge
- **Weight-driven combat** where the boss's heavy armor makes him
  slow until it falls off in later phases, where he becomes a
  blur — the player has to adapt mid-fight
- **Skillchain windows** the party plans across the boss's
  attack rotation; perfectly-timed Level-3 Light during a quiet
  3-second window is the apex DPS moment
- **NIN hand signs** weaving Hyoton: Ichi at full sprint to
  contribute one element to a chain
- **Mood propagation** through bystander NPCs in the area — the
  city panics, the boss escalates accordingly via the critic LLM
- **Cinematic entrances and defeats** that feel like a film,
  Mandalorian-style virtual production camera
- **Voice-cloned bosses** delivering personalized intro and defeat
  lines that change based on the party's behavior

This is the apex of all our pillars. Every system pulls its weight
in the most important moments of play. **The boss fight is the
shrine our entire engine has been pointing at.**

---

## Status

- [x] Design doc (this file)
- [ ] First boss recipe execution: Maat (canonical reference)
- [ ] Second boss: Quadav Roundshield (mid-tier, RL-policy-driven)
- [ ] Third boss: Shadow Lord (full Tier-3, multi-server-encounter
      learning)
- [ ] Boss-recipe authoring template: a YAML schema + a UE5 BP
      template that scaffolds the 5 layers per boss
- [ ] Tier-3 critic LLM prompt library — 6-8 hand-tuned prompts
      shared across all bosses
- [ ] First playtest: 6-player raid on Maat with the full visible
      stack
