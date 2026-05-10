# Cinematic Performance & Direction

## Vision

The previous batch built the camera truck — bodies, glass,
ACES grade, atmospheric volumetrics, render queue. This
batch builds the layer that **drives** that truck. It gives
Demoncore a performance-capture pipeline (face + body), a
MetaHuman avatar driver that maps every FFXI hero NPC and
every PC race archetype to a real MetaHuman rig, a phoneme-
to-viseme lipsync analyzer that stitches Higgs Audio output
to the character's mouth, an AI cinematographer that picks
the next shot, and a Murch-six pacing engine that picks the
moment to cut. Together they let the server speak the
language of a real film set so the LLM-driven director can
make Camerimage-grade decisions while the world runs at 60fps.

## The Five Modules

### `server/performance_capture/`
Five real capture devices — Live Link Face (iPhone TrueDepth
ARKit, 52 blendshapes at 60Hz), Rokoko Smartsuit Pro II (19
IMU body sensors at 100Hz), OptiTrack Prime 41 (41 optical
markers at 240Hz, 4ms latency, the hero combat rig), Faceware
Mark IV (head-mounted facial), and MetaHuman Animator
(video-only, runs offline). The session lifecycle is
`REGISTERED → CALIBRATED → CAPTURING → POST → ARCHIVED`. A
take can combine facial + body devices into one TakeRecord;
the picker (`best_device_for(scene_kind)`) routes dialogue to
LLF, combat to OptiTrack, on-location to Rokoko, post pickups
to MetaHuman Animator.

### `server/metahuman_driver/`
At least 18 avatar bindings — eight canon heroes (Curilla,
Volker, Ayame, Maat, Trion, Nanaa Mihgo, Aldo, Cid) plus the
ten PC archetypes (5 races × M/F, with Mithra female-only
and Galka male-only encoded as a hard rule). Each binding
carries its MetaHuman template, face blueprint id, body
skeleton variant, skin-tone id, and costume rig id. The
ARKit 52-blendshape spec is the canonical face layer; six
named emotion templates (HAPPY / ANGRY / AFRAID / SAD /
SURPRISED / NEUTRAL) expand to per-shape weights with
intensity scaling. `retarget_animation` returns an IK-rig
intent for UE5 — same-race vs. cross-race, with height
normalisation flagged when needed.

### `server/dialogue_lipsync/`
Four supported engines: NVIDIA Audio2Face (hero-quality,
ARKit blendshapes), Rhubarb Lipsync (open source MIT, the
ambient default), Oculus Lipsync (15 visemes), Apple Speech
Synthesizer (when iOS is the capture rig). The phoneme map
folds 40 ARPAbet English phonemes into a 14-viseme set;
unsupported languages demote to Rhubarb-en automatically.
Lipsync tracks move `PENDING → ANALYZING → READY → BAKED`;
the baked curve is a per-frame dict of viseme weights summing
to 1.0, ready for Live Link to feed the MetaHuman face
control rig. Hero NPCs are pinned to Audio2Face via a small
override map.

### `server/director_ai/`
Encodes CINEMATIC_GRAMMAR.md / LAYERED_COMPOSITION.md /
BOSS_GRAMMAR.md as a (SceneKind × Tempo) decision matrix
over ten shot types — wide establishing, medium, medium
two-shot, close-up, extreme close-up, OTS, POV, overhead,
Dutch angle, handheld. `suggest_shots` returns a ranked
top-3 with focus-target refinement (zero targets removes
intimate shots; two-plus targets bonus-boosts OTS / two-
shot). `violates_180` enforces the 180° rule with the
canonical exemptions (overhead, ECU, POV cross the line
legally). `pick_next_shot` handles the OTS reverse-shot
rhythm. `score_shot` is the public oracle the pacing layer
calls.

### `server/scene_pacing/`
Walter Murch's "Rule of Six" weights in code: emotion 51%,
story 23%, rhythm 10%, eye-trace 7%, 2D plane 5%, 3D space
4% — summing to 1.0. `score_against_murch_six` is the
weighted oracle. Per-scene-kind pacing profiles (avg /
min / max shot duration, allowed jump cuts, cross-cut
density) are sourced from convention — combat_close averages
1.4s, dialogue 4.5s, exploration 6.5s. A registered sequence
is a list of `Beat(kind, duration, intensity)` from
`SETUP / ESCALATION / REVEAL / CLIMAX / FALLOUT / BREATHER`.
`advise_cut` returns a `{should_cut, murch_score, reason}`
dict — climax beats lower the cut threshold to 0.35, setup
and breather beats raise it to 0.65, and any shot that
overruns the profile's max is force-cut.

