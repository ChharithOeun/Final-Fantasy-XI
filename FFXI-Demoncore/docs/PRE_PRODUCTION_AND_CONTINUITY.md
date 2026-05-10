# PRE-PRODUCTION & CONTINUITY

The five preceding batches built the *cinematic execution* layer
of FFXI Demoncore: cameras, lenses, grade, atmospherics, render
queue, mocap, MetaHuman, lipsync, AI director, Murch pacing, and
the entire voice-actor pipeline including AI-to-human hot-swap.

What was missing was the *planning layer* — the pre-production
work a real production does before a single frame gets shot, and
the continuity oversight that catches breaks the cameras would
otherwise capture and ship.

This batch closes that gap. The result is a complete production
loop: AI plot generator and dynamic quest gen produce the story
beats, the screenplay engine formalises them as shootable script,
the storyboard panel layer plans the imagery, the shot list
schedules the shoot, the previs engine rehearses it in low-fi,
the cinematic / performance / voice batches execute it, and the
continuity supervisor stands behind the camera flagging anything
that breaks across cuts.

## The five modules

### `server/screenplay_engine/` — Industry-standard screenplay format
Sluglines (`INT. BASTOK MARKETS - DAY`), action, character cues
(uppercased), dialogue, parentheticals (`(weary)`), transitions
(`CUT TO:`, `FADE OUT.`), shot directions (`!ANGLE ON CURILLA`),
and dual-dialogue for two characters speaking simultaneously.
Sluglines parse into kind/location/time. Pages map to runtime at
the WGA-standard rate (1 page ≈ 1 minute), with action weighted
~36 words/page and dialogue ~25 words/page. Revisions cycle
through the WGA colour order (white → blue → pink → yellow →
green → goldenrod → buff → salmon → cherry) with A-page line
labels for inserts. Validation catches malformed sequences:
DIALOGUE has to follow CHARACTER (or PARENTHETICAL); CHARACTER
cues must be uppercased; dual-dialogue must name both speakers.
Fountain markdown — the open-source plain-text screenplay format
used by Highland, Slugline, Beat, Trelby, Logline, FadeIn — is
both an export and import surface. 38 tests.

### `server/storyboard_panels/` — Per-shot storyboard
Each Panel carries panel id, scene id, shot index, aspect ratio
(1.33 / 1.78 / 1.85 / 2.00 / 2.39 / 0.5625 vertical), framing
(WIDE / FULL / MEDIUM / COWBOY / CLOSE / EXTREME_CLOSE / TWO_SHOT
/ OTS / INSERT), camera move (14 standard moves), lens hint,
focus target, optional dialogue excerpt, sound cue, eye-trace
position, and 180°-axis side. StoryboardSheet aggregates panels
for a scene under a target page-budget. The continuity check
between consecutive panels catches three common breaks the
audience will feel: 180° axis jumps without an INSERT/ECU bridge
(WARNING), eye-trace breaks where the viewer's gaze snaps from
left to right of frame (NOTE), and lens jumps that more than
triple the focal length without an intermediate frame size (NOTE).
30 tests.

### `server/shot_list/` — Production shot list
The Production Strip Board in code. Each row is one shot the
crew has to capture: slate (`37A`), description, lens, location,
time-of-day (DAWN / DAY / GOLDEN_HOUR / DUSK / NIGHT /
MAGIC_HOUR), talent ids, props required, vfx flag, audio flag,
mocap flag, expected setup minutes, and current status (PLANNED
/ SCHEDULED / SHOT / HOLDS / OMITTED). Grouping by location and
time-of-day minimises crew moves. Per-day call sheets aggregate
talent-required and total-setup-minutes. Equipment pull lists
collect every lens needed plus audio/vfx/mocap booleans. The
critical-path walker counts transitive downstream blockers and
ranks the shots that gate the most work. 28 tests.

### `server/previs_engine/` — Pre-visualisation
The low-fi camera blocking and timing rehearsal. Each PrevisShot
has a duration, a sparse keyframed camera path (time → position
→ look-at → lens), sparse keyframed talent blocking (time → npc
→ position → action tag), an optional sound track, and a
low-poly asset list. PrevisSequences chain shots and gate
transitions. The interpolator simulates the camera at any time
inside any shot for spot-checking. Six export targets cover the
industry pipelines: UE5 Sequencer USD, Maya .ma, Blender .blend
(open source), and ShotGrid / ftrack / Kitsu playblasts for
producer review. 31 tests.

### `server/continuity_supervisor/` — Visual continuity tracker
The script-supervisor / continuity-script in code. Per shot, per
character, snapshot the visible state: wardrobe, props in hand,
blood on face locations, weather, time of day, hair state (clean
/ messy / wet / bloodied), wounds, accessories, camera position.
On the next shot the supervisor compares the new snapshot to the
previous one for the same character and flags discrepancies at
three severities: NOTE (cosmetic — accessory swap), WARNING
(audience-visible — wardrobe change, blood movement, weather
shift), ERROR (breaks scene logic — prop teleport, wound
healing). `reset_for(scene_id, character_id)` is the hook for
script-intended changes (costume change for a bath scene). The
sequence-level report rolls up worst severity for greenlight
gating, plus a PDF-stub manifest the ftrack / Frame.io plugin
turns into the actual deliverable. 30 tests.

