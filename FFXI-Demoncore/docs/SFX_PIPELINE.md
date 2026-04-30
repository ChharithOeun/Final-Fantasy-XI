# SFX_PIPELINE.md

How Demoncore renders the entire battlefield in HD surround sound
without losing the canonical "this sounds like FFXI" quality.

The key constraint, per user direction: **spell and ability sounds
stay canonical**. The original FFXI sound design — the swoosh of a
Fire spell, the chime of Cure, the metallic whoosh of a weapon
skill, the boss roar of an NM — is part of the brand. We **don't
replace** these. We HD-upscale them and 7.1-position them, but the
samples themselves remain the canonical sounds the player remembers.

For everything else — battle chatter, environmental ambience,
new mechanic sounds (hand-sign chakra flow, intervention MB
shimmer, dual-cast bell, phase-transition armor-drop) — we either
remaster the canonical equivalent or author original assets.

This is a sister doc to:
- `MUSIC_REMIX_PIPELINE.md` (same retail-extraction pattern, but
  music can be remixed; SFX cannot be substantially altered)
- `AUDIBLE_CALLOUTS.md` (voice callouts; this doc covers
  non-voice SFX)
- `VOICE_PIPELINE.md` (Higgs Audio v2 for NPC voices)

Visual effects synced to these sounds are **post-production**
per user direction — covered in a future doc.

---

## The four SFX classes

### Class 1 — Canonical-Preserved (HD upscale only)

Sounds the player has 22-year muscle memory for. We touch them
*minimally*. The upgrade is sample rate, bit depth, and surround
positioning — but not timbre, not envelope, not character.

- All spell cast/release sounds (Fire, Cure, Banish, Drain, etc)
- All weapon skill audio (Crescent Moon swoosh, Asuran Fists thuds,
  Hexa Strike, all 200+ canonical WS impacts)
- Item use sounds (potion glug, ether tinkle, food crinkle)
- Menu / UI clicks (the iconic FFXI tab-flip)
- Boss-specific signature audio (Maat's "Hmph", Shadow Lord's
  laugh, Promathia's chant — these are recognizable from sound
  alone)

Process: extract from retail DATs → AudioSR super-resolution to
48kHz → light tonal balance EQ (-3dB at 6kHz hump that 22kHz
sources tend to have) → re-master for 7.1 spatialization at
runtime. **No timbre changes.** No re-synthesis.

### Class 2 — Canonical-Remastered (HD + tone shaping)

Battle backgrounds, environmental loops, and crowd ambience.
The originals were thinned by 22kHz/16-bit limits. We can
substantively improve the audio quality without changing the
"feel" of the source.

- Sword-on-shield clang loops
- Fire crackle, water splash, footsteps on stone/wood/grass
- Crowd chatter ambient beds (Bastok marketplace background,
  Jeuno Rolanberry Fields traders bustle)
- Beastman raid alarm bells, Bastok forge hammering, Windurst
  Tower wind chimes
- Combat impact "hits" (sword hitting flesh, spell impact thud)

Process: same as Class 1 + an additional **tonal enhancement
pass** that fills out the bass register and adds high-frequency
shimmer. Maybe 5-10% audible difference vs original — enough
that the game sounds modern, not enough that veterans say
"that's wrong."

### Class 3 — New Mechanic Sounds (custom-authored)

Sounds for Demoncore mechanics that didn't exist in retail FFXI:

- **NIN hand-sign chakra flow** (per `NIN_HAND_SIGNS.md`):
  blue-light ambient hum that ramps in brightness with each
  completed seal in the sequence
- **Skillchain element halo expansion** (per `SKILLCHAIN_SYSTEM.md`):
  per-element resonance — Fusion bright brass flare, Distortion
  underwater rumble, Light vocal chorus, Darkness sub-bass drop
- **Intervention MB shimmer** (per `INTERVENTION_MB.md`):
  golden harp + bell when a Cure intervention saves the tank;
  silver-rune for buff intervention; deep-purple rumble for
  debuff burst
- **Dual-cast unlocked bell** (per `INTERVENTION_MB.md` Layer):
  small chime when 30s dual-cast becomes active; subtle but
  catchable
- **Visible-health stage transitions** (per `VISUAL_HEALTH_SYSTEM.md`):
  per-archetype hurt cries (galkan grunts, taru high-pitched
  yelps, mithra ear-flick rustle, elvaan controlled exhale)
