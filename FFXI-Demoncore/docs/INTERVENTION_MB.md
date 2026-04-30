# INTERVENTION_MB.md

The most lethal moment in a Demoncore fight is the enemy
skillchain. A boss-grade NIN closes Distortion on your tank, the
enemy BLM is winding up Blizzard IV in the burst window — that's
~8000 damage incoming on a 5500-HP tank. It's a wipe.

**Unless** your WHM read the chain element, started Cure IV at the
right moment, and lands the cast inside the enemy's MB window. In
which case the tank takes ZERO damage — and gets healed at 3x with
a 30-second Regen. Plus your WHM unlocks dual-casting Cures for
the next 30 seconds.

This is the **Intervention Magic Burst** — the heroic save
mechanic that makes healers, buffers, debuffers, tanks, and bards
each have their own version. The same mechanic also runs in
reverse: a mob WHM can intervention-cure a boss when your party
chains it. **The world plays both sides of this game.**

This doc is the contract for the mechanic. Reads as an extension
of `SKILLCHAIN_SYSTEM.md` — the offensive Magic Burst is one
system, the Intervention MB is its dual.

---

## The intervention window (timing)

After an enemy closes a skillchain on a friendly target:
1. **Element halo** appears on the target (the same Niagara halo
   from `SKILLCHAIN_SYSTEM.md`)
2. **3-second Magic Burst window** opens — same as offensive
3. The target is about to take massive damage from the enemy's MB
4. Your healer/buffer/debuffer can cast a friendly spell, **and
   if it lands inside the 3-second window**, the spell counts as
   an Intervention Magic Burst

The intervention is *time-critical*. The friendly cast must
**LAND** (not start) during the 3-second window. That means:
- For a Cure I (1.5s cast): plenty of buffer; can start anytime
- For a Cure IV (3.5s cast): must start at the moment of chain
  detonation
- For a Cure V (5s cast): must have started *before* the chain
  closed — requires reading the chain coming together

This is why **Quick Magic, NIN/WHM sub-cast, Fast-Cast gear, and
Stoneskin-Quick-Magic cooldown rotation** all become apex
priorities for endgame healers.

---

## Intervention amplification (the rewards)

| Friendly spell type | If lands in window         | If chain element matches Light          |
| ------------------- | -------------------------- | ----------------------------------------- |
| Cure I-V (heal)     | **3x heal + Regen 30s**    | **5x heal + Regen V 30s**                 |
| Curaga (AoE heal)   | **3x heal all + Regen 30s**| **5x heal all + Regen V 30s + party cleanse** |
| -na spells (status) | Remove debuff + 30s immunity to that ailment | 60s immunity + party-wide cleanse of that ailment |
| Erase (single)      | Remove + 30s erase-immunity| 60s + party-wide Erase                    |
| RDM enhancing       | 3x duration + 50% potency  | 5x duration + Light element shield        |
| BLM debuffing       | 3x debuff potency          | 5x debuff + party gets element-link bonus |
| BRD single-target song | 3x duration + double effect | 5x duration + spreads to nearby party  |
| SCH Helix DoT       | 3x ticks for 30s           | 5x ticks + element conversion proc        |
| GEO Indi/Luopan     | 2x luopan radius           | 3x radius + element vortex visual         |
| Tank Flash/Provoke  | 3x enmity spike for 30s    | 5x enmity + +reduced damage taken 30s     |

Cure 1's lower base value but faster cast time + equal 3x
multiplier means Cure I intervention is **always feasible**;
Cure V intervention is the apex hard-mode play that requires
prediction, not reaction.

The Light-element bonus tier (the right column) is the apex of the
apex. A WHM landing Cure V on a Light skillchain heals 5x AND
immunes the entire party. Once or twice per long encounter, max.

---

## The dual-casting unlock (per-job specialization)

Successful Intervention MB unlocks **dual-casting** for spells of
that family for 30 seconds. Dual-casting means **two separate cast
timers running simultaneously** — the caster can fire two spells
back-to-back, or one of each kind in parallel.

This is the per-job depth differentiator. Each healer/support job
unlocks a different dual-cast family:

### WHM — Cure dual-cast
After Cure intervention, WHM can cast **two Cure spells (any tier
I-V) simultaneously** for 30 seconds. So Cure IV on tank + Cure
III on DPS at the same time. Major HPS spike during the most
critical phases.

