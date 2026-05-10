# Demo showcase pipeline — Bastok Markets, live-action quality

The previous batches built the cinematic stack — cameras,
lenses, atmospherics, the render queue, the metahuman driver,
the voice casting room, the screenplay engine, the storyboard,
the shot list, previs, continuity. Each individually capable;
nobody yet had to plug them all in together for a thing the
producer could open in front of a publisher and say *here, watch
this*.

This batch is that thing. Five modules that take the project
from "a stack of cinematic capabilities" to "a five-minute,
1080p-60fps-on-PC-Ultra, 4K-24fps-trailer-master Bastok Markets
walkthrough you can show as a demo." It connects the existing
retail-extraction pipeline (``EXTRACT_BASTOK_FROM_RETAIL.bat``,
``RUN_BASTOK_BLOCKOUT.bat``, ``UPSCALE_BASTOK_TEXTURES.bat``,
``bastok_layered_scene.py``) on the input side to the existing
cinematic + voice + pre-production stacks on the output side,
with a packager at the end that bundles a manifest, validates
every reference, and reports an estimated build size.

## Vision

Bastok Markets, 2002. Six-hundred-tri buildings, 256x256
textures, smelter haze rendered as a flat sprite, NPCs whose
faces are paintings on flat planes. The retail extraction
pipeline already pulled all of it onto disk. Demoncore's job
is to walk every asset through the open-source upgrade chain
— Real-ESRGAN, Marigold, StableDelight, CodeFormer, Material
Maker, Blender Geometry Nodes, UE5 Nanite — and end at a
five-minute showcase where:

- Player spawns into the Mines tutorial under the narrator's
  voiceover.
- Emerges into Bastok Markets through the north arch — wide
  establishing god-rays cut through volumetric smelter haze.
- Cid is forging at his anvil, hammering mid-cinematic.
- Volker greets the player at the musketeer briefing post and
  hands off a quest.
- The crowd does an ambient walk past the player on the main
  concourse.
- A bandit raid triggers in the clutter alley — three bandits
  spawn, three crates and a barrel get destructible-physics-ed.
- A magic burst skillchain demo lands on Iron Eater's shadow.
- Iron Eater himself appears — cinematic boss reveal, low hero
  angle, his theme music kicks in.

Eight beats. Every beat is one ``Beat`` in
``showcase_choreography``. Every character is one
``CharacterEntry`` in ``character_model_library``. Every set-
dressing item is one ``DressingItem`` in ``zone_dressing``.
Every voice line is one role in ``voice_role_registry``. Every
asset on its way from retail-quality to ship-ready is one
``AssetRecord`` in ``asset_upgrade_pipeline``. The producer
points ``demo_packaging`` at the demo and gets one
``DemoBuildManifest`` back; ``DemoPackager.validate`` rolls up
every cross-reference into a pass/fail.

## The five modules

### server/asset_upgrade_pipeline/

The forge. State machine per asset:

    RAW → UPSCALED_TEXTURE → NANITE_BUILT
        → MATERIAL_AUTHORED → PBR_BAKED
        → LOD_GENERATED → SHIP_READY

with a FAILED branch that retries from RAW (preserving the
error history for the post-mortem audit). Tools enumerated:
Real-ESRGAN for the 256x256 → 4096 texture upscale, Marigold
for depth-from-image as a normal-map source, StableDelight for
relighting, CodeFormer for face restoration, Material Maker
for procedural PBR authoring, Blender Geometry Nodes for the
remesh that fits the UE5 Nanite import budget. Per-zone
batch ops: ``upgrade_all_in_zone``, ``zone_progress`` returns
``(total, complete, failed, pct)``, ``throughput_per_hour``
walks the transition log to tell the producer how many assets
SHIP_READY-ed in the last N hours. Illegal forward jumps (RAW
→ MATERIAL_AUTHORED, skipping mesh build) are rejected.

### server/character_model_library/

Per-character presentation. ``mesh_lod_set`` holds four LODs —
nanite_dense (0–15m), nanite_mid (15–50m), card_billboard
(50–150m), impostor (150m+). ``material_set`` holds skin / eye
/ teeth / hair_groom URIs. ``costume_layers`` stack outward
with a sort order. ``eye_setup`` carries sclera and iris hex,
cornea IOR (default 1.376; Galka override 1.40), and a sclera
blood amount knob. ``tooth_setup`` carries enamel hex,
crowding factor (0 for human, 0.45 for Galka tusks), and
plaque amount. ``hair_groom_kind`` is one of GROOM_STRANDS
(Niagara hair) or HAIR_CARDS (textured planes; the fallback
for crowds), with a ``hair_card_count`` validator.

