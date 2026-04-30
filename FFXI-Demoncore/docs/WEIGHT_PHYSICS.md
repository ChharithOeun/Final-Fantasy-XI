# WEIGHT_PHYSICS.md

Every piece of equipment has weight. Weight changes how you move,
attack, cast, and survive. A heavily-armored DRK is a tank that
*walks* because the math says so, not because of a hand-tuned slow
multiplier. A naked MNK is a blur because all his weight is muscle,
not steel.

This is the physical-truth pillar of Demoncore combat. It removes a
lot of FFXI's "stat soup" and replaces it with one number every player
can read at a glance.

---

## Why weight (the design rationale)

Original FFXI tied movement speed and cast speed to ability/spell
buffs that the player had to monitor and stack. The math was
opaque, the buffs were invisible after the first cast bar finished,
and the only way to know if you were Hasted was to time your auto-
attacks with a stopwatch.

Weight inverts this. Your weight is a single number visible in your
inventory screen. Equipping a Beach Subligar (weight 2) instead of
Plate Subligar (weight 14) is a 12-point reduction. You see it
immediately. Your character literally moves faster. The math is
legible.

It also makes job identity *physical*. WAR isn't slow because of a
job tag — WAR is slow because plate weighs more than silk. Switch
your WAR to leather-only gear and you're nearly as fast as a THF.
You'll just die faster too.

---

## The weight unit

One **weight point** ≈ 250 grams of real-world equivalent. Why
abstract not literal kilograms? Because spell-weight isn't a
real-world thing, and we want one consistent number for both gear
and "this Drain spell weighs 15 weight-points to cast."

Weight totals scale roughly:
- 0-30 pts: very light (cloth, naked, pyjamas)
- 30-60: light (leather, hides, robes)
- 60-100: medium (chain, scale, thick robes)
- 100-150: heavy (plate, banded mail)
- 150-200: very heavy (full Dynamis-Bastok plate, golem-grade)
- 200+: encumbered, severe penalties

A naked Galkan is around weight 5 (the body itself isn't free, but
Galkan flesh is dense). A naked Tarutaru is weight 1.

---

## Sample equipment weight table

```
Weapons (one-handed sword)
  Bronze Sword         3
  Mythril Sword        5
  Curtana             14   (heavier; more dmg, more accuracy stationary)
  Joyeuse             10
  Excalibur           18

Weapons (two-handed)
  Wooden Staff         3
  Octave Staff        12
  Spharai Greataxe    32
  Aegis Lance         28

Body armor
  Cotton Doublet       4
  Beetle Harness      10
  Mythril Cuirass     22
  Adaman Cuirass      48

Head
  Bronze Cap           2
  Mythril Sallet      11
  Adaman Helmet       28

Misc accessory
  Ear pendant          0   (jewelry is weightless)
  Wedding ring         0
  Gem of the East      0

Spells (effective casting weight, paid once per cast)
  Cure                 4   (basic restoration)
  Cure III            14   (heavier conduit)
  Firaga III          22   (heavy elemental)
  Aspir                6
  Drain               12
  Reraise             36   (the heaviest standard cast)
  Comet               48   (one-shot endgame)
```

A typical DRK in a Mythril Cuirass + Adaman Helmet + Curtana totals
roughly 35-50 base weight. A WHM in robe + ribbon + staff is around
8-15. A NIN in shihakushou + ranger gear is around 12-25.

---

## The five weight-driven formulas

Each formula uses `W` = the character's current weight.

### 1. Movement speed multiplier
```
speed_mult = clamp(1.0 - 0.005 * (W - 30), 0.4, 1.2)
```
Below W=30 you get a small bonus (up to 1.2× at W=0). Above W=30
each additional point shaves 0.5% off your run speed, floored at
0.4× (so even at W=200 you can still walk forward).

A WAR at W=120 moves at 0.55× base speed. He runs about as fast as
a non-warrior strolls. A NIN at W=20 moves at 1.05× — slightly
faster than baseline. A naked Galkan moves at 1.1× — fast for a
big body.

### 2. Attack delay multiplier
```
attack_delay_mult = 1.0 + 0.003 * (weapon_weight - 5)
```
Heavier weapons swing slower. A bronze sword (3) swings at 0.994×
(near-instant). A Spharai (32) at 1.081×. A Curtana (14) at 1.027×.

### 3. Cast speed (Fast Cast formula adjusted)
```
cast_time = base_cast_time
            * (1.0 + 0.004 * (gear_weight - 30))
            * (1.0 - fast_cast_mult)
            * stationary_modifier
            * job_modifier
```
Where:
- `gear_weight` is total equipment weight (NOT spell weight)
- `fast_cast_mult` is the buff stack from gear/job
- `stationary_modifier` = 0.85 if you held still through the cast,
                         1.0 otherwise (cast-while-walking)
- `job_modifier` = 0.85 for SCH, 0.90 for RDM, 0.95 for BRD,
                  1.0 for everyone else

**Instant-cast spells (cast_time = 0) are NOT affected by weight.**
Quick Magic, Mythic Cape Procs, Magic Burst short-circuit cuts, the
Two-Hour Chainspell while Stoneskin is up — all unaffected.

