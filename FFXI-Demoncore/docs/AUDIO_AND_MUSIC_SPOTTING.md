# AUDIO + MUSIC SPOTTING

## Vision

The previous batch finished the demo's visual stack — 41
seamless zones with breathing crowds, animated skeletons,
combat VFX, spell systems, screen-effects punctuation. The
camera reads. The shots cut. The bandit raid lands like
film.

But take the headphones off and put them back on with the
music muted, the sound effects muted. What you have left
is a slideshow. A live-action film without sound is half a
film. The world stops being a world the moment the speakers
go quiet.

This batch is the audio + music spotting layer. Five
modules turn 41 zones from a visual stack into sonically
alive places — per-surface footsteps that read the floor
under each character, reverb that matches the architectural
volume the listener is standing in, ambient soundscapes
that say "you're in a smelter" or "you're on a pirate
porch" or "you're in a marsh in the rain", a music
conductor that fires cues on gameplay beats the way a film
composer fires cues on cuts, and a multi-stem layer system
that crossfades the score in lockstep with what the player
is doing in the fight.

The result is the demo's audio reaching the same fidelity
ceiling as its visuals: the choreography beat that swings
the camera over a Bastok Markets bandit raid is ALSO the
beat that swaps the day-march for the kinetic combat stem,
fires a magic-burst sting, attenuates Cid's anvil clang as
the listener moves down the alley, and lands a surface-
specific footstep on cobble for a galka in plate armor with
the appropriate plate-jingle overlay.

## The five modules

### 1. server/music_spotting/

The conductor. Owns the catalog of cues — what music plays
on what trigger. A SpotCue is `(cue_id, trigger_kind,
music_stem_uri, fade_in_ms, fade_out_ms, layer (BASE |
TENSION | COMBAT | BOSS | VICTORY | DEFEAT |
DIALOGUE_STING | REVEAL_STING), priority, loop)`. Cues fire
on twelve trigger kinds: ZONE_ENTER, SHOWCASE_BEAT,
COMBAT_START, COMBAT_END, BOSS_INTRO_TRIGGER,
MAGIC_BURST_FIRED, SKILLCHAIN_CLOSED, DIALOGUE_LINE_STARTED,
PLAYER_DEATH, LEVEL_UP, NIGHT_FALLS, WEATHER_CHANGED.

Layer hierarchy: BASE always plays; TENSION fades in when
threats are nearby; COMBAT replaces TENSION on engage; BOSS
replaces COMBAT on boss-engage; stings (DIALOGUE_STING +
REVEAL_STING) ride for 2-6s overlays on top of whatever is
playing.

Spot inheritance: a zone has a default BASE stem; a
showcase_choreography beat can override it for the duration
of the beat. The bandit raid override swaps Bastok Markets'
day-march for a kinetic combat stem; when the beat ends,
the override releases and the day-march fades back in.

Pre-populates 33 cues covering Bastok Mines / Markets /
Metalworks BASE stems, Sandy and Windy BASE stems, Norg,
three combat themes (light/medium/heavy), Iron Eater boss
theme, magic-burst and skillchain stings (Light, Darkness,
Crystal, Umbra), dialogue-cue stings (emotional, comedic,
menacing), a weather-change sting, a level-up fanfare, a
night-falls pad, victory + defeat themes, and two showcase
overrides.

### 2. server/foley_library/

Per-surface footsteps and interaction foley. The floor under
the foot times the body that's moving times the sample
variation that prevents machine-gun click repetition. 17
surfaces (wood / stone-dry / stone-wet / metal-grated /
metal-plate / grass / dirt / sand / marsh-squelch / water-
shallow / water-deep / snow / ice / cobble / marble / carpet
/ mog-house-rug). 5 gaits (Galka heavy, Hume normal, Elvaan
long-stride, Mithra prowl, Tarutaru light). 4 sample
variants per combo, round-robin'd at runtime — the same
character walking on the same surface gets a 4-way rotation
of subtly different recordings.

