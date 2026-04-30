# SKILLCHAIN_SYSTEM.md

Skillchains are FFXI's signature combat depth mechanic. Two or more
weapon skills closed in a precise window combine into a named
elemental burst. A mage who casts a matching-element spell in the
follow-up window — the **Magic Burst window** — multiplies the
combined damage by 50% or more.

In Demoncore, skillchains are louder, more visible, and more
dangerous to enact wrong. Every system we've built composes into
them:

- The skillchain detonation **flashes target HP for 2s** to the
  whole party (per `VISUAL_HEALTH_SYSTEM.md` reveal table)
- Magic Burst color-codes the AOE telegraph by skillchain element
  (per `AOE_TELEGRAPH.md`)
- Heavy weapons (`WEIGHT_PHYSICS.md`) hit the skillchain with more
  base damage but the window is harder to time
- NIN hand signs (`NIN_HAND_SIGNS.md`) can substitute for up to one
  weapon skill in a chain
- The boss critic LLM watches the skillchain pattern and adapts
  (per `AI_WORLD_DENSITY.md` Tier 4 bonus)

The result: players who master skillchains play a game inside the
game — chainsmithing — that veterans practice for years. Players
who don't still get plenty of damage from auto-attacks; they just
miss the apex spike.

---

## The skillchain table (canonical FFXI elements)

Two-weapon-skill combinations form a Level-1 skillchain. Three or
more form Level-2 / Level-3 chains with bigger names and bigger
damage.

### Level 1 (any two compatible weapon skills)

| Element     | Closes from properties                          |
| ----------- | ----------------------------------------------- |
| Liquefaction (fire) | Impaction → Liquefaction, Detonation → Liquefaction |
| Induration (ice)    | Impaction → Induration, Compression → Induration |
| Reverberation (water) | Detonation → Reverberation                    |
| Detonation (wind)   | Compression → Detonation, Scission → Detonation |
| Scission (earth)    | Liquefaction → Scission, Reverberation → Scission |
| Compression (dark)  | Induration → Compression, Reverberation → Compression |
| Transfixion (light) | Scission → Transfixion, Compression → Transfixion |
| Impaction (lightning) | Transfixion → Impaction                     |

### Level 2 (extending a Level-1 chain)

| Element        | Built from L1 + matching properties        |
| -------------- | ------------------------------------------ |
| Fusion (fire+light) | Liquefaction + Transfixion             |
| Fragmentation (wind+lightning) | Detonation + Impaction      |
| Distortion (water+ice) | Reverberation + Induration         |
| Gravitation (earth+dark) | Scission + Compression           |

### Level 3 (apex — Light, Darkness)

| Element        | Built from L2 + L2                         |
| -------------- | ------------------------------------------ |
| Light          | Fusion + Fragmentation, or two Lights      |
| Darkness       | Distortion + Gravitation, or two Darknesses|

These are the canonical FFXI tables, preserved exactly. Demoncore
doesn't change the skillchain math — we change what the chain
*looks and feels* like when it lands.

---

## The visible language of skillchains

Every part of a skillchain is observable on the battlefield:

### 1. Weapon skill wind-up (~0.8s)

Each weapon skill has a unique wind-up animation. Heavy weapons
(`weapon_weight > 14`) start with a deliberate stance shift —
players know a Curtana's about to swing because the player visibly
plants their feet. This is the player-side equivalent of mob
animation tells (per `AOE_TELEGRAPH.md`).

The first skill in a chain pulses a small **white flash** on the
target on impact. This is the chain marker — chainsmiths use it to
time their follow-ups.

### 2. Skillchain detonation (~0.5s)

When the second weapon skill closes a chain, a **named element
burst** detonates on the target. The element's color (per
`AOE_TELEGRAPH.md` palette) wraps the target as a brief glow:

- Liquefaction: orange + crackling fire wisps
- Induration: cyan + frost crystallization
- Reverberation: deep blue + concentric water rings
- Detonation: pale green + wind-knife slash
- Scission: umber + earthen rubble
- Compression: desaturated purple + dark inhalation
- Transfixion: white-gold + radial lance
- Impaction: yellow-violet + fractal lightning

