# MOB_RESISTANCES.md

Every mob/NM/boss has visible elemental affinity. Players read it
through fur color, equipment color, breath effect, mood-glow, and
voice. They learn the bestiary the same way they learn the
visual-health language: by looking, listening, and dying twice to
the same tell.

This is the missing depth that ties together skillchain element
choice + intervention timing + the 3x ailment amplification.
**Picking the right element matters more than picking the
biggest spell.**

---

## The element wheel (canonical FFXI)

```
        Light
       /     \
   Earth      Lightning
    |    ╳        |
   Wind         Water
       \     /
        Dark
        Fire   (Fire <-> Ice opposition)
        Ice
```

Each element has:
- One **strong-against** opposite (deals +25% damage; weakened
  resistance)
- One **weak-against** opposite (deals -25% damage; resisted)
- Two **neutral** elements (no modifier)

Skillchain elements use these same rules. A Liquefaction (fire)
chain on a fire-aligned boss does **less** damage; on an ice-
aligned mob does **more**.

---

## Per-mob-class affinities (sample)

| Mob class             | Aligned element  | Weak to     | Strong vs    |
| --------------------- | ---------------- | ----------- | ------------ |
| Quadav (lightning)    | lightning        | water       | wind         |
| Yagudo (water)        | water            | lightning   | fire         |
| Orc (fire)            | fire             | ice         | wind         |
| Goblin (earth)        | earth            | wind        | lightning    |
| Tonberry (dark)       | dark             | light       | (no penalty) |
| Naga (water)          | water            | lightning   | fire         |
| Bee (wind)            | wind             | earth       | water        |
| Slime (variable)      | rotates by zone  | rotating    | rotating     |
| Skeleton (dark)       | dark             | light       | none         |
| Sahagin (water)       | water            | lightning   | fire         |
| Bug (earth)           | earth            | wind        | water        |
| Demon NM (dark)       | dark             | light       | (resists all)|
| Dragon NM (variable)  | per-individual   | varies      | varies       |

Boss-grade NMs and final-floor bosses often have **shifting
affinities per phase** — the boss critic LLM scripts these so the
party has to re-read the affinity each time the boss transitions.

---

## Visible affinity cues

A skilled player reads mob affinity from sight + sound:

| Cue                          | Reads as               |
| ---------------------------- | ---------------------- |
| Reddish glow on attack       | fire-aligned           |
| Cyan steam-breath            | ice-aligned            |
| Yellow crackle around limbs  | lightning-aligned      |
| Earthen-brown dust trail     | earth-aligned          |
| Pale-green leaf swirl        | wind-aligned           |
| Deep-blue water droplets     | water-aligned          |
| White-gold radiance          | light-aligned          |
| Desaturated purple aura      | dark-aligned           |

These cues are subtle in `pristine` stage but **brighten** as the
mob gets damaged (per `VISUAL_HEALTH_SYSTEM.md`) — the affinity
becomes more legible the more the mob is hurt. So new players
can read affinity once the mob hits `bloodied`. Veterans read it
on first sighting.

---

## Skillchain × affinity damage interaction

```
chain_dmg_final = chain_dmg_base
                * affinity_multiplier
                * stationary_bonus

affinity_multiplier:
  weak-to:        1.25
  neutral:        1.00
  strong-against: 0.75
  matching:       0.50  (a fire chain on a fire-aligned mob is half-damage)
```

This is why picking the right chain element MATTERS. A fire chain
on an Orc (fire-aligned, strong-vs-fire) does only 50% damage. A
water chain on the same Orc does 125%. **The party that reads
the affinity and chains accordingly does 2.5x the damage of a
party that doesn't.**

The audible callout becomes a strategic broadcast: when the WAR
shouts "Skillchain open — Compression!" the party knows the chain
will end up dark-element. If the boss is light-aligned, the
party redirects mid-chain.

---

## Ailment-MB × affinity stacking

The 3x ailment amplification (per `SKILLCHAIN_SYSTEM.md`) is
multiplied by the affinity bonus. So a 3x Slow on a wind-weak
target during an Earth-element chain is **3.75x** Slow effective
strength. This is the apex CC pressure — boss is locked at
~14% normal speed for 30s.

---

## Boss critic LLM and affinity hiding

Boss-grade encounters use the critic LLM (per `BOSS_GRAMMAR.md`)
to *occasionally hide* affinity tells. A boss might suppress
their affinity glow during pristine phase, only revealing it
once they hit `bloodied`. This forces players to commit to a
chain element before they fully know the affinity — a real test
of risk-taking.

Some bosses also **shift** affinity mid-fight. Maat is famous
for this: he opens dark-aligned, shifts to light at wounded
(reflecting his MNK chi-flow), and can flip to elemental-neutral
during Hundred Fists (denying the party the 3x bonus).

---

## Status

- [x] Design doc (this file)
- [ ] LSB items.sql add `aligned_element` + `weak_to` columns to mob_pool
- [ ] LSB damage formula extension: affinity_multiplier
- [ ] UE5 mob materials: per-element glow shaders (8 elements)
- [ ] Niagara "affinity glow" emitter library (one per element)
- [ ] Critic LLM prompt extension: affinity-hiding strategies for hero bosses
- [ ] Per-mob-class affinity table (~80 entries)
- [ ] First playtest: Quadav vs water-chain — confirm 1.25x on the books
