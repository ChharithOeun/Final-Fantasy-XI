# Combat VFX + Spell Systems

Five-module batch that turns the Bastok demo's combat
beats — bandit raid, skillchain burst, Iron Eater intro —
from "things happen" into things that *land*. Niagara
particles in the engine layer, FFXI's spell-chain rules in
the server layer, screen-bound post-process for the
camera. The previous batch built character life; this one
builds the verbs.

## Vision

Cinematic combat is mostly punctuation. The act of hitting
something is already animated by the weapon-skill clip;
what makes the punch *connect* is the flash on impact, the
40-250 ms hitstop where the camera holds its breath, the
dust kicked up off the cobbles, the screen shake that
rides the camera, the magic-burst halo that blooms when a
skillchain closes inside the burst window. Take any of
those out and the swing feels weightless. Stack them
correctly and a single great-axe stroke at frame 0 cracks
four crates, ignites two, and drops a flaming awning at
frame 90 — the bandit raid is *cinema*.

The five modules in this batch are the catalog + rules
that make those punctuation marks repeatable. They do not
own simulation; UE5 Niagara owns simulation. They own the
*table of contents* the engine consults at runtime.

## The Five Modules

### server/niagara_vfx_library/ (39 tests)
The particle effect catalog. 60+ canonical effects covering
all 8 FFXI elemental families at every spell tier (I-V),
the physical impacts (blood / spark / smoke / dust / ember
/ debris), the environmental dressers (heat haze / rain
splash), the gameplay overlays (AOE rings + lines, impact
flashes, casting circles, hand glows, magic-burst halos,
KO auras, raise glows). Every effect carries a
`cinematic_tier` that scales particle count up to 4x for
the trailer shot, a `follows_emitter` flag (the spark trail
of a moving weapon strike sticks to the blade; an explosion
ring stays where it was spawned), and a sound cue id the
audio listener picks up. `tier_scaled_particle_count` reads
the LOD at render time; `warmup_recommended` flags effects
above 500 particles for a zero-emit pre-pass so the first
cast frame doesn't hitch.

### server/spell_vfx_resolver/ (38 tests)
FFXI spell name -> Niagara vfx chain. The mapping that
says "fire_iii cast" means "white casting circle, warm
hand glow on both hands, fire_tier_iii projectile vfx,
medium impact flash, fire-ember lingering puddle for 4
seconds, light pulse at 3200 lux, screen shake intensity
0.22". 40+ pre-populated spells covering 8 elements x 5
tiers + Cure I-V + Banish I-III + Raise I-III + Drain +
Aspir + Sleep + Silence + Slow + Haste + Protect + Shell.
Tier I -> IV escalates particle density + light pulse +
screen shake monotonically. Tier V (and Ancient Magic —
Flare, Comet, Tornado II, Holy II, Quake II...) flips the
`cinematic_tier_override` flag on so the engine pumps
particle counts to HIGH regardless of cinematic LOD.

Magic-Burst overlay rides on top: when `resolve()` is
called with `is_mb_active=True` (the
magic_burst_window has confirmed the cast landed inside
the 3-second window opened by a closed skillchain), the
resolver adds the MB_HALO vfx, multiplies screen shake +
light pulse by 1.5x, and emits a chromatic-aberration
spike for `lens_optics`. That overlay is the visual "YES,
THE BURST CONNECTED" feedback retail FFXI never quite
delivered.

### server/weaponskill_vfx/ (54 tests)
Physical WS visual chain. 29 pre-populated weaponskills
across all 16 weapon classes (sword, great-sword, axe,
great-axe, scythe, polearm, katana, great-katana, club,
staff, h2h, dagger, bow, crossbow, gun, marksman). Each
chain has a wind-up anim id, blade trail color +
thickness, impact flash vfx id, blood arc count, dust
burst id, shockwave id, screen shake intensity, hitstop
ms, and camera shake axis.

Skillchain glyphs: 16 canonical attributes — 8 lvl-2
fundamentals (Liquefaction red/orange, Scission
neutral-flicker, Impaction yellow, Detonation green,
Induration light-blue, Reverberation purple, Transfixion
neon-blue, Compression violet), 4 lvl-2 derived (Fusion
bright-yellow, Fragmentation cyan, Distortion ice-blue,
Gravitation dark-purple), 2 lvl-3 (Light white-spectrum,
Darkness black-with-edge), 2 lvl-4 (Crystal rainbow-prism,
Umbra void-black). Each glyph has a runic pattern id, a
sustain duration (longer for lvl-3 and lvl-4), and a
magic-burst-extends-duration that the burst window adds
when a same-element spell closes inside it.

