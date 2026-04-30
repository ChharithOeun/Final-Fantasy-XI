# Voice Pipeline

> Every NPC, monster, NM, and boss has a voice. The chat box becomes subtitles.

This doc covers the voice synthesis stack. The bubble-chat UI for player chat is in a sibling doc (`docs/UI_CHAT.md`, to be written) — this one is about what comes out of NPC mouths.

## Design rules

- **No silent characters.** Every line a non-player entity says is voiced.
- **No text-in-chat-box for NPC speech.** The chat box never receives NPC dialogue. The dialogue is *spoken* with synced subtitles below the speaker.
- **Subtitles are mandatory** (game-default-on, settings-toggleable for the few who don't want them). Voice is not a substitute for accessibility.
- **Per-character voice identity.** A shopkeeper sounds like that shopkeeper, every time. We do not re-cast voices.
- **Per-encounter consistency for monsters.** A goblin in Ronfaure sounds like a Ronfaure goblin every time. NMs and bosses get unique voices. Trash mobs share a voice bank by family.
- **Latency target: under 800 ms** from "agent decides to speak" to "first audio frame plays." Slightly above that is fine; over a second feels broken.

## The stack

Three tools doing complementary jobs:

| Tool | What it does | When we use it |
|------|--------------|----------------|
| [`boson-ai/higgs-audio`](https://github.com/boson-ai/higgs-audio) (Higgs Audio v2) | Best-in-class open-source voice cloning + emotion + multi-speaker dialogue + speech-with-background-music. Apache 2.0. | Primary voice for ALL named NPCs, NMs, bosses. The thing we lean on for the things players will hear most. |
| [`SWivid/F5-TTS`](https://github.com/SWivid/F5-TTS) (F5-TTS v1) | Flow-matching TTS, fast inference, MIT license. Excellent voice cloning from short reference clips. | Backup / fallback / batch generation when we want to pre-render bulk lines (shopkeeper bark loops, town ambient chatter). |
| [`suno-ai/bark`](https://github.com/suno-ai/bark) | Generative TTS that ALSO produces non-speech audio: laughs, grunts, gasps, sighs, coughs, monster vocalizations. | Monster combat vocalizations, ambient creature sounds, non-verbal NPC reactions. The "ugh" and "ARRGGHH" that aren't text-able. |

We add all three under `FFXI-Hardcore/repos/_voice/`.

## Voice bank architecture

Each speaking entity has a **voice bank**:

```
voice_banks/
├── npcs/
│   ├── valdeaunia_zaldon/        # Bastok Markets fish vendor
│   │   ├── reference.wav         # 10-30s clip we cloned from
│   │   ├── style_card.json       # tone, age, accent, mood biases
│   │   └── pre_rendered/          # optional: bulk lines we cached
│   │       ├── greeting_001.wav
│   │       ├── greeting_002.wav
│   │       └── ...
│   ├── (one dir per named NPC)
├── mobs/
│   ├── goblin_ronfaure/          # mob family voice bank
│   │   ├── reference.wav
│   │   ├── grunts/               # Bark-generated non-speech samples
│   │   └── lines/                # if the mob speaks
│   ├── ...
├── nms/                          # NMs get unique reference clips
└── bosses/                       # bosses get unique + background music
```

The reference clip is what Higgs Audio / F5-TTS clones from. The style card is metadata that constrains the LLM's word choice for that NPC (e.g., Zaldon never uses modern slang; he speaks like a Bastokan dock veteran).

## Where the reference clips come from

This is the question that decides whether the project flies or crashes.

**Option A — extract from existing FFXI voice tracks.** FFXI has a small amount of voiced content (cutscenes from later expansions, mostly). We use those for the characters who already had voices in the original. Risk: tiny pool, mostly Trust dialogue and main story cutscenes.

**Option B — community voice donors.** A volunteer voice actor records 30-second reference clips for each named NPC. Time-intensive but produces authentic, consistent results. Preferred for major characters (Cid, Lion, Zeid, Aldo).

**Option C — generated from descriptions.** For minor NPCs, we generate a reference voice from a short text description ("middle-aged Bastokan male, gravelly, suspicious") using Higgs Audio's text-to-voice mode. Fast, consistent, but lacks the warmth of human reference.

Default policy: Option B for the named-character roster (~200 characters), Option C for the rest (~1500 NPCs), Option A wherever we have it. NMs and bosses always get Option B unless the actor count blows up.

## Synthesis flow

```
Agent decides to speak
    │
    │ "valdeaunia_zaldon: 'You again? Fine, but cornette prices
    │  are murder this week.'"
    │
    ▼
┌──────────────────────────────────┐
│ Subtitle dispatcher              │
│  - emit subtitle line to UI      │
│  - tag with speaker_id, mood     │
│  - schedule audio start when     │
│    UI confirms first frame shown │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│ Voice synthesis selector         │
│  - if pre-rendered match: serve  │
│    cached file (sub-50ms)        │
│  - else: dispatch to TTS         │
└──────────────────────────────────┘
    │
    ├───► Higgs Audio v2 (named NPCs, NMs, bosses; default)
    ├───► F5-TTS (backup / batch pre-rendering)
    └───► Bark (monster grunts, non-verbal reactions)
    │
    ▼
┌──────────────────────────────────┐
│ Audio post                       │
│  - per-character EQ              │
│  - mob-family pitch shift /      │
│    distortion (goblins are 0.85x │
│    pitch + roughness; tonberries │
│    are 0.65x + cave reverb)      │
│  - boss: mixed with voice-       │
│    appropriate background music  │
│    bed (already from ACE-Step)   │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│ UE5 client                       │
│  - 3D-spatialized audio source   │
│  - lip sync via UnrealGenAI plugin│
│  - subtitle stays visible for    │
│    ceil(audio_duration * 1.2)    │
└──────────────────────────────────┘
```

## Monster pitch / effect chain

Higgs and F5 produce human-sounding speech. Monsters need to sound like monsters. The post-processing chain per mob family:

| Family | Effect chain |
|--------|--------------|
| **Goblins** | -2 semitones, light distortion, throat-roughness EQ, +30ms slap delay |
| **Orcs** | -4 semitones, formant-shift down, growl LFO, +reverb |
| **Tonberries** | -5 semitones, slow LFO ring-mod, cave reverb, no consonant clarity (they whisper) |
| **Yagudo** | +1 semitone, clipped vowels, occasional click consonants, mild squawk EQ |
| **Quadav** | -2 semitones, formant shift up, metallic ring, dry |
| **Beastmen warlords (NMs)** | base mob effect + reverb tail, slowed delivery, +emotional intensity prompt to Higgs |
| **Avatars / sky gods (bosses)** | echo, otherworldly chorus layer, music bed underneath |
| **Fomors** | the original player's voice + ghostly chorus + slight pitch tremolo (they ARE the player, twisted) |

The chain runs in real-time on the chharbot side via `pedalboard` (Spotify's open-source audio effects library). Output is the final WAV that gets handed to UE5.

Effect parameters are in JSON next to each voice bank, easy to tune.

## Pre-rendering vs real-time

Pre-render when we can:

- **Bulk shopkeeper barks** — "Welcome." / "Anything else?" / "Come back soon." — the same NPC saying one of ~20 stock lines. Cache once, serve instantly.
- **Quest dialogue** — when the LLM generates a line for a quest NPC, we cache it keyed on (npc_id, prompt_hash). Same context = same line, served from cache.
- **Boss intros** — long, dramatic, delivered the same every time the boss spawns. Pre-render and ship as part of the asset bundle.

Real-time when we have to:

- **Reactive NPC dialogue** — when the cooks' guild master comments on the cornette market, that line is novel; synth on demand.
- **Combat banter** — fomors taunting players, NMs threatening parties — context-dependent, real-time.
- **Players' fomor-self speaking** — your former character now insulting you in their own voice. Has to be live. Worth every millisecond of latency.

## chharbot MCP wrappers

Three tools next to `agent_tools.py`:

```python
# in mcp_server/voice_tools.py
@mcp.tool
def voice_synth(
    speaker_id: str,
    text: str,
    emotion: str = "neutral",
    output_path: str = "out.wav",
) -> dict:
    """Synthesize a line in the speaker's cloned voice with optional emotion.
    Auto-selects Higgs / F5 / Bark based on speaker_id's bank type."""

@mcp.tool
def voice_clone(
    speaker_id: str,
    reference_audio_path: str,
    style_card_path: str,
) -> dict:
    """Register a new voice bank from a reference clip + style card."""

@mcp.tool
def voice_prerender_bank(
    speaker_id: str,
    lines_json_path: str,
) -> dict:
    """Bulk-pre-render a list of lines for a speaker, cache to disk.
    Used by build pipelines to generate stock barks."""
```

## Subtitles

Subtitle UI lives in UE5 (the `UnrealGenAISupport` plugin already handles subtitle rendering tied to TTS). Format:

```
┌──────────────────────────────────────────────┐
│ Zaldon                                       │
│ "You again? Fine, but cornette prices..."    │
└──────────────────────────────────────────────┘
```

Speaker name in their faction color, line in white, fade out 1.2× the audio duration.

For overlapping speakers (party of fomors yelling at once), subtitles stack and color-code per speaker. Maximum 3 simultaneous speakers shown; beyond that the older subtitle drops.

## Known risks

- **Higgs Audio is huge.** The model is multiple GB. We host it on the chharbot box and synthesize via API. Inference fits in 24 GB VRAM.
- **Voice consistency drift.** Cloned voices drift in long-form generation. Mitigation: keep individual lines under ~15 seconds; for longer monologues, chunk and concatenate with per-chunk reference re-injection.
- **Cost / compute on a busy server.** 1000 NPCs each saying something every minute is a lot of synth. Mitigation: aggressive pre-rendering of repetitive lines + voice-priority queue (boss > NM > named NPC > generic mob > generic NPC).
- **Legal — using existing FFXI voice acting.** We extract voiced content from the user's licensed copy of FFXI for personal/private-server use only. We never ship the resulting voice models commercially.

## Build order

1. **Higgs Audio smoke test** — clone one voice from a 30-second reference, render one line, listen to it.
2. **Voice bank schema + storage** — SQLite metadata + filesystem WAV layout. Round-trip a single NPC.
3. **Subtitle UI in UE5** — wire the dispatcher → UE plugin path with one hardcoded line. Latency check.
4. **Bark integration for monster grunts** — ten goblin grunts in different inflections.
5. **First reactive NPC** — Bastok Markets fish vendor (Zaldon) generates a fresh line via the LLM, gets synthed, plays in-game. End-to-end vertical slice.
6. **Pre-rendering pipeline** — for stock dialog, batch pre-render at build time.

After step 5 we have the entire pipeline shake-tested. Steps 1–5 are weeks, not months — the upstream tools all just work.
