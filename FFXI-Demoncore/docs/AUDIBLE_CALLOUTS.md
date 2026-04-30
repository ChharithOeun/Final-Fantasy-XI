# AUDIBLE_CALLOUTS.md

In Demoncore, the chatbox is **silent during combat**. No floating
"Skillchain: Fusion" text. No "Magic Burst! +250 damage" lines.
The information lives in the **voice** instead.

Players, NPCs, monsters, NMs, and bosses all **vocalize** their
combat actions. They grunt during weapon skills. They shout
"Skillchain open!" when they land a chain-starter. They yell
"Light!" when a Level-3 chain detonates. They snap "Magic Burst
Fire!" the instant a matching nuke lands. The party is a four-voice
round. Bosses participate too — and the boss critic LLM uses what
the party shouts to plan its next move.

This is the fourth observable system after **visible health**,
**AOE telegraphs**, and **hand signs**. Players read the world
via posture, color, hands, AND ear. Combat becomes literally
audible coordination.

---

## Why audible (the design rationale)

FFXI's chatbox-driven combat had a specific failure mode: nobody
read the combat log live. The chat scrolled too fast, the windowed
UI was too easy to mute, and the only people who actually parsed
"WAR closed Skillchain: Fragmentation" in real time were
dedicated chainsmithers staring at the log instead of the fight.

Audible callouts fix this completely:
- You hear the chain open whether you're staring at the boss or at
  your own ankles
- Voice has location — you know WHO opened from where they're
  standing
- Voice has urgency — you can hear panic in a "Magic Burst!" that
  came in too late
- It SOUNDS like a fight — the audio production lifts even casual
  combat to feel cinematic

Plus: this composes naturally with everyone's voice already being
cloned via Higgs Audio v2 per `VOICE_PIPELINE.md`. We're not
authoring new audio infrastructure — we're using infrastructure
already in the engine.

---

## The skillchain callout grammar

When a weapon skill is the **opener** of a potential chain:
> "Skillchain open!"

When the **closer** lands and detonates a Level-1 chain:
> "Closing — Fusion!"  
> "Closing — Distortion!"  
> "Gravitation!"

When a Level-2 chain extends into Level-3 (Light or Darkness):
> "**LIGHT!**"  
> "**DARKNESS!**"

When a magic burst lands during the burst window:
> "Magic Burst — Fire!"  
> "Magic Burst — Blizzard!"  
> "Magic Burst — Slow!"   ← ailment burst, see below
> "Magic Burst — Bind!"

When a player calls for a chain to be closed (no chain-opener
present yet, but inviting a teammate):
> "Setting up — close on me!"

When a chain *fails* to close (window expired, wrong WS):
> *grunt of frustration; specific to the player*

The callouts are **localized to the speaker's location**. Spatial
audio in UE5 places them with the actor. A WAR shouting "Skillchain
open!" from across the arena is positionally audible to the rest
of the party — they hear the direction and lean in.

---

## The 3x ailment-amplification mechanic (the new core gameplay)

**Magic Burst with status-ailment spells = 3x effectiveness for 30 seconds.**

This is the change the user identified as the key to unlocking
boss-team-play depth. CC mages are now apex damage.

### How it works

When a player Magic Bursts an *ailment* spell (Slow, Paralyze,
Bind, Sleep, Silence, Bio, Dia, Distract, etc) during the
post-skillchain window:
- The ailment lands as normal
- The ailment's **effect strength multiplied 3x**:
  - Slow becomes 3x slow (the target moves at 1/3 speed instead
    of 2/3)
  - Paralyze proc rate triples (33% per action -> 99%)
  - Bind duration triples
  - Sleep wake-on-damage threshold triples (much harder to wake)
  - Silence interrupt extension triples
  - Bio regen-suppression triples
- The amplified ailment lasts **30 seconds**
- The audible callout is **"Magic Burst — Slow!"** etc

This means a perfectly-timed CC chain — say a WHM hits Distortion
(water+ice), a SCH closes Magic Burst with Slow II — applies a
**90-second slow at 3x strength** on the boss. Boss attack speed
crashes. Boss can't kite. The party gets a clean burst window of
their own.

### Boss-fighting implications

**This is the key to defeating bosses.** Demoncore bosses are
balanced expecting parties to chain CC-bursts during specific
phases. A party that doesn't run skillchain CC-burst will hit
soft DPS walls in Wounded and Grievous phases. A party that does
will time their chain at the exact moment the boss telegraphs
his big AOE — landing a 3x Bind during the wind-up cancels the
animation and forfeits the boss's attack.

This is also where the boss critic LLM gets smart:
- Boss notices party landed 3x Slow → next phase, boss casts
  Erase on himself or adopts a wind-up routine that's interrupt-
  resistant
- Boss notices party landed 3x Silence → boss switches to
  weapon skills (no spells to interrupt) for 30s
- Boss notices party hasn't landed an ailment burst → boss
  presses harder, knowing he has the DPS edge

### Stacking

