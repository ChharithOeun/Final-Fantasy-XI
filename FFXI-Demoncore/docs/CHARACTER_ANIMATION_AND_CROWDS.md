# Character Animation + Crowd Life

## Vision

The previous batch built the seamless world: forty-one zones,
no load screens, the camera flying from Bastok Mines to
Windurst Woods in five minutes without ever fading to black.
Beautiful — but the people in those zones still moved like
mannequins. Idle loops on a one-second clock. Eyes that
never blinked. Capes that never caught the wind. NPCs that
stared straight through the player.

This batch is the character-animation + crowd-life layer.
Five modules that turn the live-action zones into *living*
places — vendors who fidget while they haggle, guards
whose eyes track you across the plaza, kids who sidle
behind their mother's skirt as you walk past, robes that
ripple when the Pashhow wind picks up, hair that catches
the Bastok furnace draft. The kind of detail that, when
done right, no one notices because it just looks alive —
and when done wrong, every frame screams "this is a
videogame."

## The Five Modules

### 1. character_animation/

The catalog of animation clips per (kind, race, gender).
Twenty-five clip kinds — IDLE, WALK, RUN, SPRINT, SIT,
LEAN, TALK_HEAD, GESTURE_POINT, GESTURE_BECKON,
GESTURE_BOW, GESTURE_DISMISS, REACTION_SURPRISE,
REACTION_LAUGH, REACTION_ANGER, REACTION_FEAR,
COMBAT_STANCE, CAST_BEGIN, CAST_RELEASE, HIT_FLINCH,
KO_FALL, EMOTE_WAVE, EMOTE_NOD, EMOTE_HEADSHAKE,
EMOTE_SHRUG, EMOTE_FACEPALM. Five races × two genders ×
twenty-five kinds = 250 possible clips; we ship ~50
representative ones and let the lookup discipline cover
the rest. ``best_match(kind, race, gender)`` falls back
through (race, opposite gender) -> (HUME, gender) ->
(HUME, opposite gender), so a half-finished race never
crashes the game; it just borrows hume animation until
the riggers catch up. Blending rules say which kinds can
layer over which — TALK_HEAD (face-only) over GESTURE_POINT
(upper-body) over WALK (root motion) is three layers; but
COMBAT_STANCE blocks WALK because the lower body is
locked. ``emotion_to_anim()`` maps mood tags from
metahuman_driver to the natural reaction animation.
``idle_variation_for()`` round-robins through the
registered IDLE clips so a row of guards doesn't all
breathe in lockstep.

### 2. cloth_hair_sim/

Real-time cloth + groom physics profiles. Nine cloth
classes — heavy priest robe, light merchant tunic, flowing
hero cloak, chainmail, plate-skirted armor, tabard,
leather pants, formal dress, peasant skirt — each tuned
with a mass / stiffness / damping / wind-coupling /
solver-iteration triple. Eleven groom kinds covering all
five races' signature looks: short_neat, mid_loose,
long_flowing (300 000 strands at LOD 0), braided, shaved,
bald, horn_carved (galka), mithra_tail, taru_pigtail,
elvaan_long, topknot. Wind coupling reads
atmospheric_render's per-zone density: a 0.6 density
overcast Pashhow Marshlands ruffles cloaks much harder
than 0.05 density bright Bastok Markets daylight. LOD:
strands at <6 m, hair cards at <40 m, single capsule
beyond. Edge cases: KO/dead state freezes the cloth
solver and holds the death pose; sleeping NPCs pause the
sim to save cycles. NVIDIA Flow / MagicaCloth UE5 /
Bullet Cloth do the actual physics in production; this
module is the catalog + the dispatch policy.

### 3. eye_animation/

Microsaccades, blinks, look-at, pupils. The cheapest
"is this character alive?" tell — and the most expensive
to fake. Per-mood blink rates: CALM 17/min, FOCUSED
12/min, ANXIOUS 30/min, IN_COMBAT 8/min (suppressed —
combat focus), DEAD 0/min. Pupil diameter as a function
of scene illuminance: bright sun (~80 000 lux) constricts
to 2 mm, dim cave (~5 lux) opens to 7 mm; ANXIOUS mood
adds a 1 mm sympathetic dilation spike on top. Look-at
targeting: when the player enters the engagement radius
(6 m default), the NPC sets the player as their look
target, holds for 2-4 seconds, then darts away — the
social-natural glance shape. Microsaccades fire once or
twice a second at 0.1-1° amplitude. Tear sim: emotional
beats with intent_tag WEARY / AFRAID / TENDER push
tear_amount toward 1.0; everything else decays it. The
performance_direction system reads tear_amount on
big-emotion shots and asks the renderer for a wet
eyeline.