Crucially, the detonation **flashes the target's HP for 2 seconds**
to the entire party (this is the canonical reveal-skill triggered
by Magic Burst >100 dmg, per `VISUAL_HEALTH_SYSTEM.md`). This is
one of the few moments in Demoncore where players see a precise HP
number — and it's earned through coordinated skill, not granted by
the HUD.

### 3. Magic Burst window (~3.0s after detonation)

Players who matched the element get to cast a spell of the same
element during this window. Successful Magic Burst:
- Multiplies the spell damage by 50%
- Refreshes the HP-flash for another 2 seconds (so the party stays
  informed)
- Can EXTEND the chain to Level 2 / 3 if a third weapon skill lands
  during the next window

The Magic Burst window is a real thinking-window. ~3 seconds of
real time is enough for a BLM to read the chain element from the
detonation glow + immediately decide whether to commit MP. Players
get good at this in the first month. Top-end raid groups time
their Magic Bursts so chains stack into Level-3 Light/Darkness for
full-floor damage.

---

## Skillchain damage formula (with weight integration)

```
chain_dmg = sum(participating_weapon_skill_dmg)
            * level_multiplier
            * weight_bonus
            * stationary_bonus

level_multiplier:
  Level 1 chain: 1.25
  Level 2 chain: 1.65
  Level 3 chain: 2.20

weight_bonus:
  Each contributing weapon's weight adds:
    +0.5% per weight point above 5
  So a Curtana (14) WS contributes +4.5% bonus
  A Spharai (32) WS contributes +13.5%
  An Excalibur (18) WS contributes +6.5%

stationary_bonus:
  All contributors stationary during their swing windows:
    +15% bonus
  Otherwise: no bonus
```

Heavy weapons therefore have a real role at the apex — they hit the
chain harder, and the stationary requirement (per
`WEIGHT_PHYSICS.md`) is a strategic test for the party. A
fully-armored DRK + WAR + SAM line standing still for the 2.5
second chain-close window deals devastating damage. A scrambling
party kiting a boss can still chain — they just sacrifice the
+15% stationary bonus.

### Magic Burst formula

```
mb_dmg = base_spell_dmg
         * mb_multiplier
         * caster_int_mod
         * skill_chain_bonus
         * ailment_amplification

mb_multiplier:
  Standard MB: 1.50
  MB during a Level 2 chain: 1.80
  MB during a Level 3 chain: 2.20
  MB while caster is stationary: +15%
  MB during NIN sign-spell follow-up (rare): +25%

skill_chain_bonus:
  Element exact match: 1.00
  Element overlap (e.g. fire MB on Light chain): 0.50
  Element opposition (e.g. ice MB on Liquefaction): -50% damage

ailment_amplification (NEW — see below):
  Ailment-MB: 3.00 effect strength multiplier for 30s
  Damage spell MB: 1.00 (no ailment bonus)
```

The opposition penalty matters. A BLM nuking the wrong element on
a chain doesn't just miss the bonus — they take a damage penalty
for breaking the energy harmonic. **You do NOT cast Blizzard III
on a Liquefaction chain.** New BLMs learn this the hard way. Old
BLMs just *know*.

### Ailment Magic Burst — 3x amplification (the team-strategy core)

When the Magic Burst spell is a **status ailment** (Slow,
Paralyze, Bind, Sleep, Silence, Bio, Dia, Distract, Erase,
Addle, Frazzle, etc), the ailment lands as normal but its
**effect strength multiplies 3x for 30 seconds**:

- Slow: target moves at 1/3 speed instead of 2/3
- Paralyze: proc rate 33% per action -> 99%
- Bind: duration triples
- Sleep: wake-on-damage threshold triples (much harder to wake)
- Silence: interrupt extension triples
- Bio: regen-suppression triples
- Dia: defense-down triples