### 4. Accuracy bonus / penalty
```
accuracy_bonus = 0
if you didn't move during the swing's wind-up:
    accuracy_bonus += weapon_weight * 0.5
if target didn't move during your swing wind-up:
    accuracy_bonus += weapon_weight * 0.5
```

Heavy weapons reward patience. A Curtana (14) hitting a stationary
target while you stand still: +14 accuracy. The big damage is
*paid for* by the stillness — you couldn't reposition between
swings.

This makes turtling with greatswords actually viable. A WAR who
plants his feet and hits the boss has a real advantage; a kiting WAR
gives up that advantage on every step.

### 5. Spell interrupt resistance
```
interrupt_chance = base_chance
                   * (1.0 + 0.01 * gear_weight)         # heavier = louder = noticed
                   * job_interrupt_resist
                   * step_multiplier

step_multiplier:
  0 steps during cast        : 1.00
  1 step                     : 1.00   (free for every job)
  walking (RDM/BRD)          : 1.10
  walking (other jobs)       : 1.40
  running (other jobs)       : 1.80
  running (RDM Chainspell)   : 1.10
  any speed (NIN signing)    : 1.00   (no vocal component)

job_interrupt_resist:
  RDM 0.50, BRD 0.55, NIN 0.30, SCH 0.80, BLM 1.00,
  WHM 0.90, SMN 1.00, others 1.00
```

A NIN weaving signs while sprinting takes barely any extra
interrupt risk because hand-signing is kinesthetic, not vocal. A
BLM walking even one step on a Firaga III cast eats the interrupt
math hard — but they get to stand still and nuke for huge damage.

---

## Weight-modifying buffs and debuffs

Spells, songs, and abilities adjust *effective* weight (the W that
the formulas use). The character's literal gear weight doesn't
change, but the math sees a different number.

### Reducers (decrease effective weight)

| Source                          | Effect on W |
| ------------------------------- | ----------- |
| Haste (II, III)                 | -20% / -30% / -40% |
| Mage's Ballad I/II              | -8% / -16%  |
| Mazurka (mounted)               | -25%        |
| Hermes Quencher                 | -10%        |
| Refresh (a side benefit)        | -5%         |
| March I/II/III (BRD)            | -5% / -10% / -15% |
| MNK Mantra                      | -25% (self) |
| THF Flee (60s)                  | -90% (self) |

Stacking is multiplicative. Haste III + March III = 0.6 × 0.85 =
0.51 effective weight multiplier. A WAR at base W=120 with Haste +
March moves at base W=61 — almost like a NIN.

### Increasers (increase effective weight)

| Source                          | Effect on W |
| ------------------------------- | ----------- |
| Gravity                         | +50%        |
| Slow                            | +25%        |
| Slow II                         | +50%        |
| Bind (immobile but free cast)   | +infinite movement; cast unaffected |
| Heavy (Earth-EM proc)           | +35%        |
| Encumber (stack debuff)         | +10% per stack |
| Mounted (without Mazurka)       | +20%        |

Gravity is now the bottom-line slow that the user identified — it
amplifies your existing weight by 50%. A WAR at W=120 with Gravity
runs as if at W=180, which is nearly walking pace. A WHM at W=12
under Gravity is at W=18 — barely affected, since she's already
lightweight. **Gravity hits heavy classes much harder than light
ones, naturally.**

---

## Job-specific weight identities

The weight system creates physical job identity automatically; we
also tune some job traits explicitly.

| Job  | Default weight target | Notes                                                           |
| ---- | --------------------- | --------------------------------------------------------------- |
| WAR  | 80-120 (heavy)        | Bonus dmg/acc per weight point on stationary swings             |
| DRK  | 100-140 (very heavy)  | Same as WAR; absorb skills cost more weight to cast             |
| PLD  | 90-130 (heavy)        | Heavy gear unlocks shield-bash damage scaling                   |
| MNK  | 8-25 (very light)     | Hand-to-hand has no weapon weight; chakra requires <30 W        |
| THF  | 20-40 (light)         | TH/Steal at full effectiveness only when gear < 50 W            |
| RNG  | 30-60 (medium-light)  | Snapshot scales inversely with weight                           |
| RDM  | 25-50 (medium-light)  | Can cast while walking; running with Chainspell                 |
| WHM  | 15-30 (light)         | Light gear → less interrupt; staff weight is a real cost        |
| BLM  | 30-50 (medium)        | Heavy stance lowers cast time penalty for stationary nukes      |
| BRD  | 20-40 (light)         | Sings while walking; weight raises song interrupt chance        |
| SMN  | 25-45 (medium-light)  | Avatar summon cost in weight scales with avatar tier            |
| NIN  | 10-30 (very light)    | Hand signs ignore movement-cost penalty entirely                |
| SAM  | 50-80 (medium-heavy)  | Hassou/Seigan stance grants stationary +30% interrupt resist    |
| DRG  | 60-100 (heavy)        | Wyvern-mounted ignores rider weight for movement only           |
| BLU  | 25-45 (medium-light)  | Spell weight is the cast cost; learning new spells is heavy     |
| COR  | 20-40 (light)         | Quick Draw is instant-cast — bypasses weight entirely           |
| PUP  | 45-80 (medium)        | Automaton gets its own weight column; combined weight matters   |
| DNC  | 18-35 (very light)    | Step-while-casting at running speed (dance is movement)         |
| SCH  | 30-50 (medium)        | Strategos passives: -20% spell weight for currently-active arts |