Different ailments stack independently. A target can be 3x Slow
+ 3x Bind + 3x Silence simultaneously = total lockdown for 30s.
Bosses have **diminishing returns** on stacking ailments — the
critic LLM detects rapid stacking and pre-positions Erase /
Status Resist procs.

Ailment-MB does NOT trigger off direct-damage spells. Only
status-ailments. The 3x multiplier is uniquely the reward for the
party that plays *strategy* not *DPS*.

---

## Per-actor voice production

### Player voices

Players record a **30-second voice sample** during character
creation (per `CHARACTER_CREATION.md`). The sample is fed to Higgs
Audio v2 to produce per-character clone audio for:

- 8 weapon-skill grunt variations (light/medium/heavy intensity)
- 12 skillchain element callouts ("Fusion!", "Light!", etc)
- 8 magic burst callouts (per element + status)
- 4 chain-opener callouts ("Skillchain open!", "Setting up!", etc)
- 6 chain-fail grunt variations
- 12 status-effect grunt vocalizations (poisoned, slept, paralyzed,
  silenced, etc — the visible-ailment audio cues per
  `VISUAL_HEALTH_SYSTEM.md`)
- 8 fight-cry barks per mood (alert, furious, fearful, etc)

Total ~58 voice lines per character. ~3 seconds each. ~3 minutes
of audio. Higgs generates the full set in ~5 minutes server-side
on a single GPU.

For NPCs (Tier 2 and 3 generative agents), the same library is
generated from the agent's `voice_profile` reference WAV.

For mobs (Tier 4), the library uses **stock voices per mob class**
(no per-instance variation). All Quadav warriors share one voice.
All Yagudo Acolytes share another. Etc. ~80 unique mob voices for
the entire bestiary.

### Bosses

Hero bosses get individual per-character voice libraries (full
~58-line set). Mid-tier NMs share by mob class. The boss critic
LLM occasionally inserts custom one-off lines into the boss's
combat barks based on what's happening — "I see what you're
doing, Tarutaru!" if the BLM has been kiting.

Implementation: chharbot pre-generates 5-10 contextual barks per
boss per game-day, caches in Redis, plays them mid-combat when the
critic flags them. ~1 minute of pre-gen per boss per day; cost ~0.

---

## The grunt vocabulary (universal)

Beyond the named callouts, Demoncore has a vocabulary of
**non-verbal vocalizations** that fire automatically per action:

| Action                          | Grunt type                              |
| ------------------------------- | --------------------------------------- |
| Weapon skill light (low TP)     | sharp short exhale                      |
| Weapon skill medium             | clear effort grunt                      |
| Weapon skill heavy (full TP+)   | deep yell                               |
| Heavy hit taken                 | breath knock-out                        |
| Critical hit taken              | sharp pain cry                          |
| Stunned                         | dazed groan                             |
| Slept                           | "...ah" then silence                    |
| Petrified                       | gasp cut short                          |
| Paralyzed mid-attack            | jerky vocalization, then full grunt     |
| Spell complete                  | small satisfied breath                  |
| Spell interrupted               | sharp annoyed exhale                    |
| HP at scuffed (90-70%)          | occasional pain breath                  |
| HP at bloodied (70-50%)         | labored breathing audible (continuous)  |
| HP at wounded (50-30%)          | wheezing + growled exertion             |
| HP at grievous (30-10%)         | gasping + occasional choke              |
| HP at broken (10-1%)            | continuous shallow gasps                |
| Dies                            | death rattle (per-character)            |

