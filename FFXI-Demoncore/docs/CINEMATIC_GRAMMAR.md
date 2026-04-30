# CINEMATIC_GRAMMAR.md

How Demoncore looks like a film. The Mandalorian dream made
concrete: every cutscene shot on the StageCraft principles, with
real-time lighting, virtual camera operated by phone, and shots
composed for the screen, not for a fixed in-engine camera.

This doc is the contract for cinematics across the project. It
sits alongside `CINEMATICS.md` and `CINEMATICS_VIRTUAL_PROD.md`
(both already authored) and pins down the **practical UE5 setup
steps** so a director can sit down, plug in their iPhone, and
shoot a boss intro in 30 minutes.

---

## The five-shot grammar

Every Demoncore cutscene uses one of five shot types. Camera
operators learn the language; they execute it the same way every
time. Think DP shorthand for a cinematographer: ECU, MS, OS,
WS, dolly.

### 1. ESTABLISHING (4-6 seconds)
Wide shot showing the location. Slow dolly-in. Camera held by the
operator (Live Link from phone). Music swells. No dialogue.

Use for: zone-entry cutscenes (player walks into Bastok at the
opening), boss-arena reveals (the camera shows the room before
the boss appears).

### 2. HERO ENTRY (3-5 seconds)
Camera tracks the boss's silhouette emerging from environment.
Composed low-angle (camera at boss waist level looking up).
Dolly stops as the boss takes their first breath / pose.

Use for: every Tier-3 boss entrance per `BOSS_GRAMMAR.md` Layer 5.

### 3. EXCHANGE (5-8 seconds)
Two-shot: boss in foreground, party in background (or vice versa).
Camera at chest level. No dolly; held shot. The boss delivers
their voice-cloned intro line. The party hears it positionally.

