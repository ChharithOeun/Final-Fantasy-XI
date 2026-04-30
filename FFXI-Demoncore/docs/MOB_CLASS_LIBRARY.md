# MOB_CLASS_LIBRARY.md

The world is populated by ~80 mob classes — Quadav, Yagudo, Orc,
Goblin, Tonberry, Naga, Bee, Slime, Skeleton, Sahagin, Bug,
Demon, Dragon, plus their job sub-variants (Quadav Footsoldier,
Roundshield, Helmsman, etc).

This doc is the catalog. Each entry includes:
- Visual archetype (per `VISUAL_HEALTH_SYSTEM.md`)
- Element affinity (per `MOB_RESISTANCES.md`)
- Default RL-policy class (per `AI_WORLD_DENSITY.md` Tier 4)
- Default voice library (stock per class, not per instance)
- Per-class signature attacks + AOE telegraphs
- Damage profile + level range

The library is the menu. Boss authors pick a class, override
specifics, and ship a new boss in 4-6 hours per the
`BOSS_GRAMMAR.md` recipe.

---

## The 13 mob families (and their sub-variants)

### 1. Quadav (turtle-folk, lightning-aligned)

Mechanical turtle-people from Beadeaux. Heavy armor, rectangular
shields, thick scales. Slow to start, devastating up close.

Affinity: lightning. Weak to: water. Strong vs: wind.

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Quadav Footsoldier| 8-15  | front-line      | Shield Bash (cone)         |
| Quadav Roundshield| 12-20 | tank/aggro      | Tortoise Stomp (circle on self) |
| Quadav Helmsman   | 18-28 | leader          | Scaled Mail (def buff)     |
| Quadav Minelayer  | 20-30 | trap-laying     | Mine Trap (placed AOE)     |
| Quadav Healer     | 25-35 | mob-side healer | Cure spells + intervention timing |
| Quadav Lifeguard  | 30-40 | high-tier tank  | Drainkiss (single-target drain) |

Voice library: low resonant croaking, deliberate meter. "[gruff Quadav speech]" with the Quadav-shell click as punctuation.

### 2. Yagudo (bird-folk, water-aligned)

Avian humanoids from Castle Oztroja. Religious order; cast
spells; well-organized. Light armor, ranged-favored.

Affinity: water. Weak to: lightning. Strong vs: fire.

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Yagudo Acolyte    | 10-18 | front-line      | Beak Lunge (line)          |
| Yagudo Initiate   | 15-25 | scout           | Choke Breath (cone)        |
| Yagudo Cleric     | 20-30 | mob-side healer | Banishga (light AOE)       |
| Yagudo Avatar     | 30-45 | mid-boss        | Hundred Wings (multi-line) |
| Yagudo High Priest| 40-55 | high-rank       | Holy Cross (donut)         |

Voice: high-pitched chittering with feather-rustle audio cue. Religious cadence in speech.

### 3. Orc (warrior-people, fire-aligned)

Brutal warriors from the Davoi region. Heavy weapons, heavy
armor, blood-knight aesthetic.

Affinity: fire. Weak to: ice. Strong vs: wind.

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Orc Footsoldier   | 10-20 | front-line      | Cleaver (line)             |
| Orc Trooper       | 18-28 | mid-tier        | Headbutt (single-target stun) |
| Orc Warmachine    | 30-45 | heavy-armor     | Earth-Crusher (donut)      |
| Orc Crouchlear    | 40-55 | RL-policy mob   | Wolf-cub-style positional pack |

Voice: deep guttural, sparse vocabulary, lots of grunts and chest-beats.

### 4. Goblin (opportunist-people, earth-aligned)

The classic FFXI opportunist mobs. Multiple sub-variants. Bombs,
pickpockets, smiths.

Affinity: earth. Weak to: wind. Strong vs: lightning.

Already covered: `Goblin Pickpocket` (Tier 4, full YAML at
`agents/goblin_pickpocket.yaml`).

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Goblin Pickpocket | 5-15  | already done    | (per agents/)              |
| Goblin Smithy     | 10-20 | tutorial boss   | Hammer Slam (cone)         |
| Goblin Bomber     | 18-28 | suicide-attacker| Bomb Toss (placed AOE; bomb mob dies) |
| Goblin Trader     | 12-22 | quest-giver/mob | Pilfer (steals gil)        |

Voice: high-pitched cackle, "Heh heh heh!" punctuation.

### 5. Tonberry (creep-people, dark-aligned)

Slow, lethal, terrifying. The "knife and lantern" iconic FFXI mob.

Affinity: dark. Weak to: light. Strong vs: nothing significant.

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Tonberry Stalker  | 30-45 | slow-pursuit    | Knife (massive single-target damage) |
| Tonberry NM       | 60-75 | NM              | Doton: Ichi (bind seal sequence) |
| Master Tonberry   | 80-90 | endgame NM      | Everyone's Grudge (wipe-tier) |

Voice: shuffling silence punctuated by sudden whispered words. The Tonberry walks slow — every step is a sound cue.

### 6. Naga (NIN-school serpent-folk, water-aligned)

Snake-people, naturally NIN-aligned. Use hand signs (per
`NIN_HAND_SIGNS.md`). Sprinting casters.