The Bastok Markets demo roster is built-in: Volker, Cid, Iron
Eater, Naji, Romaa Mihgo, Cornelia, Lhe Lhangavo, plus four
generic crowd templates (galka smith, hume engineer, mithra
musketeer, taru apprentice, elvaan visitor) — twelve entries.
Each carries an optional ``metahuman_link`` cross-referencing
the existing ``metahuman_driver`` registry so the rig and
ARKit blendshape mapping flow through unchanged.

### server/zone_dressing/

Set-dec. Thirty-two built-in items for Bastok Markets across
five categories: Cid's workshop (forge, anvil, lathe, hammer
rack, mythril ingot pile, water trough, sparks-particle
anchor, leather apron stand — eight items), vendor stalls
(mythril smith, weapons, armor, fish, fruit, ironworks
tickets — six items), wall posters (notices board, wanted
bandit, musketeer recruitment, mythril industry — four
items), ambient clutter (eight items, four destructible),
three-tier gallery overlook props (three items), plus two
bandit-raid evidence drops. Every item carries a parent kind
(FLOOR / WALL / CEILING / FURNITURE / HUNG), a narrative tag
("cid_workshop_lathe" / "bandit_raid_evidence"), a time-of-
day variant, an interactable flag, and a physics kind. The
sparks-particle anchor is night-only; the fish and fruit
stalls are day-only. ``destructible_in_zone`` is what the
bandit-raid combat layer reads to know what it can crash
through.

### server/showcase_choreography/

The eight-beat running order. Each ``Beat`` carries a
``trigger`` (PLAYER_ENTERS_VOLUME / TIMER_AT_T / DIALOGUE_END
/ SKILLCHAIN_COMPLETED / MOB_PHASE_X), a location volume id,
a ``camera_handoff`` string the ``director_ai`` layer
consumes as a shot-kind hint, ``dialogue_line_ids`` the
``voice_role_registry`` resolves into voice-line URIs, an
expected duration, optional mob spawn ids, an optional music
cue id, and a ``fallback_if_skipped`` for the player who
walks past a trigger volume too fast. ``advance(seq, beat_id)``
returns the next beat or None at the terminal. ``fallback_for``
returns the recovery beat. ``validate_sequence`` checks every
fallback target exists and every beat is reachable. The whole
sequence is deterministic — the same beat list ships every
time, so the trailer master and the shippable demo are bit-
identical.

### server/demo_packaging/

The packager. ``DemoBuildManifest`` holds zone, character ids,
voice track URIs, dressing item ids, choreography sequence
name, music cue list, render preset (trailer_master is the
default — 4x size multiplier over gameplay_realtime),
target platform (PC_HIGH / PC_ULTRA / XBOX_SERIES_X / PS5),
estimated size in GB, validation status, and a missing-
assets list. ``validate(manifest_id)`` calls four
dependency-injected existence-check callables — one per
upstream registry — and returns a ``ValidationReport``. The
default callables accept everything (so unit tests work
without wiring the whole project graph); production wires
them to ``character_model_library.has``,
``voice_role_registry.lookup``, ``zone_dressing.has``, and
``render_queue``'s known preset list.

Estimated size formula:

    8.0 GB  zone
    1.2 GB  per character
    0.05 GB per voice line
    0.001 GB per dressing item
    multiplier:
      gameplay_realtime  1.0
      cutscene_cinematic 3.0
      trailer_master     4.0
      social_clip        1.5
      led_virtual_production 2.5

The Bastok Markets default manifest at trailer_master comes
out somewhere north of 30GB; the gameplay_realtime build is
under 12GB. ``bastok_markets_default()`` is the one-call
demo shipper.

## Integration with existing batches

The retail extraction batch (``EXTRACT_BASTOK_FROM_RETAIL.bat``
+ ``RUN_BASTOK_BLOCKOUT.bat`` + ``UPSCALE_BASTOK_TEXTURES.bat``)
hands ``asset_upgrade_pipeline`` a directory of low-poly /
low-res raw assets. Each is registered with
``register_asset(...)`` at state RAW. Upscale runs marshal
state advances to UPSCALED_TEXTURE; mesh builds advance to
NANITE_BUILT; etc.