### 4. crowd_director/

Ambient crowd life. Ten archetypes — VENDOR_BUSY,
CIVILIAN_PURPOSEFUL, GUARD_PATROL, CONVERSATION_POD_MEMBER,
IDLER_LEAN, IDLER_SIT, IDLER_SMOKE, IDLER_DRINK,
CHILD_PLAY, MERCHANT_HAGGLE — each with a baked greet
policy (vendors wave, guards stay stoic, kids sidle
away). ``populate_zone(zone_id, density_target)`` spawns
or despawns agents until the zone hits its target — Bastok
Markets 40, North Gustaberg 8, Crawler's Nest 0. Anti-
clumping: agents below 1.2 m social distance get nudged
apart every tick (0.5 m for conversation pod members
because pod members stand close). Player awareness: when
the player walks within 4 m, agents flip
``is_player_aware`` and (if an EyeAnimationSystem is
wired in) hand off eye contact via ``set_look_target``.
Conversation pods of 2-4 NPCs spawn with cross-linked
``conversation_partner_ids``, animate dialogue_lipsync
chatter for ~30 s, then break apart cleanly when the
lifetime expires.

### 5. animation_retargeting/

Mocap retargeting between skeletons. Body capture from
Rokoko, OptiTrack Prime, Mixamo, MetaHuman default, or
the FFXI retail human rig lands on a generic-human
skeleton. FFXI's five races have wildly different
proportions: galka shoulders +30 %, mithra hip sway +20 %,
taru head 1.6× body and arms 0.7×, elvaan +15 % spine,
mithra +tail bones. ``standard_body_mappings(target)``
builds the per-target mapping table baked from the race
scale tables; a hand-authored ``RetargetMap`` can
override anything. ``retarget_clip(clip_uri, source,
target)`` returns a stub URI for the retargeted clip.
``validate_retarget`` enforces the body / face source
distinction (face capture cannot retarget to a body
target; the kinds are not interchangeable) and that all
mandatory bones are present in the map. IK rules: foot-
locking on by default, hand-prop attachment sockets per
prop kind (hammer / sword / staff / cup at HAND_R_PROP;
scroll / lantern / book / bow at HAND_L_PROP).

## Integration

* ``character_animation.AnimationSystem.emotion_to_anim()``
  consumes ``metahuman_driver.Emotion`` tags ("HAPPY",
  "AFRAID", "ANGRY") and returns the animation kind for
  the natural reaction. The director_ai picks the shot;
  performance_capture drives the face; this module picks
  the body.
* ``cloth_hair_sim.apply_wind(zone_id, wind_strength)`` is
  fed by ``atmospheric_render.density`` per zone, so the
  Pashhow Marshlands overcast (high density) makes
  cloaks ruffle harder than the bright Bastok daylight
  (low density). ``zone_lighting_atlas`` already records
  the per-zone density floor; the cloth simulator just
  reads it.
* ``eye_animation.update(npc_id, dt, scene_lux, mood)``
  reads scene_lux from ``zone_lighting_atlas`` (key fill
  intensity in LUX) and mood from
  ``performance_direction.intent_tag``. The result is a
  pupil that's correctly sized for the scene the
  director shot.
* ``crowd_director.tick`` accepts an EyeAnimationSystem as
  a dependency injection. When an agent enters the
  player-aware radius the director hands off the eye
  contact to the eye system; the eye system runs the
  hold timer and dart-away. Two systems, one
  hand-shake.
* ``crowd_director.spawn_conversation_pod`` produces NPCs
  that ``dialogue_lipsync`` can animate as a conversation
  group (the pod members already have
  ``conversation_partner_ids`` cross-linked).
* ``animation_retargeting`` is the asset pipeline upstream
  of ``character_animation`` — clips authored against a
  Mixamo or Rokoko skeleton get retargeted into the
  per-race FFXI skeleton before they're registered into
  the AnimationSystem.
* ``showcase_choreography`` beat 4 of the Bastok Markets
  walkthrough already calls for "vendor waves; player
  nods" — that beat now has a real implementation:
  crowd_director picks the vendor, character_animation
  picks the EMOTE_WAVE clip, animation_retargeting maps
  it onto the vendor's race, eye_animation runs the
  contact hold + dart-away.

## Open-source toolchain

* **Mixamo** (free Adobe service) for body mocap library
  — ~2500 clips, source skeleton already supported.
* **Cascadeur free tier** for keyframe physics-aware
  cleanup; non-commercial use covers the demo build.
* **MagicaCloth UE5** (open-source plugin) for the cloth
  solver in editor.
* **Bullet Cloth** (BSD 3-clause) for headless server-side
  state stepping.