This table is tuning bait — playtest will change the bands. The
*structure* (each job has a target weight band) is fixed.

---

## Movement-while-casting (the universal rules)

Every job in Demoncore can cast while moving slightly. Specifics:

### One free step (all jobs, all spells)
You can take **one step (~1 meter)** during any cast without
penalty. This means a single emergency reposition (sidestep an
incoming AOE telegraph — see `AOE_TELEGRAPH.md`) doesn't break
your spell.

After the first step, the interrupt formula activates.

### Walking-cast (RDM, BRD)
RDM and BRD can cast at walking speed (50% run) without any
interrupt penalty beyond their job_interrupt_resist multiplier.
This is the canonical "I am the support job" identity.

### Running-cast under Chainspell SP (RDM only)
While Chainspell is active, RDM can cast at full run speed without
interrupt. This makes Chainspell the legitimate "save the wipe"
two-hour ability — RDM kites the entire raid while raising people.

### Sprinting-while-signing (NIN)
NIN's casting is hand signs (see `NIN_HAND_SIGNS.md`). Because
signs are kinesthetic and silent, they ignore the movement-cost
math entirely. NIN can run, sprint, dive, roll while signing.

The only thing that interrupts a NIN's signing is **getting hit**
(damage taken during the sign sequence breaks it). Movement does
not.

### Same rules for mobs/NMs/bosses
NPCs, mobs, NMs, and bosses are subject to the *same* weight and
movement rules. A heavily-armored Quadav Helmsman swings slower
than a Quadav Footsoldier. A Naga (lightly-clad, NIN-aligned)
weaves seal-spells while sprinting at the player.

This is critical for player-readability: when you see an enemy
casting, you can predict what kind of caster it is by how it moves.
A standing-still BLM mob is going to nuke. A hand-signing NIN mob
is going to gap-close. A walking-cast RDM mob is going to debuff
you and reposition. **Visual = predictable.**

---

## Hand signs (NIN special) — see NIN_HAND_SIGNS.md

NIN spells are spelled out by hand seal sequences, visible to all
observers. Each seal is a short held pose; spells require 2-7 seals
in sequence. NIN hands are visible in third-person to the player
and to all spectators.

Reference canon: Naruto hand seal system (Tiger, Boar, Dog, Dragon,
Snake, Bird, Ram, Horse, Monkey, Rabbit, Ox, Rat). FFXI's existing
ninjutsu schools (San, Ni, Ichi suffix tiers) map cleanly onto seal
counts.

The visual is the spectacle. NIN at high level sprints across a
battlefield trailing chakra-flow between hands, weaving Doton: Ichi
in 0.8 seconds while never breaking pursuit.

---

## Strategic implications (what this opens up)

1. **Weight-cycling**. Top-end players bring multiple gear sets to
   a fight: a heavy DPS set for stationary phases, a light
   movement set for kiting phases, a casting-set for emergency
   raises. Switching gear takes a small action delay but the
   tactical depth is enormous.

2. **Encumbered carry**. Bringing too much loot on a long run
   costs movement speed. Players have to decide: leave the
   Quadav Greatshield for the second trip, or drag it home now?
   Donkey-mounts negate this (mount carries the weight, not you).

3. **PvP weight reads**. In outlaw combat, you can /check an
   opponent and see their gear weight bucket. A heavy opponent
   you can outrun. A light opponent you have to commit and burst
   down — they'll escape.

4. **Boss weight phases**. Final-floor bosses shed armor across
   phases (a WAR-type boss ends in light gear at 20% HP, becoming
   a fast attacker). Or the inverse — Maat puts on heavier gear
   in his second wind to grind through the party. Visual cues
   (armor pieces literally falling away or being put on) sell
   this.

5. **No more weight-stat-soup**. Remove Move Speed +12% from
   gear; it doesn't exist. You manage weight directly.

---

## Status

- [x] Design doc (this file)
- [ ] LSB equipment table: add `weight` column to items.sql
- [ ] LSB combat formula: implement the 5 weight formulas
- [ ] LSB buff system: weight modifiers from Haste / Gravity / etc
- [ ] UE5 character ABP: hook movement speed multiplier
- [ ] UE5 character ABP: hook attack delay multiplier
- [ ] Weight readout in inventory UI (one number per equipped slot
      + total)
- [ ] First-pass tuning sweep (DRK W=120 vs MNK W=20)
- [ ] Hand-sign animation library (see NIN_HAND_SIGNS.md)
- [ ] Cross-link with `COMBAT_TEMPO.md` and `AOE_TELEGRAPH.md`