- **Healing structure heal-stitch** (per `DAMAGE_PHYSICS_HEALING.md`):
  reverse-particles audio cue per material (sap shimmer for
  wood; mineral chime for stone; weld glow for metal)
- **Equipment wear breakage** (per `EQUIPMENT_WEAR.md`):
  graduated breakage cues per stage (creak at scuffed; crack at
  damaged; metallic snap at broken; full shatter at unusable)
- **Master synthesis crit-repair proc** (per `CRAFTING_SYSTEM.md`):
  golden particle SFX layered on the satisfied crafter shout
- **Audible callout grunts** for races we don't have voice
  cloning samples for yet

These are all designer-authored. ~80-100 new SFX assets total
across the entire game design surface. Doable in 2-3 weeks of
focused sound design work.

### Class 4 — Procedural Variation

Some sounds need infinite variation to avoid the repetition
fatigue that plagued retail FFXI's longer farm sessions:

- **Footstep variations**: 8 takes per (race × surface) =
  ~40 surface-types × 6 races × 8 takes = ~1900 footstep
  files. Dynamically selected at runtime.
- **Combat hit variations**: 5-8 takes per (weapon-class ×
  armor-type) so consecutive sword swings on plate sound
  different.
- **Mob roar variations**: 4-6 takes per mob_class so a pack
  of 3 Quadav don't all roar identically.

Procedural variation is sample-library work, not synthesis.
~4000 samples total for full coverage.

---

## Surround sound positioning (UE5 runtime)

UE5's native **Audio MetaSounds** + **Quad Panning** + the
**5.1/7.1 surround output** handle the positioning at runtime.
The pipeline produces stereo-or-mono source files with metadata
flags for spatializer behavior:

```yaml
# example metadata per SFX asset
swoosh_sword_curtana_mythril:
  source_format: stereo_48khz_24bit
  spatializer:
    type: 3d_spatialized           # follows actor world position
    attenuation_curve: weapon_swing # specific to swords
    early_reflections: true         # plays nicely in tight rooms
    reverb_send: ambient_per_zone   # zone-aware reverb
  mood_aware: false                  # spell SFX don't change with mood
  animation_sync: weapon_skill_animation_event  # synced via AnimNotify
```

The runtime spatializer pulls source files from the SFX library
and positions them in 3D space relative to the listener camera.
A galkan WAR's heavy footstep on the listener's left rear sounds
*from the listener's left rear*. A boss's roar at 40m sounds
distant and reverb'd. A friendly skillchain detonation behind
the camera produces the audible whip-and-flash from behind.

This is fundamentally different from the canonical FFXI's stereo-
only audio. **The spatial difference alone makes Demoncore sound
20 years newer**, even before any sample-quality upgrades.

---

## The pull-and-remaster pipeline

Sister batch to `EXTRACT_RETAIL_MUSIC.bat`:

```
EXTRACT_RETAIL_SFX.bat
  - POLUtils → walks every .SE2 (sound effect) and .SPW (speech)
    file in retail client ROM directories
  - Converts to WAV (mono, native sample rate ~22kHz)
  - Outputs to extracted/sfx_retail/<category>/
  - Categories: spells/, weapon_skills/, footsteps/, ambient/,
                ui/, combat_impacts/, voice_lines/
  - Writes manifest.json with category + duration + canonical name
```

Total expected output: ~3000-4000 SFX files across all
categories, ~3 GB uncompressed audio.

### `server/sfx_pipeline/`

```
class SFXPipeline:
    def upscale_canonical(self, source_path, output_path):
        """Class 1/2 SFX upgrade — AudioSR super-resolution +
        light tonal balance. Preserves timbre."""
        ...

    def author_new_mechanic_sound(self, mechanic_id, prompt):
        """Class 3 — generate or compose new SFX for new mechanics
        (chakra flow, intervention shimmer, dual-cast bell)."""
        ...

    def generate_variation_set(self, base_sfx, num_variations):
        """Class 4 — produce N pitched / time-shifted / EQ'd
        variations of a base sample for runtime selection."""
        ...

    def write_metadata_manifest(self, sfx_dir, output_manifest):
        """Write the spatializer-config YAML that UE5 reads."""
        ...
```

Two backends:
- **stub** — for CI; writes JSON manifest entries
- **audiosr** — real super-resolution via AudioSR HTTP service

---

## Specific worked examples