### RDM — Enhancing dual-cast
After Enhancing intervention (Haste, Refresh, Phalanx, Stoneskin,
Blink, Aquaveil etc), RDM can cast **two enhancing spells in
parallel** for 30 seconds. Refresh on the BLM + Haste on the WAR
at once. RDM's identity as "support that doesn't fall behind" is
realized.

### BLM — Debuffing dual-cast
After debuff intervention (Slow, Paralyze, Bind, Distract,
Frazzle, Addle, Bio, Dia — non-direct-damage spells only), BLM can
cast **two debuffs simultaneously** for 30 seconds. Stack
debuffs at double speed. The 3x amplification also applies to
each debuff individually.

Canonical FFXI debuff-slot rules apply: **Bio and Dia are
mutually exclusive** (same elemental-DoT slot — applying one
overwrites the other). Same for **Slow and Slow II** (same
slot). Dual-cast pairs that stack legitimately:
- Slow + Paralyze (different slots)
- Slow + Bind (different slots)
- Slow + Bio (different slots)
- Bio + Distract (different slots)
- Frazzle + Addle (different slots)

The canonical FFXI debuff-slot map remains intact in Demoncore.
Dual-cast just lets BLM apply both halves of a multi-slot debuff
spread in 1.5 seconds instead of 3.

### BRD — Single-target song dual-cast
BRD's intervention works on **single-target songs only**
(canonical BRD songs are AOE; Demoncore introduces single-target
song variants for this purpose). After intervention, BRD can have
**two single-target songs active per party member** instead of
the canonical limit, AND can dual-cast new songs for 30 seconds.
BRD becomes a per-character buff orchestrator.

### SCH — Helix dual-cast
After Helix intervention, SCH can cast **two Helix spells
simultaneously** for 30 seconds. Two Helix DoTs ticking on the
same target → ~4x DoT pressure during the window.

### GEO — Luopan radius doubling
GEO's intervention is unique. Instead of dual-casting, **the GEO's
active luopan/Indi spell doubles its AoE radius** for 30 seconds
(or 3x if Light-bonus). A party that's spread across the room can
all be inside Indi-Refresh again. Strategic positioning becomes
trivially easy during the window.

### Tank — Enmity spike (PLD/NIN/RUN)
Tanks have intervention via **Flash, Provoke, Foil, Atonement, or
Lunge**. Successful intervention spikes their enmity 3x for 30
seconds (5x if Light-bonus). This means the tank can hold the
boss's aggro through almost any threat for the next 30s — letting
the rest of the party safely DPS without pulling.

### What's not unlocked
Direct-damage spells (Fire, Blizzard etc) do NOT have an
intervention path — those use the offensive Magic Burst pipeline.
Direct-damage MB stays as a +50%/+80%/+120% multiplier per
`SKILLCHAIN_SYSTEM.md`. The intervention path is exclusively for
healing, support, debuff, song, helix, geomancy, and
enmity-spike spells.

---

## Mob-symmetry (the world plays both sides)

Same rules apply to mobs, NMs, and bosses — they can intervention-
cure their friendlies AGAINST player skillchains.

When the player party chains a Quadav Helmsman:
1. Player WAR opens chain on Quadav Helmsman → "Skillchain open!"
2. Player NIN closes Distortion on Quadav Helmsman → "Distortion!"
3. **Adjacent mob Quadav Healer** sees the chain element halo,
   begins casting Cure IV on the Helmsman
4. If the Quadav Healer's Cure IV lands in the window:
   - Quadav Helmsman takes 0 damage from the chain
   - Quadav Helmsman gets 3x Cure + 30s Regen
   - Quadav Healer audibly shouts: "[mob voice] Cure burst!"
   - Quadav Healer unlocks dual-cast Cure for 30s — much more
     dangerous threat now
5. Player party has just had their chain *intercepted*. They
   need to silence/Bind/kill the Quadav Healer before doing it
   again.

This makes mob healers **legitimate threat actors** that the
party must prioritize. A 4-mob group with a healer is harder than
a 6-mob group without. Players learn to read mob roles by their
animations and voice cues.

For the boss critic LLM: when a boss has off-screen healer mobs
(rare, but high-end raids include this), the critic specifically
times intervention attempts for the highest-impact phases — i.e.
when the boss is at `wounded` and the player chain is about to
push him to `grievous`.