Hitstop tuning is a single weight axis: LIGHT = 40 ms
(quick & flashy), MEDIUM = 80 ms, HEAVY = 150 ms (the
two-handed slammers), ULTRA = 250 ms (relic / mythic
finishers — the camera literally holds for a quarter
second on the killing blow). `blade_trail_for_weapon`
returns an anamorphic-style ribbon for swords / katana /
daggers (thin, elongated) and a broader trail for axes /
great-swords / clubs. H2H + bows get minimal trails — H2H
gets a wrist-pulse glow only on the chain finisher.

### server/destructible_props/ (50 tests)
Destroyable scenery. 7 armor classes with default HP
(WOOD=50, MASONRY=200, GLASS=10, METAL=500,
CRATE_LIGHT=15, BARREL_OIL=8, CLOTH_AWNING=5), 5 fracture
patterns (CRACK, SHATTER, EXPLODE, TOPPLE, BURN), and a
cascade engine. Calling `damage(prop_id, hp_delta,
element)` returns the list of prop_ids that broke as a
result, in order — so a bandit raid showcase beat that
fires `damage("oil_barrel_3", 8)` gets back ["oil_barrel_3",
"crate_light_5", "crate_light_6", "cloth_awning_main"]
because the oil barrel's 3-meter explosion radius dealt 30
fire damage to neighbors, which propagated to a CLOTH_AWNING
(2x fire multiplier) and chained.

Element rules:
- Cloth awning takes 2x damage from FIRE.
- Glass shatters from any non-physical hit.
- Oil barrels chain to all `fire_propagates`-flagged
  neighbors within radius (CRATE_LIGHT, CLOTH_AWNING,
  WOOD, BARREL_OIL itself).

`can_be_destroyed_by(prop_id, weapon_class)` answers
weapon-class compatibility: a dagger cannot crack masonry
(the walls of Bastok survive a thief), a great-axe destroys
anything (including metal anvils — eventually).

The bandit raid integration: the showcase_choreography
"bandit_raid" beat fires a sequence of `damage` calls on
the registered Bastok Markets DESTRUCTIBLE-flagged
dressing items, reads back the cascade, and hands the
fracture events to the renderer in the right frame order.

### server/screen_effects/ (46 tests)
Camera-bound post-process layer. 18 effect kinds covering
hit shake (LIGHT / MEDIUM / HEAVY / ULTRA), MB flash
(rainbow chroma-ab spike), KO fadeout (vignette + desaturate
over 1.2s), bleed-out red overlay, levitate bob,
intoxication blur, dragon-breath heat haze, undeath grain,
haste time dilation, slow time thicken, sleep vignette,
silence muffle visual, charm pink haze, paralyze static
crackle, petrification grey freeze.

Each effect carries an IntensityCurve — a sparse list of
(t, value) keyframes the system samples at any t with
linear interpolation between adjacent keyframes and clamped
endpoints. Tiny data (a hit-shake is 4 keyframes) but rich
enough to author non-linear ramps for the dramatic effects
(KO is a slow ease-out vignette).

Stacking: most effects compose. Hit shakes layer with each
other, intox blur runs alongside silence muffle. Two
effects are full-screen takeovers and block stacking:
KO_FADEOUT and DRAGON_BREATH_HEAT_HAZE — `apply()` raises
RuntimeError if you try to add either on top of an existing
effect, or anything on top of one. The screen is already
saturated; piling more on top only muddies the read.

`tick(dt)` advances all active effects, returns expired
handles, and clears them from per-player tracking.

## Integration

- `spell_catalog` + `weapon_skills` provide the spell + WS
  ids; this batch's resolver/system maps each id to the
  Niagara chain.
- `combat/skillchain_detector` reports closed skillchains
  and the attribute (Liquefaction, Fusion, Light...). The
  weaponskill_vfx system serves the right glyph color
  + runic pattern.
- `magic_burst_window` opens a 3-second window after a
  skillchain closes; spell_vfx_resolver consults the window
  state and applies the MB overlay when a same-element
  spell lands inside.
- `aoe_telegraph` reads the AOE_TELEGRAPH_RING /
  AOE_TELEGRAPH_LINE entries from the niagara_vfx_library
  for its red-zone-on-the-floor effect.
- `zone_dressing` provides the source dressing pieces;
  destructible_props wraps the DESTRUCTIBLE-flagged subset
  in HP + cascade rules.
- `showcase_choreography` (bandit_raid beat) fires the
  damage calls into destructible_props and reads back the
  cascade list for renderer scheduling.
