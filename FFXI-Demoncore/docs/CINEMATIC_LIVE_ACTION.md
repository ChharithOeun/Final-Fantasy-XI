# Cinematic Live-Action Render Pipeline

> "The save file looks like the movie someone would have made of it."

This is the render-pipeline addendum to `CINEMATICS.md`,
`CINEMATIC_GRAMMAR.md`, and `LAYERED_COMPOSITION.md`. Those
docs cover *why* Demoncore looks the way it does — film
grammar, layered framing, blocking. This one covers *how
the pixels get there*: which open-source tools we use, how
the server publishes camera intent, and how UE5 realises
that intent end to end.

## Vision

FFXI Demoncore is rendered as if a film crew were on set
every time a player draws a sword. Not "stylised", not
"painterly" — live action. The image discipline is the same
discipline you'd apply to a Denis Villeneuve picture: real
sensors, real glass, real volumetrics, real grain, ACES
colour science, motion blur driven by shutter angle, depth
of field driven by aperture.

That bar shows up in three places:

1. **Cutscenes** — already covered by the Sequencer +
   MetaHuman + path-tracer pipeline in `CINEMATICS.md`.
2. **Gameplay** — the same colour pipeline, the same lens
   model, the same atmospherics, just at realtime fidelity
   (TSR + Lumen instead of path tracer).
3. **Trailer / promo cuts** — ProRes 4444 or 16-bit EXR
   masters from MRQ, ACES OCIO config, no compromise.

The five modules in this batch give the server everything
it needs to drive (1)–(3) consistently. The server picks
the camera, the lens, the LUT, the atmosphere, and the
render preset; UE5 applies them via Live Link and Movie
Render Queue.

## Open-source toolchain

* **UE5** (Epic source license) — Lumen, Nanite, virtual
  shadow maps, TSR, path tracer, Cine Camera Actor,
  Sequencer, Movie Render Queue.
* **MetaHuman Creator + MetaHuman Animator** — facial
  performance, hair groom, body shape variants.
* **OpenColorIO (OCIO) 2.x** — ACES 1.3 config; the
  `film_grade` LUT chain ships as an OCIO config UE5 reads
  from disk.
* **OpenEXR** — `trailer_master` writes 16-bit half-float
  EXR sequences.
* **DaVinci Resolve** (free tier) — final colour pass on
  trailer masters; ACES round-trip is lossless thanks to
  the OCIO config.
* **ICVFX plugin** (UE5 first-party, open) — drives the
  LED wall for in-camera VFX shoots; the
  `led_virtual_production` preset and `atmospheric_render`
  module both feed this.
* **Niagara** — particles, dust motes, flare embers; the
  `atmospheric_render` `dust_mote_density` parameter is
  a Niagara emitter rate.

## How the five modules feed UE5

```
                          ┌─────────────────────┐
                          │  Demoncore server   │
                          └─────────┬───────────┘
                                    │
   ┌─────────────────┬───────────────┼───────────────┬────────────────────┐
   │                 │               │               │                    │
   ▼                 ▼               ▼               ▼                    ▼
cinematic_camera  film_grade     lens_optics  atmospheric_render   render_queue
sensor / iso /    ACES + LUT     focal /      density / god rays /   preset /
shutter / WB      chain          T-stop /     LED wall colour /      fps / codec /
                                 anamorphic / scatter anisotropy     bit depth
                                 bokeh
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │  Live Link / OCIO   │
                          └─────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
            Cine Camera      Post-Process Vol    ExpHeightFog +
            Actor (lens +    (LUT, exposure,     VolumetricCloud +
            sensor crop)     RRT/ODT)            LightShafts
                                    │
                                    ▼
                            Movie Render Queue
                            (preset → output)
```

Each module exposes a `get_render_intent()` (or analogous
function) that returns a JSON-serialisable dict. The Live
Link bridge ships the dict frame-by-frame; UE5's Cine Camera
+ post-process volume + ICVFX pipeline read from it.

### `cinematic_camera`
Real-camera body parameters — Arri Alexa 35, Alexa Mini LF,
RED V-Raptor 8K VV, Sony Venice 2, BMD URSA Mini Pro 12K,
iPhone 16 Pro (handheld B-roll), Canon C500 Mk II. Sensor
geometry, native ISO, dynamic range, max resolution, color
matrix, gate aspect, rolling-shutter readout. Shutter angle
defaults to 180°; configurable. ISO must lie inside the
selected camera's range — ISO 25600 is fine on a BMD 12K
but illegal on a Mini LF.

### `film_grade`
ACES working space (ACEScg) with the 1.3 RRT/ODT pair.
LUT library: Kodak Vision3 250D, Kodak Vision3 500T, Fuji
Eterna 250D, Cinestyle (Technicolor), Bleach Bypass,
Day-for-Night, Demoncore Standard. Per-scene exposure
metering targets Zone V skin tone (0.18 linear). White
balance is shooter-set in kelvin; the system labels it
(tungsten / fluorescent / daylight / cloudy / overcast).