### Example 1: Crescent Moon weapon skill audio

```
SOURCE:    extracted/sfx_retail/weapon_skills/ws_crescent_moon.wav
           (22kHz mono, 1.4s duration)

PROCESS:
  1. AudioSR upscale to 48kHz mono
  2. Light EQ: -3dB at 6kHz, +1dB at 80Hz for body
  3. Save as 48kHz mono, no surround mixing yet (mono is fine
     for runtime positioning)

OUTPUT:    sfx_remastered/weapon_skills/ws_crescent_moon.wav
           48kHz mono, same envelope, slightly cleaner

METADATA:  spatializer 3d, attenuation_curve weapon_swing,
           sync_to anim_notify "WS_CrescentMoon_Impact"
```

The player who used Crescent Moon in retail FFXI 2003 will
recognize the sound instantly. The upgrade is *clarity*, not
substance.

### Example 2: NIN Hand-Sign Chakra Flow (new mechanic)

No retail equivalent. Authored from scratch:

```
DESIGN:
  - 4-second loop, ramps brightness over the seal sequence
  - Layer 1: low blue ambient hum, ~80Hz fundamental
  - Layer 2: sparse high-tinkle (suikinkutsu-style water bell)
  - Layer 3: per-seal "click" on each hand-pose lock
  - Layer 4: brightness ramp = harmonic series rising to
            mid-range as sequence progresses

OUTPUT:    sfx_authored/nin/chakra_flow_loop.wav
           48kHz stereo, 4s loop

METADATA:  spatializer 3d (positioned at NIN's hand sockets),
           mood_aware false, layer-blend params on the
           AnimGraph slot
```

This is a designer composition, not a synthesis. ~3-4 hours of
work in Reaper or Pro Tools. Would generate via prompt-driven
audio model only as a placeholder for a quick first pass.

### Example 3: Intervention MB Cure-V Light Save

Per `INTERVENTION_MB.md`, the apex moment: WHM lands Cure V on
a Light skillchain at the perfect moment, cancels enemy ultimate
damage, 5x Regen V applied to entire party.

The sound:
- 0.0s: gold harp glissando (~1s, ascending)
- 0.5s: choir vocal "ah" sustain
- 0.8s: bell chime (high)
- 1.2s: layered shimmer particles
- 1.5s: warm breath + audible crowd murmur (the party reacting)

Total: 1.5-second cue + 30-second Regen-V ambient drone
underneath while the buff is active.

This is the audio bookend for the most heroic moment in the
game. Authored once; played whenever the trigger fires.

---

## Mood awareness for Class 1/2 (subtle)

Even canonical SFX get *mild* mood modulation at runtime:

- A `furious` actor's footsteps land slightly heavier (lower-end
  EQ +0.5dB)
- A `fearful` actor's footsteps are quieter (-2dB) and faster
- A `drunk` actor's swing-and-impact has slight pitch waver
- A `contemplative` actor's casts have +5% reverb send

These are SUBTLE — players won't consciously notice. But the
world *feels* alive because every sample is being live-mixed
through the actor's current mood state.

---

## Visual effects pairing (post-production note)

Per user direction: **all visual effects synced to SFX are
post-production work**. We don't author the VFX during the SFX
pipeline. Instead:

- Each SFX has a `vfx_pair_id` metadata field referencing a
  Niagara emitter / particle system
- The runtime triggers SFX + VFX simultaneously via shared
  AnimNotify or trigger event
- VFX revamps happen later — the SFX library is authored
  first; VFX hooks in via the metadata

This decoupling lets us ship the full SFX library before any
new VFX exists. The original FFXI VFX (which look dated) play
against the new SFX initially; later we swap in the modern
Niagara VFX without touching audio.

---

## Status

- [x] Architecture doc (this file)
- [ ] EXTRACT_RETAIL_SFX.bat (POLUtils-driven extraction)
- [ ] server/sfx_pipeline/pipeline.py (upscale + author + variations)
- [ ] AudioSR HTTP service setup notes (Higgs-companion deployment)
- [ ] data/sfx_remastering_targets.json — full ~4000-asset catalog
- [ ] First test: Crescent Moon WS audio remaster
- [ ] First test: NIN chakra flow loop authoring
- [ ] First playtest: walk through Bastok with new audio
- [ ] First playtest: full Maat fight with HD audio + cinematic camera
- [ ] VFX-pairing post-production (after SFX library lands)