* **NVIDIA Flow** (open-source under the BSD-style NVIDIA
  Software License) for the volumetric wind field that
  drives the atmospheric_render -> cloth_hair_sim wind
  coupling.
* **Live Link Face** (Epic, free) for ARKit face capture.
* **Rokoko Studio Live** (free tier) for body mocap; the
  Rokoko Body 82 source skeleton is supported.

## Per-race animation library targets

| Race | Gender | Target clip count (M1) | Notes |
|------|--------|------------------------|-------|
| HUME | M / F | 25 each | the baseline; everything falls back here |
| ELVAAN | M / F | 20 each | longer stride, taller posture |
| TARUTARU | M / F | 20 each | head-bobbing waddle, exaggerated gestures |
| MITHRA | F | 25 | prowl gait, +tail animation pass |
| GALKA | M | 25 | heavy stomp, +30 % shoulder swing |

M1 = milestone 1, ~250 clips total, covers IDLE / WALK /
TALK_HEAD / REACTION_SURPRISE / GESTURE_BOW / EMOTE_WAVE /
COMBAT_STANCE / HIT_FLINCH / KO_FALL across every race
and gender. M2 doubles that with the full reaction +
cast set.

## The cross-module flow — a vendor in Bastok Markets

1. Producer calls
   ``crowd_director.populate_zone("bastok_markets", 40)``.
   Forty CrowdAgents spawn with archetypes weighted toward
   VENDOR_BUSY + MERCHANT_HAGGLE.
2. ``cloth_hair_sim.apply_wind("bastok_markets", 0.05)``
   bakes the bright-daylight low-wind setting from
   atmospheric_render. Vendor's tabard sits relatively
   still.
3. Player walks within 4 m of vendor. ``crowd_director.tick``
   marks the agent as player-aware, calls
   ``eye_animation.set_look_target(vendor.npc_id, "player")``.
4. ``eye_animation.update`` runs at 60 Hz: vendor's gaze
   tracks the player, blink rate 17/min (CALM mood),
   pupil 4 mm at the noon-Bastok scene_lux. Hold timer
   accumulates.
5. ``character_animation.emotion_to_anim("HAPPY")`` returns
   ``EMOTION_WAVE``; the vendor's clip gets selected via
   ``best_match(EMOTE_WAVE, race=HUME, gender=MALE)``.
   Body capture was authored on Mixamo;
   ``animation_retargeting.retarget_clip`` mapped it onto
   the FFXI HUME M skeleton at registration time.
6. After 3.2 s the eye hold timer expires; the vendor
   darts gaze toward the next pedestrian. Gesture
   completes; vendor returns to IDLE — but
   ``idle_variation_for`` picks idle_variant_b this time,
   not the same clip as last cycle.
7. Wind picks up (zone weather changes); cloth_hair_sim
   re-bakes the wind to 0.4. The vendor's tabard flicks
   visibly.

That's seven steps, all from public surfaces, all
deterministic, all unit-testable. The producer's dashboard
sees one number — "ambient life: 215 tests passing" — and
the live-action zones get their last layer of breath.

## Three design hinges

1. **THE FALLBACK CHAIN IS THE FEATURE.** We will never
   have all 250 clips authored on day one. The
   ``best_match`` chain — exact -> same race opposite
   gender -> HUME same gender -> HUME any gender — means
   the engine *never* crashes on a missing clip. A
   half-finished mithra race plays hume animations until
   the riggers catch up. Producers can ship intermediate
   builds; QA never sees a t-pose.

2. **EYES ARE THE SINGLE BIGGEST UPGRADE.** Of the five
   modules, eye_animation is the one a casual viewer
   notices most and codifies least. A character whose
   eyes don't track the player reads as dead from across
   the plaza, regardless of how good the cloth or
   gesture is. The blink-rate-by-mood + pupil-by-illum +
   look-at-with-dart-away triple is the absolute minimum
   "this NPC sees me" baseline. It's also dirt cheap —
   four floats per agent updated at 60 Hz.

3. **CROWD DIRECTOR IS A POLICY ENGINE, NOT A SOLVER.**
   It doesn't simulate physics. It makes high-level
   decisions: how many agents per zone, which archetype
   gets which greet policy, when to spawn a conversation
   pod, when to break it apart. The actual movement,
   cloth, hair, eyes are in the four other modules. That
   separation lets us tune the *crowd feel* (more
   children in Windurst, more guards in Bastok) without
   touching the simulation, and tune the *simulation
   fidelity* (groom strand count, blink rate) without
   touching the crowd policy.

The previous batch made the world seamless. This batch
makes it alive. Together: a five-minute camera move
from Bastok Mines to Windurst Woods, no load screens, no
wax dummies, just three nations of breathing characters
going about their day.