Action foley overlays: drawing a sword while wearing plate
fires SWORD_DRAW + ARMOR_PLATE_JINGLE in the same frame.
The library's `foley_for_action(action, costume_kind)`
returns the right pair (or single sample for actions that
don't engage the body — chest_open, eat_crunch). 16
canonical interaction foleys: sword draw / sheathe, axe
heft, cloth rustle, three armor profiles, backpack set-
down, inventory open / flip, two door types, chest open,
bottle uncork, eating crunch / liquid.

The default library yields 17×5 + 16 = 101 entries.

### 3. server/reverb_zones/

Per-zone (and per-volume-within-zone) acoustic profile. A
ReverbProfile is the parameter pack the audio engine uses
to convolve real-time DSP: `(rt60_seconds, early_reflections
_ms, diffusion, damping_freq_hz, high_cut_hz, low_cut_hz,
room_size_m3, wetness)`.

Pre-populates 12 profiles: BASTOK_MINES_TUNNEL (long
metallic 2.3s rt60), BASTOK_MARKETS_OPEN (mid-air 1.1s
parallel-wall flutter), CIDS_WORKSHOP (small smelter 0.4s,
high-frequency damped at 3kHz), SANDY_CATHEDRAL (massive
4.2s, stone), SANDY_ALLEYWAY (medium 1.6s), WINDY_GLASS_HALL
(forward 0.9s), KONSCHTAT_OPEN_PLAIN (outdoor 0.2s, almost
dry), CAVE_SUBTERRANEAN (deep 3.5s), DUNGEON_GARLAIGE (echo
chains 2.7s), FOREST_DENSE (damp 0.3s, leaf-absorbed),
WINDY_WOODS_PAVILION, NORG_PIRATE_HALL.

Sub-volumes: a ReverbVolume is a bounding box inside a
zone with an override profile. Cid's workshop is registered
as a volume inside Bastok Markets — bounds_min (140, 0,
-10) to bounds_max (150, 4, 0). The listener stepping into
that box swaps from BASTOK_MARKETS_OPEN to CIDS_WORKSHOP
in real time.

Smallest-volume-wins resolution: nest a workshop inside a
foundry inside the city; the listener gets the workshop
profile, not the foundry. `interpolate_at_boundary(zone_a,
zone_b, t)` does smooth blending between two zone defaults
— couples to zone_handoff so the moment the player crosses
the loading edge between Bastok Markets and Bastok Mines,
the reverb morphs through the crossfade window instead of
popping.

### 4. server/ambient_soundscape/

The ambient bed for each zone — the always-on layer of
non-music, non-action sound that says "you're somewhere".
A SoundscapeBed is a stack of AmbientLayer records;
layers come in five kinds:

- **LOW_FREQ_HUM** — carrier rumble (smelter low-end,
  ocean, cave drone). Always-on, looped, mixed low.
- **MID_TEXTURE** — texture (footstep floor sound, leaf
  rustle, market chatter). Looped.
- **HIGH_DETAIL** — bright detail (wind chimes, insects,
  seagulls). Looped, panned.
- **SPATIAL_POINT** — fixed-position point source (Cid's
  anvil, fountain). Linear-falloff distance attenuation.
- **ONE_SHOT** — fires periodically with a min/max
  interval (vendor cry, Yagudo gong, distant chocobo).
  `schedule_next_one_shot()` returns deterministic ETAs at
  the midpoint of the interval window.

13 default beds covering: Bastok Mines (industrial hum +
steam vent + distant hammer + shift whistle), Bastok
Markets DAY (crowd murmur + cart wheels + smelter low-end
+ Cid's anvil + vendor cries) and Bastok Markets NIGHT
(crickets + distant cart wheel only), South Sandoria
(cathedral choir distant + cobble bg + fountain trickle +
lutist on corner), Windurst Woods (chimes + tarutaru
chatter + Yagudo gong + flower-petal flutter), Norg (waves
+ ship creak + pirate banter), Konschtat Highlands (wind
through grass + chocobo distant + insects + sheep bleat —
CLEAR-weather-only), Pashhow RAIN (frogs + dripping +
leech splosh + thunder distant), Davoi (orc drumming +
howl + axe-on-wood + cooking fire), Crawler's Nest (chitin
+ skitter + drip + ovum hatch), The Eldieme Necropolis
(wind ghost-moan + bone creak + crow caw + organ distant),
Qufim Island (waves + seagull + lost-souls wail + island
palm), Tahrongi Canyon (canyon wind + rockslide distant +
falcon screech + hoof-step distant).

Time-of-day + weather variants. Bastok Markets at DAY is
full crowd cacophony; at NIGHT it's a single drunk cart
wheel and a cricket. Pashhow at CLEAR weather is dry
frogs; at RAIN it adds dripping water and thunder. The
bed-selector scores variants — exact weather match worth 8
points, exact tod match worth 4 points, ALL fallback worth
0 — so a specific variant always beats a fallback.

### 5. server/dynamic_music_layers/

The multi-stem layer system. Where `music_spotting` decides
"what cue plays on this beat", this module decides "of the
active stems, what gain does each get RIGHT NOW".

A MusicLayer is `(layer_id, kind, zone_id, stem_uri,
gain_db_default, low_cut_hz, high_cut_hz)`. 10 layer kinds:
EXPLORATION, TENSION, COMBAT_LIGHT, COMBAT_HEAVY, BOSS,
VICTORY, DEFEAT, MOG_HOUSE, TOWN_DAY, TOWN_NIGHT.

Crossfade engine — `target_gains(zone_id, combat_state,
weather, time_of_day)` returns the dB-per-layer-kind dict
the audio mixer feeds the actual crossfade DSP. Rules:

- `threat_level < 3` and not in_combat -> EXPLORATION at
  default gain (or TOWN_DAY/NIGHT if zone is a town, or
  MOG_HOUSE if zone_id starts with `mog_house`).
- `threat_level >= 3` and not in_combat -> TENSION fades
  in. Replaces EXPLORATION.
- `in_combat` and `threat_level < 7` -> COMBAT_LIGHT
  replaces TENSION + EXPLORATION.
- `in_combat` and `threat_level >= 7` -> COMBAT_HEAVY
  replaces COMBAT_LIGHT.
- `is_boss_engaged` -> BOSS overrides everything.
- `combat_end with won=True` -> VICTORY plays once.
- `combat_end with won=False` or `death` -> DEFEAT plays
  once.

Stings (one-shots, parameterized): MAGIC_BURST,
SKILLCHAIN_LIGHT/DARKNESS/FUSION/FRAGMENTATION/DISTORTION/
GRAVITATION/CRYSTAL/UMBRA, CRITICAL_HEALTH (party HP <
25%). `should_play_sting(state_event, combat_state)` checks
whether the sting should fire — MAGIC_BURST only when
`magic_burst_recent`, CRITICAL_HEALTH only when
`party_below_25pct_hp`, skillchain stings always fire when
invoked.

Zone-specific overrides: a zone can register its own
COMBAT_LIGHT or BOSS layer that wins over the global
default. Bastok Markets has its own combat-light stem
(`bastok_markets_combat_light`) and Iron Eater has his own
boss layer (`iron_eater_boss`).

## Integration with existing systems

### music_pipeline (#147) — ACE-Step generation
`music_pipeline` produces the actual `.ogg` stems referenced
by `SpotCue.music_stem_uri` and `MusicLayer.stem_uri`. Each
of the 33 default cues + 12 default layers maps to a stem
the music_pipeline can be told to generate, with the
characteristic prompt + style that names the cue (Bastok
industrial march, Norg pirate haven, Pashhow marsh bog,
Iron Eater boss theme, etc).

### music_pipeline/remix.py (#149)
The remix module composes layered stems from a base track.
The `dynamic_music_layers` system's stem catalog is a
direct downstream consumer — every COMBAT_LIGHT /
COMBAT_HEAVY / BOSS layer can be a remix variant of the
zone's BASE stem with kinetic drums, vocal tags, brass
overlays added.

### sfx_pipeline (#152) — HD surround 4-class SFX
`sfx_pipeline` produces footstep / interaction / ambient
samples used by `foley_library` and `ambient_soundscape`.
The `(surface, gait)` -> 4-variant cycling reads sfx_
pipeline-generated footsteps.

### audio_listener_config (#480)
The listener config tells the engine where the player's
ears are in 3D space. `reverb_zones.profile_at(zone_id,
listener_pos)` consumes that listener position to pick the
right sub-volume profile. `ambient_soundscape.playlist_for
(zone_id, listener_pos, ...)` consumes it to attenuate
SPATIAL_POINT layers (Cid's anvil at 60m attenuation gets
quieter as you walk away).

### surround_audio_mixer (#473)
The mixer is the ultimate consumer. `music_spotting.fire()`
returns SpotPlan tuples; `dynamic_music_layers.target_
gains()` returns per-layer dB targets;
`reverb_zones.profile_at()` returns the active reverb
profile; `ambient_soundscape.playlist_for()` returns the
active ambient layer gains. The mixer takes all four,
applies the DSP, and outputs surround-encoded audio.

### voice_swap_orchestrator
Voice lines fire DIALOGUE_LINE_STARTED triggers into
`music_spotting` — the orchestrator tags lines with their
emotional context (emotional, comedic, menacing) and the
spotting system fires the matching dialogue sting under the
voice line.

### showcase_choreography
The choreography system fires SHOWCASE_BEAT triggers with a
beat tag (e.g. `bandit_raid`, `market_dawn`). The spotting
system has zone-and-tag-keyed override cues that swap the
zone's BASE stem for a beat-specific stem, and the dynamic-
layer system flips the threat-level state to land the
combat-stem crossfade in the same frame.

### scene_pacing
Scene pacing decides how long each beat sustains. The
spotting system's fade_in/out_ms values are tuned by the
pacing module's beat duration — a 2-second beat gets a
500ms fade-in; a 12-second cinematic gets a 3-second
swelling fade.

### zone_lighting_atlas
The lighting atlas's NIGHT-FALLS event fires the
NIGHT_FALLS spot trigger; the spotting system fires the
night-falls ambient pad sting.

### scene_pacing + showcase_choreography + dynamic_music_layers
The threat-level signal is computed by the AI / encounter
systems and threaded into `dynamic_music_layers.
target_gains()` per frame. The 0->10 scale maps to:
0-2 = exploration, 3-6 = tension or combat-light depending
on `in_combat`, 7-10 = combat-heavy. Boss-engage flips the
override flag.

## Open-source toolchain

| Tool | Use | License |
|------|-----|---------|
| Reaper (free trial unlimited) | DAW for stem editing + music_pipeline output mixing | unrestricted free trial |
| MetaSounds (UE5 builtin) | In-engine procedural audio graph (reverb, crossfade, sting routing) | UE5 EULA |
| Wwise free tier | Production audio middleware for foley + music + reverb routing | free <$200K rev |
| FMOD free tier | Alternative audio middleware option | free for indie |
| Audacity | Sample editing, batch normalize, simple effects | GPL |
| Sonic Visualiser | Sample analysis (RT60 measurement, spectrum) | GPL |
| Praat | Phoneme analysis (already in use for voice_swap) | GPL |
| OBS Studio | Audio capture for cinematic recording sessions | GPL |
| Spectrum lab | Long-form spectrogram for ambient bed authoring | freeware |

## Per-zone audio coverage

| Zone | BASE cue | Reverb profile | Ambient bed | Notes |
|------|----------|----------------|-------------|-------|
| bastok_mines | base_bastok_mines | BASTOK_MINES_TUNNEL | bed_bastok_mines_all | industrial-march + 2.3s rt60 + steam vent ambient |
| bastok_markets | base_bastok_markets | BASTOK_MARKETS_OPEN | bed_bastok_markets_day/night | day vs night crowd swap; CIDS_WORKSHOP sub-volume |
| bastok_metalworks | base_bastok_metalworks | (default) | (zone-shared) | anvil-theme stem |
| south_sandoria | base_south_sandoria | SANDY_ALLEYWAY | bed_sandy_all | medium 1.6s reverb, lutist + fountain |
| north_sandoria | base_north_sandoria | SANDY_CATHEDRAL | (zone-shared) | massive 4.2s for cathedral |
| windurst_woods | base_windurst_woods | WINDY_WOODS_PAVILION | bed_windy_all | chimes + tarutaru chatter + Yagudo gong |
| windurst_walls | base_windurst_walls | WINDY_GLASS_HALL | (zone-shared) | high-freq forward 0.9s |
| norg | base_norg | NORG_PIRATE_HALL | bed_norg_all | waves + ship creak + pirate banter |
| lower_jeuno | base_lower_jeuno | (default) | (TBD) | jeuno neutral sway |
| konschtat_highlands | base_konschtat | KONSCHTAT_OPEN_PLAIN | bed_konschtat_all | 0.2s rt60, chocobo + sheep + insects (CLEAR only) |
| pashhow_marshlands | base_pashhow | (default) | bed_pashhow_rain | RAIN-specific bed: frogs + thunder + leech splosh |
| jugner_forest | base_jugner | FOREST_DENSE | (TBD) | 0.3s leaf-absorbed |
| davoi | (default combat) | (default) | bed_davoi_all | orc drum + howl + axe-on-wood + cooking |
| crawlers_nest | (default combat) | (default) | bed_crawlers_nest | chitin + skitter + ovum hatch |
| eldieme_necropolis | (default combat) | DUNGEON_GARLAIGE | bed_eldieme_all | wind moan + bone creak + organ distant |
| qufim_island | (default exploration) | (default) | bed_qufim_all | waves + seagull + lost-souls wail |
| tahrongi_canyon | (default exploration) | (default) | bed_tahrongi_all | canyon wind + falcon + rockslide distant |
| dangruf_wadi | (default combat) | CAVE_SUBTERRANEAN | (TBD) | deep 3.5s |

## Cross-module flow — bandit raid kill blow with audio

1. Player enters Bastok Markets.
   - `music_spotting.fire(ZONE_ENTER, {zone_id:
     "bastok_markets"})` returns SpotPlan(`base_bastok_
     markets`, BASE, fade-in 2400ms).
   - `reverb_zones.profile_at("bastok_markets",
     listener_pos)` returns BASTOK_MARKETS_OPEN.
   - `ambient_soundscape.bed_for("bastok_markets", DAY,
     CLEAR)` returns bed_bastok_markets_day.
   - `dynamic_music_layers.target_gains("bastok_markets",
     idle_state, "clear", "day")` returns TOWN_DAY at
     -6dB; everything else silent.
2. Showcase choreography fires the bandit raid beat.
   - `music_spotting.fire(SHOWCASE_BEAT, {zone_id:
     "bastok_markets", context_tag: "bandit_raid"})`
     returns SpotPlan(`showcase_bandit_raid`, COMBAT,
     fade-in 400ms).
   - `dynamic_music_layers.transition_to("combat_start")`
     returns (COMBAT_LIGHT,).
   - `dynamic_music_layers.target_gains` with
     `in_combat=True, threat=4` returns
     COMBAT_LIGHT (zone override:
     `bastok_markets_combat_light`) at -3dB; TOWN_DAY
     silent.
3. Galka raider in plate armor swings at oil barrel.
   - `foley_library.pick_footstep(COBBLE, GALKA_HEAVY)`
     returns next round-robin variant.
   - `foley_library.foley_for_action("axe_heft", "plate")`
     returns (axe_heft.ogg, armor_plate_jingle.ogg).
4. Listener moves into Cid's workshop.
   - `reverb_zones.profile_at("bastok_markets", inside_
     volume_pos)` returns CIDS_WORKSHOP — workshop sub-
     volume wins, reverb morphs from MARKETS_OPEN to
     0.4s damped-3kHz inside the box.
   - The anvil-clang SPATIAL_POINT layer in the ambient
     bed gets attenuated to near-zero as the listener walks
     past the source.
5. Skillchain closes (Fragmentation).
   - `music_spotting.fire(SKILLCHAIN_CLOSED, {context_tag:
     "fragmentation"})` returns SpotPlan(sting_skillchain_
     light, REVEAL_STING, fade 50ms in / 1200ms out).
6. Magic burst connects.
   - `music_spotting.fire(MAGIC_BURST_FIRED)` returns
     SpotPlan(sting_magic_burst, REVEAL_STING).
   - `dynamic_music_layers.should_play_sting(MAGIC_BURST,
     state(magic_burst_recent=True))` returns True.
7. Iron Eater intro fires.
   - `music_spotting.fire(BOSS_INTRO_TRIGGER, {context_tag:
     "iron_eater"})` returns SpotPlan(boss_iron_eater, BOSS,
     fade 600ms in).
   - `dynamic_music_layers.transition_to("boss_engage")`
     returns (BOSS,); zone-override boss layer (`iron_
     eater_boss` at -1dB) replaces COMBAT_LIGHT/HEAVY.
8. Player kills Iron Eater.
   - `music_spotting.fire(COMBAT_END)` returns
     SpotPlan(victory_default, VICTORY).
   - `dynamic_music_layers.transition_to("combat_end",
     won=True)` returns (VICTORY,).
9. Player levels up.
   - `music_spotting.fire(LEVEL_UP)` returns SpotPlan(sting_
     level_up, REVEAL_STING, priority 9).

## Three design hinges

### 1. SPOTTING IS DECISIONS, NOT SAMPLES
`music_spotting` doesn't own the audio. It owns the
*decision* — what cue plays now, at what fade, at what
priority. The actual stems are produced by
`music_pipeline` (ACE-Step) and the actual mixing happens
in `surround_audio_mixer`. This separation lets us re-
spot the entire demo (different beat triggers, different
fade values, different priority breakdown) without
regenerating any audio. Re-spotting takes minutes.
Re-mastering takes weeks. The system is built to favor the
cheap operation.

### 2. ROOM TONE IS WORLD TONE
Every zone has reverb. Every zone has an ambient bed.
Every zone has a music base stem. Take any one of those
three away and the zone immediately feels like a stage
prop. The trick is getting the *match* between them right
— the BASTOK_MARKETS_OPEN reverb profile matches the
crowd-murmur ambient bed, which matches the Vana'diel
march BASE stem; all three were authored to fit together.
The ear hears all three as a single coherent space, and
the demo's 41 zones all ship with that match guaranteed by
the catalog.

### 3. STEMS BEAT TRACKS
A track is a finished mix. A stem is a single layer of the
mix that the engine can fade independently. Every BASE
stem in `dynamic_music_layers` has a TENSION variant, a
COMBAT_LIGHT variant, a COMBAT_HEAVY variant, a BOSS
variant — all built on the same harmonic bed. The
crossfade engine swaps stems in lockstep with the combat-
state signal; the player walks from idle into a fight, and
the music smoothly transitions from EXPLORATION to TENSION
to COMBAT_LIGHT to COMBAT_HEAVY to VICTORY without ever
cutting to a different track. The film-score grammar is
*the score reacts to the cut*, and the stem grammar lets
us deliver that without an army of composers.

The previous batch made the world punch. This batch makes
it sound like a place worth fighting in.