- `cinematic_camera` reads the screen_effects active list
  to apply hit-shake offsets to the camera transform.
- `lens_optics` reads the `chromatic_aberration_spike` from
  the resolved spell vfx for its post-process aberration
  pass.
- `audio_listener_config` reads the `sound_cue_id` /
  `sound_event_id` from every effect chain so the audio
  layer hits in lockstep with the visuals.
- `atmospheric_render` provides the `light_emit_lux`
  baseline; spells that emit serious light (Fire V at
  9600 lux) push the global exposure briefly.

## Open-source toolchain

- **Niagara** — comes with UE5; native particle engine.
  Effects in this batch reference Niagara system asset
  paths the engine resolves at runtime.
- **Houdini Apprentice** — free non-commercial tier;
  fluid sims + procedural debris cascades for the bandit
  raid pre-vis. Bake to alembic + import as Niagara
  Geometry Cache.
- **Embergen** — free indie tier; real-time fluid sim for
  the dragon-breath heat haze and oil-barrel explosion
  fireballs. Bakes to flipbook texture sheets that Niagara
  reads directly.
- **Cascadeur free tier** — physics-based animation for
  the wind-up + recovery on the heavier WS clips.

## Cross-module flow — bandit raid beat

1. `showcase_choreography` reaches the "bandit_raid" beat
   at frame 0. It calls
   `weaponskill_vfx.resolve_ws_vfx("ukko_fury")` for the
   raider's opening swing — gets the wind-up anim id, the
   broad amber-metal blade trail, the heavy impact flash,
   the dust_explosion burst id, 250 ms hitstop.
2. The swing connects with an oil barrel.
   `destructible_props.damage("bastok_oil_barrel_3", 30,
   element=FIRE)` returns ["bastok_oil_barrel_3",
   "bastok_crate_5", "bastok_crate_6",
   "bastok_awning_spice"]. The cascade is the bandit raid's
   visual climax.
3. For each cascaded prop, the showcase reads
   `fracture_event(prop_id)` and hands the
   FractureEvent (pattern=EXPLODE / pattern=BURN /
   pattern=CRACK, debris_count, replaces_with id,
   particle_emit_id like "ember_storm" or "debris_wood")
   to the renderer.
4. `screen_effects.apply(EffectKind.HIT_SHAKE_ULTRA, "player")`
   shakes the camera for the kill blow.
5. The follow-up Iron Eater intro fires its black-magic
   cast: `spell_vfx_resolver.resolve("comet",
   is_mb_active=True)` returns a ResolvedSpellVfx with the
   AM cinematic_tier_override flag and the MB_HALO overlay
   (chromatic_aberration_spike=0.35) because the prior
   skillchain (Fragmentation) closed inside the 3-second
   burst window.
6. The renderer pumps the comet vfx particle count to
   HIGH-tier at trailer LOD (4x) — 3600 particles on the
   ground impact — and the lens_optics module spikes the
   chromatic aberration on the same frame as the impact
   flash. The bandit raid lands like film.

## Three design hinges

1. **THE LIBRARY IS VOCABULARY, NOT SIMULATION.** Niagara
   in UE5 owns simulation. This module is the catalog the
   engine consults at runtime to answer "what particle
   pack, how big, what color, how loud, how much light?"
   That separation lets us re-tune the cinematic LOD
   (LOW/MED/HIGH/TRAILER) without touching the simulation,
   and re-tune the simulation (Niagara emitter rates,
   collision modes) without touching the catalog.

2. **CASCADES ARE THE BANDIT RAID.** A bandit who only
   knocks down individual crates is a stage-prop bandit. A
   bandit who hits one oil barrel and watches it cascade
   through three crates and a flaming awning is *acting in
   a heist film.* The cascade engine in destructible_props
   is the cheap-but-load-bearing trick: the showcase
   choreography fires one damage call and gets back the
   whole sequence, in order, ready to schedule across the
   beat's frame budget.

3. **SCREEN EFFECTS ARE PUNCTUATION.** Stack a hit shake
   on a magic-burst flash on a chromatic-aberration spike
   and the player *feels* the damage even if their eyes
   are reading the HP bar. Block stacking on the
   takeovers (KO, dragon breath) — the screen is already
   saturated; more on top is just mud. The intensity-curve
   format keeps the data tiny (4 keyframes for a hit
   shake, 5 for a paralyze crackle) so we can author
   dozens of effects without bloating the asset pipeline.

The previous batch made the world breathing. This batch
makes it punch.
