# MUSIC_REMIX_PIPELINE.md

How we take FFXI's canonical 22-year-old soundtrack and remix it
into Demoncore's audible palette. The original music is the
single biggest emotional brand element from retail FFXI — every
veteran has Bastok's industrial march in their head. We don't
replace it. We **remix** it.

This sits next to `MUSIC_PIPELINE.md` (already designed) and
`server/music_pipeline/` (already built — with ACE-Step + stub
backends). Where MUSIC_PIPELINE handles AI-original BGM
generation, this doc is about taking the retail FFXI soundtrack
as input and producing modernized, mood-conditioned variants.

The user has indicated they'll provide a YouTube reference when
it's time to define the remix style. This doc captures the
extraction + remix architecture so we're ready to execute as
soon as the style direction lands.

---

## Why remix vs. replace

Three reasons:

1. **Brand continuity.** Veterans hear the first 8 bars of
   "The Republic of Bastok" and it triggers 15-year memories.
   Throwing that out and putting in pure AI-generated BGM
   would make the world feel *like a different game*.
2. **Cinematic foundation.** Nobuo Uematsu / Kumi Tanioka /
   Naoshi Mizuta wrote great themes. We'd need to be very
   good to do better. We don't have to be — we just have to
   re-orchestrate and re-time.
3. **AI capability.** ACE-Step v1.5 is good at style transfer
   when you give it a melody as a stem. It's mediocre at
   composing original 3-minute pieces from prompt alone. The
   remix path plays to ACE-Step's strengths.

---

## The pull-and-remix pipeline

### Step 1 — Extract from retail client

The retail FFXI client at `F:\ffxi\client\FINAL FANTASY XI\` has
all the music in `BGW` format (Square's proprietary audio
format) inside the zone DAT files. The canonical extraction
tool: **POLUtils** (already referenced in
`ZONE_EXTRACTION_PIPELINE.md`).

Extraction batch (sister to `EXTRACT_BASTOK_FROM_RETAIL.bat`):

```
EXTRACT_RETAIL_MUSIC.bat
  - Locates POLUtils (download if missing)
  - Walks every BGW file in the retail ROM directories
  - Converts BGW → WAV via POLUtils' bgw2wav utility
  - Outputs to F:\ChharithOeun\...\extracted\music_retail\
  - Writes manifest with: zone_or_event, original_filename,
    duration_seconds, key_signature_hint, instrumentation_hint
```

Output catalog example:
```
music_retail/
├── manifest.json
├── bgm_bastok_markets.wav       (3:42)
├── bgm_metalworks.wav           (4:15)
├── bgm_battle_normal.wav        (2:08)
├── bgm_battle_versus_the_shadow_lord.wav  (3:22)
├── bgm_chains_promathia_intro.wav         (1:48)
├── bgm_san_doria.wav            (3:55)
├── bgm_windurst.wav             (4:01)
├── bgm_jeuno.wav                (3:30)
├── bgm_ronfaure.wav             (3:18)
└── ... (~150 tracks total across all expansions)
```

The full FFXI music library is ~150 tracks. Total ~10 hours of
audio. Total disk: ~1 GB uncompressed WAV. Tractable.

### Step 2 — Stem separation

Each track gets stem-separated into 4 stems via Demucs (free
open-source, runs on the user's GPU):
- **vocals** (rare in FFXI; mostly choir cues)
- **bass** (low-end harmonic skeleton)
- **drums** (percussion + rhythmic energy)
- **other** (melodic + harmonic instruments — the most expressive layer)

Stems sit at:
```
music_remix/
├── stems/
│   ├── bgm_bastok_markets/
│   │   ├── vocals.wav
│   │   ├── bass.wav
│   │   ├── drums.wav
│   │   └── other.wav
│   └── ...
```

Stem separation is a one-time cost (~30 sec per track on a
modern GPU). After this we have surgical control: keep the
melody, swap the percussion, replace the bass with a heavier
modern engine.

### Step 3 — Style-transfer remix via ACE-Step

ACE-Step takes:
- Stems (or a melody guide track)
- A natural-language style prompt
- Optional length parameter

And produces:
- A new track that follows the input melody but with the new
  style applied

Example prompt for Bastok:
```
"Take this melody and re-orchestrate as: industrial-fantasy
hybrid, brass-heavy, modern hip-hop drum bus, 95 BPM, 4-min
loop, build tension at 2:30 with sub-bass + electric guitar,
emotional palette: pride + grit + warmth. Maintain the
original melodic motif throughout."
```

Each zone gets a base remix per its `LAYERED_COMPOSITION.md`
atmosphere preset. Same Bastok track gets:
- **Daytime variant**: warm + brass-heavy
- **Nighttime variant**: cooler, sub-bass dominant, slower
- **Siege/raid variant**: fast tempo, drums up, brass biting
- **Aftermath variant**: solo strings, slow, reverent

So one canonical FFXI track yields ~3-4 mood-tagged variants.
~150 tracks × ~3 variants each = ~500 files in the final
remix library. Total ~50 hours of music for the entire game.
**This is the audio brand.**

### Step 4 — Mood-aware playback at runtime

Per `MOOD_SYSTEM.md` + the Vana'diel game clock, the LSB
runtime selects the right variant per zone + per current
state:

```
zone:        bastok_markets
hour_of_day: 18:00 (evening)
state:       siege_alarm_active