## Integration

The previous batch published render-intent dicts; this batch
publishes performance-intent and shot-intent dicts that feed
into the same Live Link bus.

End-to-end Maat boss intro:

1. **Scene engine** raises `boss_intro` for Maat in Bastok
   Metalworks. `voice_pipeline.generate_for_agent("maat")`
   produces the WAV; `voiced_cutscene` schedules the line.
2. **performance_capture** picks `optitrack_prime_41` for
   Maat's body + `live_link_face` for facial. The actor (or
   the offline MetaHuman Animator footage) feeds Live Link.
3. **metahuman_driver** looks up Maat's binding — `Hume_M`
   skeleton, `MH_M_Hume_Maat` face blueprint, `maat_doublet`
   costume rig — and applies emotion `ANGRY` at intensity
   0.9, returning the 52-blendshape weight set.
4. **dialogue_lipsync** queues the Higgs WAV with engine
   `audio2face` (hero override). After analyze + bake, UE5
   has a per-frame viseme curve.
5. **director_ai** asks for `(EMOTIONAL_BEAT, MEDIUM,
   focus_targets=2)` and gets `[CLOSE_UP 0.95, EXTREME_CLOSE_UP
   0.9, OVER_THE_SHOULDER 0.85]`. The cinematographer picks
   CU; `cinematic_camera.select_profile("arri_alexa_35")` +
   `lens_optics.select_lens("cooke_s4_50mm")` configure the
   rig. `film_grade.apply_lut("kodak_vision3_500t")` warms
   the tungsten interior.
6. **scene_pacing** registers a 4-beat sequence (SETUP 5s,
   ESCALATION 8s, CLIMAX 4s, FALLOUT 6s) and asks
   `advise_cut` every frame. Murch sum 0.6 + climax beat →
   cut at frame X. `render_queue.queue_render` emits the
   ProRes 4444 master.

## Open-Source Stack

* Live Link Face (iOS, free)
* MetaHuman Animator (UE5 plugin, free)
* MetaHuman Creator (Epic, free for Unreal use under the
  Unreal Engine EULA — see license note below)
* Rhubarb Lipsync (MIT)
* OpenSeeFace (BSD; alternate facial fallback)
* Audio2Face (NVIDIA Omniverse Audio2Face, free for
  individual use; Enterprise tier for studios)
* Oculus Lipsync SDK (Meta, free with attribution)
* Rokoko Studio (commercial; Studio Lite free tier)
* OptiTrack Motive (commercial)
* Faceware Studio (commercial)
* CMU Sphinx / wav2vec2 for offline phoneme alignment

The server modules in this batch don't ship with any of the
above — they publish device intents and structured frames
that the UE5 plugin layer maps to the actual SDK calls. That
keeps the Demoncore server a pure data + logic surface that
runs anywhere Python 3.10 runs.

## MetaHuman License Note

MetaHuman avatars are governed by the Unreal Engine EULA
plus the MetaHuman Content License. In short: MetaHuman
characters generated via MetaHuman Creator can be used in
any Unreal Engine project (including commercial projects)
provided the final renderer is Unreal Engine. They cannot be
ripped to other engines. Demoncore complies trivially —
every pixel is rendered in UE5. Custom face blueprints and
costume rigs we author ourselves are unencumbered; they
slot into the MetaHuman face control rig via the standard
DNA file format.

## Cross-References

* `CINEMATIC_LIVE_ACTION.md` — the previous batch (camera /
  lens / grade / atmospherics / render queue)
* `CINEMATIC_GRAMMAR.md` — shot-grammar rule library
  encoded into `director_ai`
* `LAYERED_COMPOSITION.md` — staging rules feeding focus-
  target refinement
* `BOSS_GRAMMAR.md` — boss-fight beat templates feeding
  `scene_pacing`
* `COMBAT_TEMPO.md` — per-encounter pacing profile sources
* `VOICE_PIPELINE.md` — Higgs Audio v2 voice generation
  (upstream of `dialogue_lipsync`)
* `CINEMATICS.md` / `CINEMATICS_VIRTUAL_PROD.md` — the
  cutscene scheduler that owns the timeline these modules
  feed.

## What's Next

The visible-image ceiling was hit last batch. The visible-
**performance** ceiling is hit by this one. From here the
inflection is content (more avatar bindings, more emotions,
more director rules) and tighter per-NPC overrides — not new
architecture.