Affinity: water. Weak to: lightning.

| Sub-variant       | Level | Role            | Notable skill              |
| ----------------- | ----- | --------------- | -------------------------- |
| Naga Renja        | 25-40 | sprint-NIN      | Hyoton: Ichi (sprint-cast) |
| Naga Hatamoto     | 40-55 | mid-boss        | Suiton: Ichi escape + counter |
| Naga Houju        | 60-75 | high-NM         | Aisha (debuff stack via signs) |

Voice: hissing speech, chakra-flow audio cue between hand signs.

### 7-13: Compressed
For brevity, the remaining 7 families follow the same structure.
Detailed per-family entries to be authored as we approach those
zones in development:

- **Bee** (wind-aligned): Honey-burst (placed AOE), Sting (poison)
- **Slime** (rotating elemental): Bomb-Toss, Engulf (single-target)
- **Skeleton** (dark-aligned): Bone Crusher (line), Ravage (cone)
- **Sahagin** (water-aligned): Lariat (cone), Maelstrom (donut)
- **Bug** (earth-aligned): Pollen Burst (donut buff for self), Sting
- **Demon NM** (dark-aligned): Soul Voice (silence AOE), Aero IV
- **Dragon NM** (variable, per-individual): Wing Beat (cone),
  Spike Flail (donut), Fire Breath (line)

Each family has 4-6 sub-variants spanning level 1-90.

---

## Per-class voice library (stock voices)

Per `AUDIBLE_CALLOUTS.md`, mob classes share **stock voice
libraries** (no per-instance variation). All Quadav Helmsmen
share one voice. All Yagudo Acolytes share another.

Stock voice authoring: ~30 minutes per class for the audible-
callout vocabulary (~58 lines per class). Total: ~80 classes
× 30min = ~40 hours of voice authoring across the entire
bestiary. Doable in 1 week of focused production.

---

## Element-affinity glow shaders

Per `MOB_RESISTANCES.md`, each mob has a visible affinity glow
that intensifies as the mob takes damage. Authoring is one
material parameter per element + one Niagara emitter:

- 8 affinity-glow shaders (one per element)
- Each is parametric — turn on/off via a material parameter at
  runtime
- Authoring time: ~4 hours total for the 8 shaders

The shaders are designed to be subtle in `pristine` and
unmistakable in `wounded` — so a new player learns affinity by
seeing a wounded mob's clear glow, then over time learns to
read the same cues earlier.

---

## RL-policy training

Per `AI_WORLD_DENSITY.md` Tier 4, each mob class has a trained
ONNX policy. Training pipeline lives in
`repos/_combat_rl/training/<mob_class>/`:

1. Authoring: define state-feature vector + action space for the class
2. Synthetic-player environment in PettingZoo + Neural MMO 2.0
3. ~24-72 hours of training per class on a single A100
4. Export ONNX → ships with the mob

For mobs that share archetypes (e.g. all Quadav use the same
state-action layout), training cost is paid once per archetype,
not per sub-variant.

---

## Mob class YAML schema

Each mob class gets a YAML in `agents/_mob_classes/<class>.yaml`.
Format follows `agents/_SCHEMA.md` Tier 4:

```yaml
mob_class: quadav_helmsman
race: beastman_quadav
gender: n
voice_profile_stock: /Content/Voices/StockMobs/quadav_helmsman.wav

# Affinity per MOB_RESISTANCES.md
aligned_element: lightning
weak_to: water
strong_against: wind

# RL policy per AI_WORLD_DENSITY.md
policy_onnx: /Content/AI/Policies/quadav_helmsman_v1.onnx
state_features: [...]   # 13-feature vector
action_space: [...]     # 7 actions

# Visible health archetype
visible_health_archetype: mob_quadav

# Default level range (instances clamp to this in spawn data)
level_range: [18, 28]

# Damage response per existing patterns
damage_response:
  on_aoe_near: ...
  on_outlaw_nearby: ...
```

---

## What this enables

A boss author doesn't reinvent any wheels. They:
1. Pick a mob_class entry
2. Override 1-2 specifics for the boss flavor
3. Apply the BOSS_GRAMMAR.md 5-layer recipe on top
4. Author the cinematic Sequencer

Total: ~1-2 days for a mid-tier boss. ~4-6 days for a hero boss
that needs hand-sculpted mesh + full critic LLM tuning.

---

## Status

- [x] Design doc + 13-family table (this file)
- [ ] Voice library authoring sweep (~40 hours, 80 classes)
- [ ] Affinity-glow shader library (8 shaders)
- [ ] First 10 mob class YAMLs:
  - [x] goblin_pickpocket (already done as Tier 4 exemplar)
  - [ ] quadav_helmsman
  - [ ] yagudo_cleric
  - [ ] orc_footsoldier
  - [ ] tonberry_stalker
  - [ ] naga_renja
  - [ ] sahagin_swordsman
  - [ ] skeleton_warrior
  - [ ] bee_soldier
  - [ ] goblin_smithy (tutorial-zone boss)
- [ ] RL training pipeline scaffolds (per archetype, ~6 archetypes)
- [ ] First playtest: Quadav Helmsman vs party of 4