→ playback: bgm_bastok_markets_siege_evening.wav
```

The orchestrator's mood propagation drives the variant
selection. Players walking through Bastok during a beastman
siege hear a faster, harder, more anxious version of the
familiar theme. The melody is the SAME — what's modulated is
the orchestration + tempo + dynamics.

---

## Style-direction parameters (when the YouTube reference lands)

We're parameterizing this now so the YouTube reference becomes
a single config update. The remix pipeline reads:

```json
"style_direction": {
  "primary_genre": "tbd_per_youtube_reference",
  "secondary_genre": "fantasy_orchestral",
  "tempo_modifier": 1.0,
  "drum_kit": "tbd",
  "bass_synth": "tbd",
  "lead_instruments": "tbd",
  "production_tags": ["wide_stereo", "modern_dynamics"]
}
```

When you point at the YouTube video, we listen to it, transcribe
the production style (genre, instrumentation, tempo, mix
character), populate this config, and the remix pipeline
re-renders all 150 tracks in that style.

**The user's specific direction takes priority over any default
guess.** The doc captures the architecture; the actual style
choice waits for the reference.

---

## Implementation outline

### `EXTRACT_RETAIL_MUSIC.bat`
Sister batch to the zone extraction. Auto-installs POLUtils,
walks retail client BGW files, converts to WAV, writes manifest.

### `server/music_pipeline/remix.py` (extending the existing module)

```python
class RemixPipeline:
    def __init__(self, *,
                 stems_dir, style_config_path,
                 output_dir, backend="stub"):
        ...

    def stem_separate(self, source_wav_path):
        """Demucs → 4-stem separation"""
        ...

    def apply_style(self, stems_dir, style_config, mood_tag,
                     duration_sec):
        """ACE-Step remix → 1 styled output WAV"""
        ...

    def generate_zone_variants(self, zone_slug, base_track_path,
                                mood_variants):
        """For each mood (daytime/nighttime/siege/aftermath),
        generate a separate styled output."""
        ...
```

### `data/music_remix_targets.json`
Maps the canonical 150 retail tracks to:
- Zone or event they belong to
- Mood-variant requirements per
  `LAYERED_COMPOSITION.md` atmosphere presets
- Special-case tracks (boss themes, story cinematics)

### Manifest generation
After remix, we get a manifest the LSB runtime reads:
```json
{
  "track_id": "bgm_bastok_markets",
  "variants": [
    {"mood": "daytime", "path": "remix/bastok_markets_daytime.wav", "duration": 240},
    {"mood": "nighttime", "path": "remix/bastok_markets_nighttime.wav", "duration": 240},
    {"mood": "siege", "path": "remix/bastok_markets_siege.wav", "duration": 240},
    {"mood": "aftermath", "path": "remix/bastok_markets_aftermath.wav", "duration": 180}
  ],
  "original_motif_preserved": true,
  "remix_style_version": "v1_pending_user_youtube"
}
```

---

## Cost + time budget

- Extraction: ~10 minutes for the full 150-track library
- Stem separation: ~75 minutes for all 150 tracks (30s each on a 4090)
- Remix per track per variant: ~5-10 minutes per minute of
  audio on ACE-Step. So 150 × 4 variants × ~3 min each = 1,800
  minutes of audio = 9,000-18,000 minutes of compute = 6-12
  GPU days for the full library
- Realistic schedule: 1 zone per overnight run, full library in
  ~3 weeks of overnight work

**Worth it.** The music brand stays. The player's first time
walking into Bastok in Demoncore feels like coming home — but
*better*.

---

## License + IP considerations

The retail client is the user's purchased property; they
extracted the music for their own server. Original Square Enix
copyright applies to the source music. **Demoncore is a
private server project, not a commercial release.** Internal
use of remixed retail music for a private LSB-based server
falls under fair-use precedent that LSB itself relies on.

If Demoncore ever moved to public commercial distribution, the
remix pipeline would need to switch to fully AI-original BGM
(per `MUSIC_PIPELINE.md`, already authored). The two pipelines
coexist in the codebase for exactly this reason.

---

## Status

- [x] Architecture doc (this file)
- [ ] EXTRACT_RETAIL_MUSIC.bat (POLUtils-based extraction)
- [ ] data/music_remix_targets.json — 150-track catalog
- [ ] User-provided YouTube style reference → style_direction config
- [ ] server/music_pipeline/remix.py — Demucs + ACE-Step style-transfer
- [ ] First test: Bastok Markets daytime variant
- [ ] First playtest: walk into Bastok Markets, hear remixed BGM
- [ ] Run the full overnight remix pipeline (3 weeks of compute)
- [ ] License confirmation for private-server use
