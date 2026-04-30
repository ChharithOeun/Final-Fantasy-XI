# NIN_HAND_SIGNS.md

Ninja casting in Demoncore is *visible* and *kinetic*. NIN doesn't
chant — they form hand seals in sequence, chakra-flow visible
between fingers, while moving at full sprint. Other observers can
tell which spell is coming by reading the seal sequence (high-level
players will memorize them).

The reference is the canonical Naruto twelve-zodiac hand-seal system
(Tiger, Boar, Dog, Dragon, Snake, Bird, Ram, Horse, Monkey, Rabbit,
Ox, Rat). FFXI's own Ninjutsu spell tiers (Ichi / Ni / San suffixes)
map onto seal counts cleanly.

---

## The twelve seals

| Seal     | Japanese | Mnemonic shape                          | Element bias  |
| -------- | -------- | --------------------------------------- | ------------- |
| Tiger    | Tora     | both hands up, index+middle vertical    | fire / kai    |
| Boar     | I        | hands fist-pressed, thumbs out          | earth         |
| Dog      | Inu      | left fist closed, right palm covers     | water         |
| Dragon   | Tatsu    | right hand on left, fingers interlaced  | wind / spec   |
| Snake    | Mi       | hands palm-pressed, fingers interlaced  | earth         |
| Bird     | Tori     | hands palm-pressed, thumbs interlocked  | wind          |
| Ram      | Hitsuji  | hands palm-pressed, fingers wiggling    | balance       |
| Horse    | Uma      | left fist + right palm, slight hinge    | fire          |
| Monkey   | Saru     | left fingers crossed over right thumb   | metal / ice   |
| Rabbit   | U        | both hands fingers up, index extended   | wind / agility|
| Ox       | Ushi     | right hand cupped over left fist        | thunder       |
| Rat      | Ne       | both hands fingers wiggling, palm-down  | utility       |

Each seal is a held pose (~0.15s at base speed). Sequences for
spells run 2-7 seals.

This vocabulary is freely available across martial-arts and anime
canon; we authored our own seal animations from reference, no IP
issues.

---

## Spell → seal-sequence mapping

Every Ninjutsu spell is authored with a sequence. Examples:

| Ninjutsu                | Seals                                          |
| ----------------------- | ---------------------------------------------- |
| Utsusemi: Ichi          | Tiger → Boar                                   |
| Utsusemi: Ni            | Tiger → Boar → Snake                           |
| Utsusemi: San           | Tiger → Boar → Snake → Ram                     |
| Katon: Ichi             | Snake → Tiger                                  |
| Katon: Ni               | Snake → Tiger → Horse                          |
| Katon: San              | Snake → Tiger → Horse → Monkey → Tiger         |
| Hyoton: Ichi            | Bird → Snake → Ram → Boar → Ox → Tiger         |
| Doton: Ichi             | Boar → Dragon → Rabbit                         |
| Suiton: Ichi            | Dog → Boar                                     |
| Huton: Ichi             | Bird → Dog                                     |
| Raiton: Ichi            | Ox → Rabbit → Monkey                           |
| Tonko: Ni (escape)      | Tiger → Snake → Rat                            |
| Aisha (debuff stack)    | Snake → Boar → Tiger                           |

These are designer-authored, balanced for combat tempo:
- Ichi-tier: 2-3 seals (~0.45s)
- Ni-tier: 3-4 seals (~0.6s)
- San-tier: 4-7 seals (~0.9-1.1s)

NIN's job_modifier in `WEIGHT_PHYSICS.md` (interrupt resist 0.30) is
already built around the assumption that the visible seal sequence
*itself* is the main interrupt window — not movement.

---

## Visual production

### Animation
Each seal is a 5-frame held pose authored on the NIN base skeleton.
Sequences blend additively onto the locomotion layer — so a NIN
running, sprinting, or rolling can layer the seal animation onto
their hands without breaking the lower-body sprint.

UE5 anim graph slot: `NinSignSlot`. The seal animator pushes the
held pose onto this slot for the duration of that seal in the
sequence; other slots (locomotion, attack) play freely on the rest
of the body.

### Chakra-flow VFX
A persistent Niagara emitter binds to the NIN's two hand sockets
(`Hand_L_Socket`, `Hand_R_Socket`). On seal-sequence start, the
emitter spins up:
- Faint blue chakra-light wrapping each hand
- Thin chakra-line tracing between hands (especially at seals where
  hands touch)
- Brightness ramps with each completed seal in the sequence —
  mid-sequence the NIN is visibly glowing
- On final seal, a bright burst as the spell completes

The element of the spell tints the chakra:
- Katon (fire): red-orange shift in the last 30%
- Hyoton (ice): cyan shift
- Raiton (lightning): yellow flicker
- Suiton (water): deep blue
- Doton (earth): brown-amber
- Huton (wind): pale green
- Tonko (escape): silver-flash

### Audio
Each seal has a short woody/papery click (the hand pose locking).
The full sequence builds an audible rhythm; experienced players
recognize spells by sound alone in chaotic fights.

The final seal cuts to the spell's release sound (Katon explosion,
Hyoton crystalline shatter, etc).

---

## Visible reading — why this matters

A NIN who's about to Katon: San runs through a 5-seal sequence.
Every player in line of sight can see:
- The first seal (Snake) — could be water-school, earth-school,
  or fire-school
- Second seal (Tiger) — narrows to fire-school
- Third seal (Horse) — confirmed Katon family
- Fourth seal (Monkey) — confirmed Katon: Ni or higher
- Fifth seal (Tiger) — confirmed Katon: San (highest fire)

A skilled player moves out of fire-cone the moment they see the
third seal. A novice sees a generic "ninja casting something" and
eats the AOE.

This is the same observability principle as the visual health
system. The information is there, displayed physically on the
character's body, and players who learn to read it gain real
combat advantage.

---

## NIN-specific weight rules (already in WEIGHT_PHYSICS.md)

- NIN's `job_interrupt_resist` is **0.30** — they *only* interrupt
  on direct damage during the seal sequence
- NIN's movement has no penalty on seal speed: walking, running,
  sprinting, rolling, jumping all have step_multiplier 1.00
- NIN's seal sequence pauses if interrupted; resumes from the
  same seal index if combat clears within 1.5s
- Damage taken during seal sequence: each instance has a fixed
  10% chance to break the sequence, regardless of damage
  magnitude (encourages NIN to *position* away from threats while
  signing, even if they can't *stop* moving)

---

## Mob NIN identity

Mobs and NMs that follow a NIN archetype use the same hand-sign
visuals. This is a cornerstone of the visible-AI principle:

- Naga (NIN-aligned) sprint at the player while signing
- Tonberry NMs occasionally form Boar → Dragon → Rabbit (Doton)
  to root the player to the floor
- Specialist Quadav scouts use Suiton: Ichi to escape — players
  who recognize the Dog → Boar sequence can pre-position to
  intercept

Same mechanics, same visuals, same readability rule.

---

## Status

- [x] Design doc (this file)
- [ ] Twelve seal pose animations (one per zodiac, hands only,
      blended onto NIN locomotion via NinSignSlot)
- [ ] Niagara hand-flow emitter with elemental tint parameters
- [ ] Audio: seal-click SFX library
- [ ] Spell → seal-sequence data file
      (`data/ninjutsu_sign_sequences.json`)
- [ ] LSB Ninjutsu cast logic: pause on damage, resume window
- [ ] Mob NIN archetype animation set hooked to RL-policy classes
- [ ] First playtest pass on Naga / Tonberry NM encounters