``character_model_library`` references ``metahuman_driver``
records by id (no import; just a string field). The
``voice_role_registry`` already has Volker, Cid, Iron Eater,
Romaa Mihgo, Lhe Lhangavo and the generic narrator slot — the
``demo_packaging.validate`` step can wire ``has_voice_line``
to ``voice_role_registry.lookup`` once the line-id naming
schema is finalised.

``showcase_choreography``'s ``camera_handoff`` strings
(WIDE_GOD_RAYS, MEDIUM_OVER_SHOULDER, TWO_SHOT_EYE_LINE,
DOLLY_FOLLOW, HANDHELD_WHIP, LOW_HERO_ANGLE,
CINEMATIC_BOSS_REVEAL, ESTABLISHING_INT_TIGHT) map to the
``director_ai`` shot-kind taxonomy. The pre-production batch's
``screenplay_engine`` writes the dialogue lines that feed
``Beat.dialogue_line_ids``; the ``shot_list`` walks the same
beats to produce the production strip board; the
``previs_engine`` exports a UE5 Sequencer USD per beat for
the rehearsal review.

``demo_packaging.render_preset`` references the existing
``render_queue.PRESETS`` dict by name. ``trailer_master`` is
the 24fps 16-bit half-float EXR / ACES OCIO preset; the
packager defaults to it for demo builds and falls back to
``gameplay_realtime`` for live walkthroughs.

## Demo target spec

- 1080p / 60fps on PC_ULTRA — gameplay_realtime preset, 12GB
  build, mp4 H.265 deliverable.
- 4K / 24fps trailer master — trailer_master preset, 32GB
  EXR sequence, ACES AP0, no compression. Producer renders
  this once per milestone for the publisher meeting.
- Total walkthrough length: 132 seconds across eight beats
  (computed by ``ShowcaseChoreography.total_duration_s``).
- Eleven heroes + crowd templates, thirty-two dressing items,
  ten voice lines, eight music cues — the demo's full asset
  manifest fits in one screen of producer review.

## Open-source asset stack

- **Real-ESRGAN** — image super-resolution, MIT (xinntao).
- **Marigold** — diffusion-based monocular depth, Apache.
- **StableDelight** — diffusion-based relight, MIT.
- **CodeFormer** — face restoration, NTU.
- **Material Maker** — Godot-based procedural materials, MIT.
- **Blender Geometry Nodes** — open-source remesh, GPL.
- **UE5 Nanite** — Epic, royalty-free under 5% Unreal license.
- **Niagara hair grooms** — Epic, royalty-free.
- **OpenColorIO ACES OCIO** — colour pipeline, BSD.
- **OpenEXR** — half-float EXR sequence output, BSD.

Every link in the upgrade chain ships under a license
compatible with the project's open-distribution intent.

## Three design hinges

1. **Demo is a manifest, not a build script.** The packager
   doesn't drive the build — it *describes* the build. The
   actual rendering is the existing render_queue's job. The
   actual mesh upgrade is the existing asset_upgrade_pipeline's
   job. The packager owns one piece: the cross-reference
   validation that says "every character this manifest names
   exists in the model library, every voice line exists in
   the role registry, every dressing item exists in the zone
   book, the render preset is one of the five known names."
   Validation lives where the cross-references live.

2. **Choreography is an explicit beat list, not a scripted
   timeline.** Eight beats with explicit triggers, durations,
   and fallbacks. Player-state-machine-friendly. The director
   doesn't have to walk a frame timeline; they ask the
   choreography "what's beat 3?" and get a Beat record back
   with the camera hint, the dialogue ids, the music cue, and
   the recovery path. The trailer master and the live demo
   walk the same beat list.

3. **Asset upgrade is a state machine, not a pipeline graph.**
   Forward-only DAG with a FAILED retry edge. Every transition
   is logged. The producer's daily question — "how many of
   the 600 Bastok assets are SHIP_READY?" — is one
   ``zone_progress(zone_id)`` call. The throughput question —
   "are we going to make the milestone?" — is one
   ``throughput_per_hour(window_hours)`` call. State machines
   are how factories work; this module is the factory floor.

The retail extraction layer can already pull Bastok onto disk.
The cinematic stack can already shoot it. The voice stack can
already speak it. The pre-production stack can already plan
it. This batch is the *demo packager that wires it all
together end-to-end*. From here, the producer can hand a USB
stick to a publisher.