### `lens_optics`
Lens kit: Cooke S4 (32/40/50/75/100), Atlas Orion 2x
anamorphic (40/65/100), Zeiss Master Prime (35/50/85),
Helios 44-2 vintage 58. Per lens: focal length, T-stop
range, anamorphic squeeze, distortion k1, vignette, flare
colour, bokeh shape, breathing flag. Aperture-driven DoF
via thin-lens approximation. Anamorphic glass flares 1.5×
hotter than spherical at the same lux.

### `atmospheric_render`
Per-zone profile of density, god-ray count, distance haze,
dust motes, LED-wall ambient colour, scatter anisotropy.
Weather (clear / overcast / rain / sandstorm / aurora) maps
to density + scatter; time-of-day (dawn / day / dusk /
night) maps to god-ray multiplier. This is the source of
the Mandalorian StageCraft "you can feel the air" look —
forward-scatter HG g, hot-spot lighting, hard rim light.

### `render_queue`
Movie Render Queue presets. `gameplay_realtime` (60fps TSR
H.265 8Mbps), `cutscene_cinematic` (24fps path-traced
ProRes 4444), `trailer_master` (24fps 16-bit half-float EXR
ACES AP0), `social_clip` (60fps 4K AV1 mobile-optimised),
`led_virtual_production` (24fps ICVFX). `cost_factor`
estimates wall-clock time per second of footage —
`gameplay_realtime` is 1×, `trailer_master` is 120×, so a
60-second trailer takes 2 hours.

## Comparison to Mandalorian StageCraft

StageCraft (ILM, 2019) has three pillars: (a) LED wall as
diegetic light source, (b) camera tracker driving in-engine
parallax, (c) match-grade colour pipeline so the in-camera
plate matches the final master without re-grading. We do
exactly the same with off-the-shelf open source:

| StageCraft pillar    | Demoncore equivalent                              |
| -------------------- | ------------------------------------------------- |
| LED wall as light    | `atmospheric_render.led_wall_color` per zone +    |
|                      | UE5 `nDisplay` + ICVFX plugin                     |
| Camera tracker /     | `cinematic_camera` profile published via Live     |
| in-engine parallax   | Link to UE5 Cine Camera Actor                     |
| Match-grade pipeline | OCIO 2.x config built from `film_grade.LUTS`,     |
|                      | shared by UE5, Resolve, Nuke, Houdini             |

Where StageCraft cost ILM eight-figure capex, Demoncore
runs on a 4090 + a free Epic source license. The aesthetic
ceiling is the same; only the throughput differs.

## Cross-references

* `CINEMATICS.md` — high-level cinematic vision (live-action
  theatrics, anamorphic letterboxing, three-point lighting).
* `CINEMATIC_GRAMMAR.md` — shot-grammar rules: when to use
  wide vs. close, blocking, edit cadence, axial cuts.
* `LAYERED_COMPOSITION.md` — fore-/mid-/back-ground layering
  rules; the `lens_optics.depth_of_field_meters` output is
  the parameter that makes the layer separation visible.
* `CINEMATICS_VIRTUAL_PROD.md` — virtual production workflow
  (LED wall, ICVFX, in-camera VFX); now backed concretely
  by `atmospheric_render` and the
  `led_virtual_production` render preset.
* `MUSIC_PIPELINE.md` / `SFX_PIPELINE.md` — diegetic audio
  chain; renders are mastered against a -23 LUFS broadcast
  loudness target, set in MRQ.

## A test cut, end to end

A boss-intro cutscene for the Maat encounter:

1. **Camera.** Director picks `arri_alexa_35`, ISO 800,
   shutter 172.8° (slightly tighter than 180 — a Roger
   Deakins choice), white balance 4300K (the Bastok
   foundry is fluorescent-lit). `cinematic_camera`
   publishes the intent.
2. **Lens.** A `cooke_s4_50mm` at T2.0 for the
   over-the-shoulder; a `helios_44_2_58mm` at T2.0 for
   Maat's reaction shot — that swirly bokeh signals
   memory-lane. `lens_optics.depth_of_field_meters` says
   ~0.4m of DoF, so the rack focus has to be precise.
3. **Grade.** `kodak_vision3_500t` LUT for the cool
   tungsten foundry interior. `film_grade.exposure_meter`
   on the average scene luminance returns +0.3EV — the
   cinematographer wants the shot a hair brighter than
   the meter says.
4. **Atmosphere.** `atmospheric_render.set_zone_atmosphere`
   for `bastok_metalworks` with density 0.4 (smoke from
   the forge), `god_ray_count=8` for the high windows,
   `led_wall_ambient_color=(1.0, 0.6, 0.3)` (forge fire),
   `scatter_anisotropy=0.5` (forward scatter — the godrays
   read).
5. **Queue.** `cutscene_cinematic` preset. 90 seconds of
   sequence × 30× cost factor = 45 minutes of render.
   The producer goes for coffee.

The result lands on disk as a ProRes 4444 in ACES AP1, ready
to be cut into the master timeline in Resolve. No re-grade
needed; the OCIO config the renderer used is the same OCIO
config Resolve loads.

That's the pipeline.