This is the key to Demoncore boss-team-play. CC mages are now apex
damage. Demoncore bosses are tuned expecting parties to chain CC-
bursts during specific phases. A party that runs only direct-damage
chains will hit soft DPS walls in `wounded` and `grievous` phases.
A party that lands a 3x Slow + 3x Bind + 3x Silence stack at the
right moment will lock the boss for a clean burst window.

Different ailments stack independently. A target can be 3x Slow
+ 3x Bind + 3x Silence simultaneously = total lockdown. Bosses
have **diminishing returns** on stacking ailments — the critic
LLM detects rapid stacking and pre-positions Erase / Status
Resist procs in the next phase.

Ailment-MB does NOT trigger off direct-damage spells. The 3x
multiplier is uniquely the reward for the party that plays
*strategy* not *raw DPS*.

### The defensive twin (see INTERVENTION_MB.md)

The Magic Burst pipeline has a *defensive sibling*: the
**Intervention Magic Burst**. When an enemy closes a skillchain on
a friendly target, the same 3-second MB window opens — and a
healer/buffer/debuffer/song/helix/luopan/enmity spell that lands
inside that window **cancels the incoming damage entirely** and
amplifies the friendly spell at 3x (5x on Light chains).

Successful intervention also **unlocks dual-casting** for that
spell family for 30 seconds (per-job: WHM dual Cures, RDM dual
Enhancing, BLM dual Debuffs, BRD dual Songs, SCH dual Helix, GEO
doubled Luopan radius, Tank tripled enmity spike).

The mechanic is fully symmetric — mob healers can intervention-
cancel the *player party's* chains too. Party play vs. mob-healer
encounters becomes a duet of who reads whose chain element first
and times the intervention better.

See `INTERVENTION_MB.md` for the full spec, per-job breakdowns,
and the complete audible-callout vocabulary.

### The audible layer (see AUDIBLE_CALLOUTS.md)

Skillchain and Magic Burst events do **NOT** appear in the
chatbox. The information is delivered through **voice callouts**
shouted by the players, NPCs, and bosses involved. A WAR opening
a chain shouts "Skillchain open!". The NIN closing it shouts
"Closing — Distortion!". The RDM landing the ailment burst
shouts "Magic Burst — Bio!". A Level-3 Light closure produces a
party-wide "**LIGHT!**" call.

Bosses respond in voice too — Maat audibly reacts when the party
chains him, mood-conditioned tone (mischievous = playful;
furious = gut-punch volume). The chatbox stays silent. Combat
becomes literally audible coordination.

See `AUDIBLE_CALLOUTS.md` for the full callout vocabulary, voice-
production pipeline (Higgs Audio v2 per-character lines), audio
mixer priority lanes, and grunt vocabulary tied to visible-health
stages.

---

## NIN hand-sign substitution

A NIN's elemental ninjutsu (Katon, Hyoton, Suiton, Doton, Huton,
Raiton) can substitute for one weapon skill in a chain — provided
the seal sequence completes inside the 2-second close window.

Mechanics:
- The NIN's ninjutsu impact counts as one chain contributor
- The seal sequence's last seal MUST land within the window
- A NIN signing while sprinting toward the target makes this
  trivial; a stationary NIN obviously also qualifies
- This is the only way for NIN to *substantially* contribute to a
  chain's burst damage; their auto-attack damage is moderate

Practical example: WAR opens with Crescent Moon (compression),
NIN signs Hyoton: Ichi (induration), the chain closes as
**Distortion (water + ice, Level 2)**. Followed by RDM Magic Burst
of Bio III for elemental composition extraction. ~8000 damage in
2.8 real seconds. **This is what high-end Demoncore PUG raids
look like.**

---

## Skillchain visualization in UE5

`BPC_SkillchainVisualizer` is a server-driven component on the
target actor. When a chain closes, the server replicates a
`SkillchainEvent` containing:
```
{
  element: ESkillchainElement,
  level: int (1-3),
  participating_actors: list<AActor*>,
  total_damage: int,
  timestamp: double,
  mb_window_ends_at: double,
}
```

