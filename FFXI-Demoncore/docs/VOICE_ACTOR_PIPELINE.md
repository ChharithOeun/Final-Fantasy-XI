# Voice Actor Pipeline

**Vision: AI today, real humans tomorrow, no rework on the day we swap.**

FFXI Demoncore ships voiced from day one. The first iteration is
entirely AI-cloned — `voice_pipeline` drives Higgs Audio v2 against
a 30-second reference WAV per character. That gets the project on
its feet. But Demoncore is a long-tail project; over its life we
expect to upgrade specific roles to real, contracted voice actors,
one role at a time, line by line. This pipeline is the layer that
makes the upgrade non-disruptive: `voiced_cutscene` and
`dialogue_lipsync` never have to know whether Curilla is being
spoken by Higgs or by Jane the human VA. They ask the registry,
and the registry tells them what's current. That's the whole game.

## The five modules

### `voice_role_registry`
The casting bible. 30+ named FFXI hero / villain / mentor / boss
roles — Curilla, Volker, Ayame, Maat, Trion, Nanaa Mihgo, Aldo,
Cid, Prishe, Selh'teus, Tenzen, Mihli Aliapoh, Lion, Ulmia,
Esha'ntarl, Eald'narche, Atomos, the Shadow Lord, Shantotto, the
five nation rulers, the five Crystal Warrior heroes from the
canonical BCNM, plus a generic narrator slot. Each role carries a
casting brief (pitch, accent, vibe, age, gender, languages), a
rate card, and a `Provisioning` field that names who currently
voices the role: an AI engine, a human VA + contract id, or
VACANT. `provision_with_ai`, `provision_with_human`, `vacate` are
the three knobs every other module hits. `provisioning_summary()`
returns a count dict the dashboard renders.

### `voice_audition_pipeline`
The funnel for real VAs. Producer opens an audition for a role
with an `AuditionPacket` (3-5 canon sample lines, 1 wild line in
character, performance notes from the director). VAs submit
demos with a `RecordingSpec` (≥48k/24bit, ≥3s room tone, EBU R128
loudness window of -23 to -16 LUFS); spec is enforced on submit
so we never burn screener time on bad audio. Lifecycle is
SUBMITTED → SCREENED → CALLBACK → BOOKED, with a terminal REJECTED
branch off any non-terminal state. Booked submissions hand off to
`voice_role_registry.provision_with_human(role_id, va_name,
contract_id)`. Peer flagging exists but is advisory — flags do
not veto, they're a signal.

### `voice_session_studio`
Six studios — `home_booth` (Source-Connect remote), Burbank
Voiceworks (LA), City NYC, AIR Studios (London), AOI Tokyo, plus
the open-source `jamulus_remote`. Each is parameterised: latency
to director, max simultaneous actors, hourly rate, isolation in
dB, ADR support. Sessions follow BOOKED → SETUP → RECORDING →
WRAPPED → DELIVERED. Per-session, per-line, per-take logging with
director marks (PICK / ALT / WILD / HOLD). `best_studio_for(va_
location, budget_usd_max)` routes by city: LA actors → Burbank,
Tokyo → AOI, etc., falling back to the cheapest fit if budget
won't cover the local studio. ADR is a session kind — Jamulus
doesn't support it (latency too low for picture lock), Burbank
does.

### `voice_performance_direction`
The director's per-line brief in data form. `Intent` enum has 15
tags: WEARY, COMEDIC, ANGRY, TENDER, COLD, BREATHLESS, WHISPER,
SHOUT, SARCASTIC, MENACING, RESIGNED, DEFIANT, AFRAID, WITHDRAWN,
BREAK_FOURTH_WALL. Each line gets a `Direction` (intent tag set,
tempo +/- 2, pitch +/- 2 semitones, pause-before / after in ms,
allow alt takes flag, optional reference clip URI). The same data
structure feeds two outputs: `ai_inference_kwargs(line_id)`
returns a dict the `voice_pipeline` engine prompt-conditions on,
and `human_va_brief(line_id)` returns a markdown call sheet the
director hands the actor in the booth. `to_murch_emotion_score`
maps the intent tags to a 0..1 emotional-loading score the
`scene_pacing` Murch rule-of-six layer uses for cut weighting —
heavy whisper / tender / menacing tags load more than comedic /
sarcastic / cold ones, and stacking multiple heavy tags loads the
line further.