---

## Audible callouts (extending AUDIBLE_CALLOUTS.md)

Players, NPCs, and mobs all vocalize intervention events:

| Event                                          | Callout (player WHM)                  |
| ---------------------------------------------- | -------------------------------------- |
| Cure intervention lands                        | "Magic Burst — Cure!"                  |
| Cure intervention on Light chain (5x bonus)    | "**MAGIC BURST — CURE V!**"            |
| Curaga intervention                            | "Magic Burst — Curaga!"                |
| -na intervention (e.g. Paralyna)               | "Magic Burst — Paralyna!"              |
| Erase intervention                             | "Magic Burst — Erase!"                 |
| Failed intervention (cast started, didn't land in window) | *grunt of frustration*       |

For other jobs:
- RDM: "Magic Burst — Haste!" / "Magic Burst — Refresh!"
- BLM: "Magic Burst — Bio!" / "Magic Burst — Slow!"
- BRD: "Magic Burst — Mage's Ballad!" / song-element-specific
- SCH: "Magic Burst — Firestorm Helix!" / element-specific
- GEO: "Magic Burst — Indi-Refresh!" / "LUOPAN BURST!"
- Tank: "PROVOKE BURST!" / "FLASH BURST!"

For mobs: per-mob-class voice line. A Quadav Healer shouts
"[gruff Quadav speech] Cure burst!" in their canonical mob voice.

When dual-casting unlocks, the caster's UI shows a small visual
cue (a glowing tier-V indicator next to the cast bar). No
chatbox text. The audible cue is the rest of the party's only
indication that "the WHM is now in dual-cure mode for 30s — coordinate
your attacks accordingly."

---

## Damage formula (intervention path)

```
intervention_dmg_cancellation:
  if friendly_intervention_spell_lands_in_window:
    enemy_mb_damage *= 0.0   # cancelled entirely
    fire_intervention_event()

intervention_effect_amplification:
  base_effect = spell.base_effect
  amplification = 3.0
  if chain_element == "Light":
    amplification = 5.0
  spell.applied_effect = base_effect * amplification

intervention_regen_or_immunity:
  if spell_family in (cure, curaga):
    apply_status(target, "Regen V", duration=30s)
    if light_bonus:
      apply_status(target, "Regen V", duration=30s)
  elif spell_family in (na_spell, erase):
    apply_status(target, "Immunity_to_X", duration=30s)
    if light_bonus:
      apply_status(target, "Immunity_to_X", duration=60s)
      cleanse_party(X)

dual_cast_unlock:
  caster.add_buff("DualCast_Family_X", duration=30s)
  # implementation: caster has 2 cast slots in parallel for 30s
```

The damage cancellation is the heart of it. **An incoming 8000-
damage enemy MB is reduced to 0 if the friendly intervention
lands in time.** This is the save-the-wipe moment.

---

## Why this design (rationale)

The original FFXI had healers in a defensive role — react to
incoming damage, top off HP, stay alive. It was effective but not
particularly *heroic*. Damage came, damage got healed, no
narrative beat.

Demoncore's intervention mechanic creates a different kind of
heroic moment. The most lethal moment of the encounter — enemy
chain incoming, party tank about to die — is **inverted into the
most rewarding moment** if the healer can read the chain and time
the spell correctly.

This also creates per-job character. WHM is "the wall that
catches the chain". RDM is "the orchestrator who buffs at double
speed". BLM is "the debuffer who locks the boss in two stacks at
once". BRD is "the conductor who makes each party member their
own buffed character". SCH is "the DoT specialist who doubles up".
GEO is "the area controller who covers the party". Tanks are "the
shield that holds the boss". **Each job has a different heroic
beat in the same shared mechanic.**

And it works for mobs, so encounters become a duet of
intervention attempts. A boss-grade encounter has both sides
trying to read each other's chains and intervene. The fight feels
like jazz — improvisational, listening, responding.

---

## Mood event hooks (additions to event_deltas.py)

```
("intervention_mb_succeeded",       "*hero*")    -> ("content",  +0.50)
("intervention_mb_succeeded_light", "*hero*")    -> ("content",  +0.70)
("intervention_mb_failed",          "*hero*")    -> ("furious",  +0.30)
("dual_cast_unlocked",              "*hero*")    -> ("content",  +0.30)
("dual_cast_active",                "*hero*")    -> ("alert",    +0.10)
("party_member_saved_by_intervention", "*civilian*") -> ("content", +0.40)
("party_member_saved_by_intervention", "*hero*")     -> ("content", +0.30)
("enemy_intervention_blocked_our_chain", "*hero*")    -> ("furious", +0.40)
```

A WHM who saves the tank with an Intervention Cure V on Light is
a celebrated player — bystander civilians visibly cheer
("content +0.4"); other heroes' moods spike in respect. The world
**recognizes** the play.

A party that gets their chain intervention-blocked by a mob healer
gets `furious` — the right player-emotion for "we set up the
perfect chain and got cock-blocked".

---

## Implementation outline (UE5 + LSB)

### LSB combat code
- New event: `enemy_chain_window_open` fires when an enemy chain
  closes on a friendly target. Carries `{element, expires_at,
  predicted_mb_damage}`.
- New event: `friendly_spell_lands_in_window` fires when a
  player/mob spell lands during a `enemy_chain_window_open`.
  Triggers the intervention path.
- Damage formula extension: cancel damage if intervention lands;
  apply 3x/5x amplification + regen/immunity.
- Buff system: `DualCast_Cure`, `DualCast_Enhance`,
  `DualCast_Debuff`, `DualCast_Song`, `DualCast_Helix`,
  `LuopanRadius_Doubled` — each is a 30-second buff that the
  caster's spellcaster reads to enable parallel cast slots.

### UE5 client
- Element halo color is already replicated per `SKILLCHAIN_SYSTEM.md`
- Intervention cancellation: when the server pushes
  `intervention_succeeded`, the client cancels the predicted
  damage VFX (no big damage number, no impact mesh)
- Intervention success VFX: a friendly-element burst on the target
  (gold-light shimmer for cures, silver-rune for buffs, deep-purple
  for debuff bursts)
- Dual-cast UI: the caster's cast bar splits into two parallel bars
  for 30s (a clear visual cue that they have two cast slots)

### Audible
- `AUDIBLE_CALLOUTS.md` library extended with the 6+ intervention
  callouts per job
- Mob class voice library extended with their intervention barks

### Tier-3 boss critic LLM
- Critic now considers intervention timing in its strategy. If
  the boss has a healer add, the critic schedules intervention
  attempts. If the boss is alone, it tries to disrupt the
  player's intervention chain (silence the WHM, AOE the
  back-row casters).