These are **race-categorized**. Galkan grunts are deeper and
shorter; Tarutaru higher and more verbal; Mithra have a slight
yowling lilt; Elvaan grunt politely (it's a thing); Hume are the
baseline.

The grunt audio reads the visible-health stage (per
`VISUAL_HEALTH_SYSTEM.md`) and adjusts continuously. A WAR at
wounded breathes hard *while attacking* — the player party hears
him struggling without needing a HP number. **The audio IS the
HP bar.**

---

## Mood-aware voice tone

The Higgs Audio v2 conditioning prompt per voice line includes
the actor's current `mood`. From `MOOD_SYSTEM.md`:

| Mood          | Voice tone for callouts                              |
| ------------- | ---------------------------------------------------- |
| content       | even, confident, slightly warm                       |
| gruff         | clipped, lower register, terse                       |
| furious       | louder, faster, cutting                              |
| fearful       | higher pitch, shaky, callouts shorter or unfinished  |
| alert         | crisp, professional, almost military                 |
| drunk         | slurred, drawling — chain callouts may be slightly off |
| contemplative | slower, lower energy                                 |
| mischievous   | playful, slight upward inflection                    |

A panicking healer screams "Magic Burst Cure!" with audible fear,
the rest of the party hears it and reads the situation as
critical. A mischievous Bondrak shouting "DARKNESS!" mid-tavern-
brawl sounds drunkenly triumphant. **The world has tone.**

---

## Audio mix and overlap

When 6 players + 5 mobs are all combat-vocalizing in a chaotic
fight, audio overlap could become noise. We handle it with:

1. **Priority lanes** — each callout type has an audio-mixer
   channel. Chain callouts are top priority (always audible).
   Grunts duck under chain callouts. Mob barks duck under both.
2. **Ducking** — when a chain callout fires, all other audio
   ducks 6dB for the callout's 0.4s duration.
3. **Spatial audio** — 3D positional. Distant Quadav grunts are
   quiet; the WAR next to you shouting Fusion is loud.
4. **Per-player filter** — the player can opt to suppress non-
   party callouts. Default: party callouts at full volume,
   non-party at 50%, mobs at 30%.

The mix is tuned in playtest to feel like a battle, not a
cacophony. Goal: a 6-player + 8-mob skirmish should be
*readable by ear* the way a good Star Wars space-battle is
readable by ear.

---

## Skillchain callout flow (worked example)

A 6-player party fighting Maat. Phase: bloodied. WAR opens with
Crescent Moon (compression).

```
T+0.0  WAR plants stance, swings:    *short exhale + sword swing SFX*
T+0.4  WAR's weapon skill connects:  white flash on Maat
T+0.5  WAR audibly shouts:          "Skillchain open!"
T+0.6  Other players hear the call.
T+1.0  NIN sprints in, signing
       Hyoton: Ichi (induration)     *6 seal clicks*
T+1.6  NIN's spell impacts:         "Closing — Distortion!"
       (water+ice, Level 2 chain)
T+1.7  Element halo on Maat: deep blue shimmer
       Visible-health flash for 2s on all party clients.
T+2.0  RDM in burst window casts
       Bio II (a status ailment).
T+3.4  Bio II lands during MB window:
       RDM shouts:                   "Magic Burst — Bio!"
       3x amplification activates: Maat's regen suppression
       triples for 30s. The audible callout is the only place
       the party learns this — no UI.
T+3.5  Chain halo brightens; 30s ailment timer starts.
T+3.6  Maat (in his bloodied phase, mood mischievous)
       audibly responds:             "Hmph. Now we're talking!"
       His attack-speed multiplier increases 5%
       (mischievous bosses press harder when respected).
```

The whole exchange is 3.6 seconds. The party didn't look at any
UI. They moved, shouted, and listened. The world responded.

---

## Boss audible callouts

Bosses also vocalize:

| Boss action                          | Boss line (Maat as example)                |
| ------------------------------------ | ------------------------------------------- |
| Phase transition pristine -> scuffed | "So you survived the warmup. Hmph."         |
| Phase transition to wounded          | "ENOUGH PLAYING."                           |
| About to use Asuran Fists II         | *fast inhale + foot-plant audio cue*        |
| About to use Final Heaven (5s cast)  | "...and this is for me."  (slow line)       |
| Counterstance activated              | *slow controlled breath*                    |
| Hundred Fists begins                 | "Watch this!"                               |
| Quivering Palm cursed                | (no line — silent cast; that's the tell)    |
| Maat hits "broken" stage             | "...you've earned this."                    |
| Final Word fires                     | "FAREWELL!"                                 |

A skilled player reads the boss's voice as much as his animations.
The combination of audible-cue + visible-health + AOE-telegraph
makes every encounter a **performance the boss conducts and the
party answers in tempo**.

---

## Mood event hooks (additions to event_deltas.py)

```
("skillchain_called",   "*hero*")           -> ("alert",    +0.20)
("skillchain_closed",   "*hero*")           -> ("content",  +0.20)
("magic_burst_landed",  "*hero*")           -> ("content",  +0.30)
("magic_burst_ailment_amplified", "*hero*") -> ("content",  +0.40)
("party_chained_light", "*hero*")           -> ("content",  +0.50)
("heard_panicked_call", "*civilian*")       -> ("fearful",  +0.30)
("heard_skillchain_call_nearby", "*hero*")  -> ("alert",    +0.15)
("boss_cried_phase_transition", "*civilian*") -> ("fearful", +0.40)
("boss_cried_ultimate_warning", "*civilian*") -> ("fearful", +0.60)
```

So a panicked civilian inside a building hears their ally healer
yell "Magic Burst Cure!" outside and goes fearful. Combat is
audibly contagious through bystanders, which makes city-wide
sieges feel real even to non-combatants.

---

## Status

- [x] Design doc (this file)
- [ ] Higgs Audio v2 line library generator (per-character ~58 lines)
- [ ] Stock-voice library for ~80 mob classes
- [ ] Audio mixer priority lanes + ducking config
- [ ] Skillchain callout trigger in BPC_SkillchainVisualizer
- [ ] Magic Burst callout trigger
- [ ] 3x ailment-amplification damage formula in LSB combat code
- [ ] Boss line library generator (per-encounter contextual barks)
- [ ] Mood-conditioned voice tone hook in voice synthesis
- [ ] Localization passes (Japanese voice library uses Japanese
      Higgs conditioning; same line set translated)
- [ ] Mob class -> stock voice mapping (~80 mob classes)
- [ ] First playtest: WAR + NIN + RDM Distortion -> Bio II MB
      with full audio