### `voice_swap_orchestrator`
The line-level state machine that lets a single line transition
from AI default to human take and back if needed. Lifecycle is
AI_DEFAULT → HUMAN_RECORDING → HUMAN_QC → HUMAN_LIVE, with a
DEPRECATED → AI_DEFAULT rollback path. QC happens between
HUMAN_RECORDING and HUMAN_LIVE: alignment check (Whisper
transcription against the canonical line, character error rate
≤ 5%), duration check (within +/- 10% of the AI version), loudness
check (EBU R128), room-tone match. `QcReport` is a frozen
dataclass with `passed`, `alignment_cer`, `duration_delta_pct`,
`loudness_lufs`, `issues`. `qc_fn` is pluggable so the test suite
injects a deterministic stub (any URI containing `"good"` passes,
`"bad"` fails). `percent_human_voiced(role_id)` and
`provisioning_dashboard()` are the per-role / per-project
completeness oracles. `active_uri_for(line_id)` is the question
`voiced_cutscene` actually asks at playback time — the orchestrator
returns the human URI when the line is HUMAN_LIVE, otherwise the
AI URI.

## How it integrates with existing modules

- **`voice_pipeline`** — the engine. The registry's
  `provisioned_by.kind == AI_ENGINE` says "synthesise via this
  engine." `voice_performance_direction.ai_inference_kwargs` is
  the kwargs payload the engine consumes.
- **`voice_profile_registry`** — kept distinct from
  `voice_role_registry` on purpose. The profile registry is voice-
  *clone* metadata (reference WAVs, Higgs voice IDs); the role
  registry is *casting* metadata. A role can be voiced by an AI
  engine that uses a profile, OR by a real human who doesn't.
- **`voiced_cutscene`** — at playback, asks
  `voice_swap_orchestrator.active_uri_for(line_id)` to know what
  audio to load. Doesn't care whether it's AI or human.
- **`dialogue_lipsync`** — when a line transitions to HUMAN_LIVE,
  the orchestrator's promotion step is the trigger to re-bake
  visemes from the new audio (the Audio2Face / Rhubarb /
  Oculus / Apple pipelines all accept any WAV).
- **`scene_pacing`** — the Murch rule-of-six cut threshold uses
  per-line emotional loading. `voice_performance_direction.
  to_murch_emotion_score` is the source.
- **`director_ai`** — already a stateless picker; pacing layer
  feeds it intent-loaded scores.

## The open-source recording stack

Demoncore's bias is open-source-first. The pipeline is designed
to run end-to-end on free / FOSS tooling, with paid studios
slotting in whenever a role wants real human polish:

- **DAW**: Reaper (perpetual license, $60 commercial / free
  evaluation). Audacity for quick edits.
- **Whisper** (OpenAI, MIT) for transcription-based alignment QC.
  The orchestrator's `_stub_qc` is replaced in prod by a real
  Whisper call against the canonical line.
- **Jamulus / SonoBus** for low-latency remote sessions when
  going-to-a-studio isn't viable.
- **Source-Connect** is the paid alternative when Jamulus latency
  isn't tight enough — the `home_booth` studio in `voice_session_
  studio` represents that vendor.
- **EBU R128 loudness analyser** — `loudness-scanner`,
  `ffmpeg ebur128`, or `pyloudnorm` are all viable for the
  `loudness_lufs` field of `QcReport`.

## Real-VA business model placeholder

The `RateCard` dataclass carries two fields:
`per_word_usd_for_human` (default $0.45/word, mid-market non-union
rate for character work) and `per_minute_inference_cost_for_ai`
(default $0.08/min for Higgs-class TTS). When the project upgrades
a role, the casting director knows the budget envelope from the
rate card. Contracts go in the `contract_id` field of
`Provisioning` — that field links the role to whatever paperwork
system the producer uses (SAG-AFTRA, non-union LOA, work-for-hire,
royalty-share, etc.). The pipeline doesn't care which; it just
needs the id.

## The one decision worth flagging

We chose **line-level** swap granularity, not role-level. Once a
real VA is booked for a role, you can still ship 90% of that
role's lines from AI and the 10% the VA has actually recorded
from the human take. The orchestrator handles the heterogeneous
case naturally — `provisioning_dashboard()` shows
`{"curilla": 12.3}` to mean Curilla is 12.3% human-voiced, and
that number ticks up over time as more sessions deliver. This
matches how real animation studios mix temp and final dialogue,
and it lets the project always be ship-able, never in a
half-recorded limbo.

---

Cross-references: `VOICE_PIPELINE.md`, `CINEMATIC_PERFORMANCE.md`,
`CINEMATICS.md`.