---

## What this enables

A typical 6-player Maat fight, late phase:
- T+0.0 Maat (wounded) winds up Final Heaven (5s arena cast)
- T+0.5 Player WAR shouts "Skillchain open!" (Crescent Moon)
- T+1.5 Player NIN signs Hyoton: Ichi closes Distortion
- T+1.7 Element halo on Maat — friendly chain
- T+2.0 Player BLM Magic Bursts Slow II → "Magic Burst — Slow!"
        Maat 3x slowed for 30s. Final Heaven cast time stretches
        from 5s to 15s. Plenty of time.
- T+2.5 Player WHM intervention-cures the tank just in time
        because Maat had also opened a counter-chain.
        Tank lives at 25% HP instead of dying.
- T+5.0 Maat (still casting Final Heaven, slowed)
        Player BRD and RDM stack 3x debuffs.
- T+8.0 Maat hits 0% during his own Final Heaven cast
- Defeat cinematic plays. Maat: "...you've earned this."

That's a 8-second sequence with **5 distinct intervention/MB
events**, no chatbox text, all driven by audible callouts and
visible cues. **This is what Demoncore endgame combat sounds
and feels like.**

---

## Status

- [x] Design doc (this file)
- [ ] LSB damage broker: enemy_chain_window_open event + intervention detection
- [ ] LSB combat formula: cancellation + 3x/5x amplification + regen/immunity
- [ ] LSB buff system: 6 dual_cast buffs + luopan_radius_doubled
- [ ] UE5 client: intervention success VFX (per spell family)
- [ ] UE5 client: dual-cast UI (parallel cast bars)
- [ ] Audible callout library: per-job intervention lines
- [ ] Mob healer class voice library
- [ ] Tier-3 critic LLM: intervention strategy prompts
- [ ] First playtest: WHM Cure IV intervention on Maat's Final Heaven cast
- [ ] Mob-side test: Quadav Healer intervention on player chain