Client renders:
- 0.0-0.5s: contributor weapon skill animations finish
- 0.5-1.0s: element-colored ring expands from target
  (Niagara sphere, color from the AOE_TELEGRAPH palette)
- 1.0-3.5s: persistent element halo on target + HP flash visible to
  party
- 3.5s: halo fades; HP flash ends unless extended by Magic Burst

Magic Burst extension: when a matching-element spell lands during
the halo's lifetime, the halo brightens and pulses for an additional
2 seconds. Stacks across Level-2 / Level-3 progressions.

The element halo is **not** an AOE telegraph (it doesn't damage
the area). It's a flag — "this entity was just hit by [element]
chain". Other casters can chain off it.

---

## Mood event hooks

Adding to `event_deltas.py`:

```
("skillchain_closed_level_3",  "*hero*")     -> ("content", +0.40)
("skillchain_closed_level_3",  "*soldier*")  -> ("content", +0.30)
("magic_burst_landed",         "*hero*")     -> ("content", +0.30)
("magic_burst_failed_element", "*hero*")     -> ("gruff",   +0.20)  # the energy harmonic break
("hit_by_skillchain",          "*civilian*") -> ("fearful", +0.50)
("hit_by_skillchain",          "*"           )-> ("alert",   +0.30)
```

When a player party detonates a Level 3 Light chain in the middle
of Bastok during a PvP scuffle, the bystander civilians visibly
panic, the soldiers go alert, and any other heroes nearby visibly
react with respect. The world *feels* the chain's apex.

---

## What players should learn over time

**Day 1 (new player)**: doesn't see the chain marker; just notices
the white flash. Doesn't connect it to anything strategic.

**Week 1**: notices that follow-up swings sometimes do "way more"
damage and the screen flashes. Starts pattern-matching.

**Week 2**: looks up the skillchain table. Memorizes Level-1 chains.
Practices in a duo with another DD.

**Month 1**: can close a Level-2 chain reliably. Recognizes
incoming chains by the contributor's wind-up stance.

**Month 3**: as a BLM, can match-element-burst a Level-2 chain
within the window, ~80% of the time.

**Month 6**: as a tactician, can plan a Level-3 chain across a
full party with timed weapon skills. Reads the boss's wind-up to
schedule the chain *in between* boss attacks.

**Month 12**: can close Light/Darkness during a moving boss fight.
Does it consistently. Other players watch and learn.

---

## Boss-side: skillchain reading (the critic LLM)

Per `AI_WORLD_DENSITY.md` Tier 4, NMs and bosses get a critic LLM
that watches the encounter every 30 seconds. Skillchain patterns
are explicit input to that critic:

```
boss_critic_input = {
  party_skillchain_history: list[(timestamp, element, level)],
  last_3_magic_bursts: list[element],
  party_dps_estimate: float,
  ...
}

boss_critic_output = {
  next_phase_strategy: str,
  recommended_ws_to_use: str,
  recommended_aoe_to_target: location,
  silence_priority_player: agent_id?,
}
```

A BLM-cheese strategy that worked on day 1 won't work on day 30.
The boss critic will see the BLM's burst pattern, recommend a
Silence-AOE on the next phase, and the BLM player has to adapt.

This is what makes Demoncore boss fights *grow with the
playerbase*. Encounters are alive, not static.

---

## Status

- [x] Design doc (this file)
- [ ] LSB skillchain detection: extend the WS combo table to emit
      `skillchain_closed` events
- [ ] BPC_SkillchainVisualizer (UE5 component)
- [ ] Element halo Niagara templates (8 elements)
- [ ] Magic Burst window timer (server-authoritative)
- [ ] Match-element bonus / opposition-penalty math in damage formula
- [ ] NIN sign-spell substitution rule in skillchain detection
- [ ] Boss critic LLM input pipeline (skillchain history → adaptation)
- [ ] First playtest: WAR + DRK Distortion → BLM Blizzard III MB