## Integration with prior batches

The pre-production stack hands clean inputs to every cinematic
module that came before:

- **`ai_plot_generator` → `screenplay_engine`**. The plot
  generator's beat-list becomes scenes; each beat becomes
  ACTION + CHARACTER + DIALOGUE + parenthetical elements. The
  screenplay engine validates the result and computes runtime
  for budget gating.
- **`dynamic_quest_gen` → `shot_list`**. A generated quest
  yields a list of cinematic moments; each moment becomes a
  ShotRow with talent and location pulled from the quest's
  npc/zone metadata.
- **`screenplay_engine` → `storyboard_panels`**. Each scene's
  ordered elements decompose into shot indices; the storyboard
  layer plans framing, lens, and camera move per shot, and
  carries the dialogue excerpt forward so the storyboard reads
  as a comic-book version of the script.
- **`storyboard_panels` → `previs_engine`**. The panel's lens
  hint becomes a CameraKey lens; the framing implies camera
  distance; the action description seeds talent blocking
  keyframes.
- **`shot_list` → `voice_session_studio`**. Talent ids on a
  shot row drive booking — a shot needing Curilla on day 12
  books a session on day 11 to record her lines for it.
- **`screenplay_engine` → `voice_performance_direction`**. Each
  DIALOGUE element with a parenthetical tag (`(weary)`,
  `(menacing)`) maps directly to an Intent on the per-line
  Direction the AI engine and the human VA both consume.
- **`previs_engine` → `cinematic_camera` + `lens_optics`**.
  When shooting starts, the previs camera path is loaded into
  Sequencer; cinematic_camera picks the matching real-camera
  body; lens_optics matches the focal length to a real lens.
- **`previs_engine` → `performance_capture`**. The talent
  blocking keys become mocap take targets — the actor on the
  volume hits the marks the previs already laid down.
- **`continuity_supervisor` ← every shoot**. Every shot
  delivered via voice_session_studio or performance_capture
  registers a snapshot. The supervisor checks against the
  previous snapshot for the same character. Issues feed the
  director_ai's score for "should I take another take" plus the
  ftrack / Kitsu producer review.
- **`director_ai` ← `screenplay_engine`**. The director's
  decision matrix already keys on (scene_kind, tempo); the
  screenplay's slugline + dialogue mix gives the director the
  scene_kind classification automatically (interior dialogue
  with two character cues → SceneKind.DIALOGUE).
- **`scene_pacing` ← `screenplay_engine`**. The Murch
  rule-of-six pacing engine wants per-element runtimes. The
  screenplay engine's `_element_pages` is exactly the input it
  needs.

## Open-source toolchain

Every module is designed to round-trip with the open-source
production stack so the project never has to license a
proprietary tool:

- **Fountain** (`fountain.io`) for screenplays. Highland 2,
  Slugline 3, Beat (free, macOS), Trelby (cross-platform),
  Logline, FadeIn — every modern screenwriting app reads and
  writes Fountain. `to_fountain` and `from_fountain` are the
  hand-off.
- **Storyboarder** (`wonderunit.com/storyboarder`) for panels.
  Free, exports Fountain + storyboard PDF.
- **Blender 4.x** (`blender.org`) for previs and final
  animation. Free, GPLv3.
- **Unreal Engine 5 + Sequencer** for live cinematics, with
  USD as the interchange.
- **OpenTimelineIO** for timeline export — bridges Blender,
  Maya, Premiere, Resolve.
- **Krita / Inkscape / GIMP** for storyboard panel art.
- **ftrack** (free for ≤10 users), **Kitsu** (open-source
  CG-Wire), **Tactic** (open-source Southpaw) as ShotGrid
  alternatives. Their playblast and continuity-report APIs
  consume the manifest stubs `previs_engine.export_for` and
  `continuity_supervisor.export_pdf_stub` produce.
- **Whisper** (`openai/whisper`, MIT) for line transcription
  during continuity checks.
- **Reaper** for audio editing (cheap commercial), **Audacity**
  (open-source) as a fallback.

## Vision

A real cinematic production runs on three layers: a *story
layer* that decides what happens, an *execution layer* that
captures it, and an *oversight layer* that catches mistakes.
The cinematic + performance + voice batches built a world-class
execution layer. The plot generator and dynamic quest gen built
the story layer. This batch builds the oversight layer and the
formal hand-off between story and execution. From here, the AI
can run the entire pipeline — generate a plot, format it as a
screenplay, board it, schedule the shoot, previs it, capture
it, voice it, and ship it with a continuity report attached —
the way a real studio runs, just compressed into the Demoncore
server's daily build.

The point is repeatability. A pipeline that catches its own
breaks is a pipeline that scales: the AI plot generator can
churn out a hundred quests this week and the continuity
supervisor will tell us which two need a re-take before they
ship.