Use for: pre-fight banter ("So. You're it for today."), mid-fight
phase-transition lines ("ENOUGH PLAYING."), defeat dialogue ("...
Excellent. You've earned the right.").

### 4. CHAOS (variable, follows action)
Handheld camera tracks combat. The operator (using their phone's
Live Link) actually walks/spins around the action. Editor can
later cut between multiple operators' takes. The look: ALWAYS
slightly off-balance, small involuntary motion, quick reframings
when something dramatic happens.

Use for: skillchain Detonation moments (camera whips toward the
target halo), ultimate-attack telegraphs (camera pulls back to
show the AOE shape), party wipe (camera tilts up to the sky as
the screen darkens).

### 5. AFTERMATH (8-12 seconds)
Slow tracking shot. Camera glides across the aftermath. The
defeated boss in foreground; the party in mid-ground; the world
in background. Music fades. Voice-cloned soliloquy if the boss
has one.

Use for: Tier-3 boss defeats, end-of-Genkai test, story-mission
endings.

---

## The virtual-camera setup (StageCraft adaptation)

UE5 supports phone-as-camera natively via the **VirtualCamera**
plugin (already enabled in `INSTALL_DEMONCORE_PLUGINS.bat`). The
Mandalorian's StageCraft uses a high-end VR-tracker rig; we use a
phone running the UE5 VCam app via Live Link. **Same workflow,
1000x cheaper.**

### Hardware
- iPhone 12+ or Android with ARCore (Live Link compatible)
- USB cable (or wireless via 5GHz network for studio use)
- Optional: a small handheld rig with phone mount + camera-shaped
  body (so the operator's grip translates into natural shots)

### UE5 setup (one-time per project)
1. **Enable plugins** (already done): Live Link, VirtualCamera,
   VPUtilities, Take Recorder
2. **Create a VirtualCamera Pawn** in the demoncore project at
   `/Game/Demoncore/Cinematics/BP_VCamera`
3. **Configure Live Link Source**: phone connects via the UE5
   VCam app, source name "iPhone_Director"
4. **Bind the VCamera to the Live Link source** so phone movement
   drives the camera transform
5. **Configure Take Recorder** to save phone-driven takes as
   Sequencer assets

### Per-scene workflow
1. Director opens UE5, loads the boss arena level
2. Director takes phone, opens UE5 VCam app, connects to PC
3. Director walks/turns physically — UE5 viewport updates in real
   time with the phone's perspective
4. Director presses record — Take Recorder captures phone movement
   as a Sequencer track
5. Multiple takes captured back-to-back; editor picks the best in
   Sequencer
6. Final shot is a Sequencer asset that plays back the recorded
   camera moves on cutscene trigger

Total setup time on a fresh PC: ~10 minutes one time. Per-scene
shoot: ~5-15 minutes for a 30-second cutscene including 3-5
takes.

---

## Real-time lighting integration

The real magic of StageCraft is the lit volume — the LED wall
that lights the actors AND provides the visible environment.
We don't have an LED wall, but UE5's Lumen + the layered scene
system per `LAYERED_COMPOSITION.md` deliver something
functionally similar:

- **Layer 1 (Sky)** drives the global lighting per
  `bastok_layered_scene.py`. SkyAtmosphere, SkyLight, sun
  rotation. Time-of-day and weather both affect the lit
  environment.
- **PostProcessVolumes** in each cinematic location can dramatize
  the lighting per-shot. A "Maat tea-set entrance" PPV pushes
  warmth +20%, contrast +10%, slight orange tint. A defeat
  cinematic PPV pulls saturation -30%, slight desaturated cool
  shift.
- **Lumen GI** ensures every camera angle is correctly lit
  without manual baking. The director can frame the same shot
  from 5 different angles in 5 minutes; each looks correct.

The Mandalorian principle: **light the environment first, then
shoot anywhere in it.** Demoncore inherits this exactly.

---

## Sequencer template per boss-recipe Layer 5

Per `BOSS_GRAMMAR.md`, every boss has 4 cinematic moments:
entrance, intro line, defeat, optional aftermath. We provide
**Sequencer template assets** that authors reuse across bosses:

```
/Game/Demoncore/Cinematics/Templates/
  ST_Entrance_Establishing       — establishing + hero-entry combo
  ST_Entrance_DirectReveal       — quick boss reveal (mid-tier)
  ST_PhaseTransition             — short cut for visible armor-drop
  ST_Defeat_PlayerWon            — slow-clap aftermath template
  ST_Defeat_PlayerLost           — boss head-shake / sit-back-down
  ST_Aftermath_BossImpressed     — Maat-style "I haven't seen Light in years"
  ST_Aftermath_Lore              — multi-line soliloquy template
```

Each template has:
- 5-8 keyframed camera tracks (using the 5-shot grammar)
- Audio bus for boss voice-cloned line
- Music cue track (ACE-Step-generated theme per zone)
- Particle/post-process tracks
- Trigger event tracks for game-state changes

To author a new boss cinematic: clone the template, swap the
camera target actor, swap the voice-cloned audio file, swap the
music cue. ~30 minutes per boss. ~50 cinematics across the world
= ~25 hours of cinematic authoring after the templates exist.

---

## Camera language for combat (the ChaosMode shot)

During *active* combat, the camera doesn't replay a pre-recorded
Sequencer. It runs real-time per the `ChaosMode` operator script:

- Default: third-person camera follows the player (canonical FFXI)
- On **skillchain detonation** (per `SKILLCHAIN_SYSTEM.md`):
  brief whip toward the halo target (50ms), 200ms pause, return
  to follow
- On **Magic Burst landed**: 100ms zoom-in toward the target,
  300ms pause, return
- On **boss phase transition**: 1-second slow-mo + camera tilt
  during the visible armor drop
- On **Intervention MB succeeded**: 200ms pulse toward the
  intervening healer (the heroic-save moment is *seen*)
- On **player wipe**: camera tilts up to the sky over 1.5s as
  the screen fades

These are auto-driven by the LSB combat broker pushing
"`camera_event`" messages. No director needed during play. The
Mandalorian style for combat is automated; only set-pieces need
the human operator.

---

## Audio-led editing

`AUDIBLE_CALLOUTS.md` says combat sound is the UI. Cinematics
treat it the same way: **shots are cut to the audio**. The voice-
cloned "Skillchain open!" call on the soundtrack triggers a
camera whip. The boss's "ENOUGH PLAYING." line gets a wide-shot
hold for 1.5 seconds before any other camera move. The party's
panicked "Heal! Heal!" calls cut to a tight on the WHM mid-cast.

This is film grammar, and Demoncore uses it because every voice
event the LSB combat broker emits has a precise timestamp. The
camera operator script reads the timeline of events and selects
camera moves accordingly.

---

## Where the cinematics live in the project

```
/Game/Demoncore/Cinematics/
  Templates/                     — reusable Sequencer templates (above)
  Bastok/
    MaatEntrance.uasset
    MaatDefeat_PlayerWon.uasset
    MaatAftermath_LightChain.uasset
    GoblinSmithy_TutorialBoss.uasset (lvl 5 boss recipe)
  Sandy/
    CurillaEntrance.uasset
    ...
  Windy/
    KerutotoEntrance.uasset
    ...
  Story/
    OpeningCinematic.uasset      — first 3 minutes of player life
    GenkaiTransition.uasset
    EndOfChapter1.uasset
```

Each `.uasset` is a Sequencer asset that plays back when its
trigger fires (boss intro, boss defeat, player level threshold,
story progression, etc).

---

## Status

- [x] Design doc (this file)
- [ ] BP_VCamera Pawn in /Game/Demoncore/Cinematics/
- [ ] Live Link source configuration documentation
- [ ] 7 Sequencer template assets
- [ ] First cinematic authored: Maat entrance (using templates)
- [ ] First cinematic authored: Maat defeat (using templates)
- [ ] ChaosMode camera operator script (BP_ChaosCameraDirector)
- [ ] LSB combat broker → camera_event message format
- [ ] First playtest: full Maat fight with cinematics + ChaosMode
- [ ] Phone-grip handheld rig assembly notes for the team
