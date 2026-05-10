# LAUNCHER + INPUT + ACCESSIBILITY + PHOTO + SPECTATOR

The polish layer. The previous batch shipped multiplayer
networking — entity replication, lag compensation, party
sync, cross-server zone handoff, spatial voice chat. The
demo is playable in co-op. But it's still a tech demo —
no front door, no rebind UI, no accessibility, no way to
brag about the screenshot, no way to broadcast the run.
This batch is the front door, the keyboard, the
accessibility panel, the photo mode, and the spectator
feed. Five modules turn the tech demo into a shippable
product.

## Vision — the shippable layer

Every game that ever launched needed five things outside
the gameplay loop:

1. **A launcher.** Not "press play in your IDE". An
   Anthropic-style splash, a title screen with the score
   playing, a patch check, login, server selection, the
   16-slot character select. Hand-off to character
   creation if you have an open slot. A one-time
   cinematic intro on first launch.
2. **An input layer.** The QWERTY player and the AZERTY
   player both press the "move forward" key. The Xbox
   player and the PlayStation player both press the
   "primary attack" button. The game doesn't care which
   physical input arrives — it cares which `GameAction`
   fires. Rebindable per character, importable per
   account.
3. **Accessibility.** Every player can play. Colorblind
   filters (protanopia / deuteranopia / tritanopia /
   monochromat). Reduced motion (kills camera shake).
   Reduced flash (photosensitive-safe — no strobes ever).
   Subtitles always-on, high-contrast, large. TTS. Screen
   reader hooks. Sticky keys. Hold-to-toggle. One-hand
   mode. Arachnophobia mode (spiders → cubes). Tutorial
   pace slow or fast. Twenty-two flags, every one of them
   one click away.
4. **Photo mode.** The marketing trailer needs hero
   shots. The streamer needs to share. The player wants
   to brag. Same camera bodies (Arri / RED / Sony) from
   `cinematic_camera`, same lens catalog (Cooke / Atlas /
   Zeiss) from `lens_optics`, same LUT chain from
   `film_grade`. Scrub time-of-day, override weather,
   apply filters, pose-lock a friend mid-jump, export
   PNG_4K / PNG_8K / EXR_HDR / MP4_60s_4K / GIF_5S.
5. **Spectator mode.** The streamer needs a director-cam
   that picks the best angle automatically. The esports
   caster needs a broadcast overlay (party comp left,
   party comp right, DPS chart bottom, current target
   middle-top). The replay viewer needs a 60-second
   rolling buffer to save the kill. Six modes from
   FREE_CAM to BROADCAST_OVERLAY; the cuts are picked by
   the same `director_ai` matrix the cutscene engine
   uses.

## The five modules

### `server/game_launcher/`

State machine for everything outside the in-game loop.
Fifteen states — SPLASH (Anthropic-style fade-in, 1.2s),
TITLE_SCREEN (region-localized background video + music),
PATCH_CHECK, PATCHING, LOGIN, DISCORD_OAUTH_FLOW,
SERVER_SELECTION, CHARACTER_SELECT, CHARACTER_CREATION,
WORLD_LOAD, CINEMATIC_INTRO (first-play only), IN_GAME,
PAUSED, DISCONNECTED, ERROR.

Every transition is in a directed graph at module load.
USER edges fire on button press; AUTO edges fire when
their predicate is true (`splash_elapsed`,
`patches_clean`, `download_finished`, `oauth_complete`,
`world_loaded`, `intro_complete`, `socket_dropped`).
`transition_to` returns `ok` or `denied`.

Character select renders up to 16 cards per account. Each
card carries name, race, main job, level, last-played
zone, and the hero shot URI for that zone (pulled from
`zone_lighting_atlas`). Last-played card is auto-picked
by most-recent `last_played_ms`.

CINEMATIC_INTRO runs `showcase_choreography`'s
`first_play_intro` sequence only on the very first
launch. `set_first_play_complete` flips it off for the
account forever.

### `server/input_mapping/`

The QWERTY → AZERTY → QWERTZ → JIS keyboard problem and
the Xbox → PlayStation → Switch Pro → Steam Deck gamepad
problem solved once. Twelve `InputDevice` values
including EYE_TRACKING (Tobii) and MOTION_CONTROL (Wii-
style, both accessibility and cinematic-kit use cases).
Forty-eight `GameAction` values cover every demo verb —
locomotion, combat, camera, menus, MACRO_1..10 +
ACTION_BAR_1..10.

Default profiles ship for KEYBOARD_QWERTY, GAMEPAD_XBOX,
GAMEPAD_PLAYSTATION, GAMEPAD_STEAM_DECK. 4 × 48 = 192
default bindings at boot. Per-character rebind via
`rebind(char_id, device, action, new_input)`;
`reset_to_default` clears overrides; `conflicts_for`
returns shared-input pairs so the UI can warn the player.

`importable_profile_blob` / `import_profile_from` give
players a shareable JSON for taking their setup between
machines.

### `server/accessibility_options/`

Twenty-two `AccessibilityFlag` values across five
`SettingsCategory` values (VISUAL / MOTOR / COGNITIVE /
AUDIO / CONTROL). Every flag is default-off and carries
metadata — `interferes_with` (you can't have both
DEUTERANOPIA and TRITANOPIA on), `recommended_with`
(REDUCED_MOTION pairs with REDUCED_FLASH), and
`suggested_by` (a set of complaint tokens that bubble
the flag to the top of the suggestion list).

Three integration points:
- `apply_color_filter(rgb, player_id)` — runs every
  rendered RGB through the player's colorblind LUT
  (placeholder matrix in code; ships as the canonical
  Brettel-Vienot-Mollon transform via Open Color Filter
  in production).
- `should_show_screen_effect(player_id, kind)` —
  `screen_effects` calls this before spawning hit-shake,
  MB-flash, paralyze-crackle, etc. REDUCED_MOTION
  suppresses shake/blur effects; REDUCED_FLASH
  suppresses strobes.
- `subtitle_renderable(player_id, line)` — returns the
  styled subtitle (large / high-contrast backplate /
  always-on toggles).
- `narrate_to_player` returns whether TTS should fire,
  driven by TTS_DIALOGUE or SCREEN_READER_HOOKS.

`suggest_flags_for(["camera_shake_complaint",
"flashing_lights"])` returns the recommended flags. The
settings panel can use it after a player reports a
problem in support chat.

### `server/photo_mode/`

Photographer mode reuses the entire cinematic-batch
pipeline. Four `PhotoState` values (INACTIVE /
ACTIVE_FREEROAM / ACTIVE_POSE_LOCK / CAPTURING). A
`PhotoCamera` references the same `cinematic_camera`
profile ids (arri_alexa_35, red_v_raptor, sony_venice_2,
canon_c500, iphone_15_pro_log) and the same `lens_optics`
lens ids (cooke_s7i, atlas_orion, zeiss_supreme,
helios_44).

Scrub time-of-day 0..24, override weather (clear / rain /
fog / snow / aurora / sandstorm), apply filters (vignette,
chromatic aberration, lens dust, film grain, bloom,
sepia, vintage-faded, `demoncore_trailer_master`).
Pose-lock freezes another player mid-animation for a
photogenic capture. Hide-HUD and hide-other-players for
privacy.

Export targets: PNG_4K, PNG_8K, EXR_HDR (16-bit half-
float, color-accurate for grading later), MP4_60S_4K
(short clips with dolly path), GIF_5S (5-second loops).
Sticker overlay frames the result with "Demoncore —
<zone> — <character_name>".

`recommended_camera_for(zone_id)` reads the zone lighting
atlas profile and suggests the best body + lens + focal
length — bastok_markets gets arri_alexa_35 + 75mm Cooke,
sandoria_castle gets the 135mm Zeiss for the throne-room
hero shot.

### `server/spectator_mode/`

The same engine for streaming, esports, and replay. Six
`SpectatorMode` values: FREE_CAM, FOLLOW_PLAYER,
DIRECTOR_CAM (auto-picks angles via the `director_ai`
matrix), POV_INSIDE_PLAYER, REPLAY_PLAYBACK,
BROADCAST_OVERLAY.

Replay buffer keeps `ROLLING_BUFFER_SECONDS=60` of
snapshots per active player. `save_replay(player_id,
event_kind, ts)` flips a copy of the buffer into a
permanent clip on any of four `ReplayEvent` values —
CRITICAL_KILL, WORLD_FIRST_NM, MAGIC_BURST_BOSS_KILL,
DEATH.

Broadcast metadata exposes NDI source names + RTMP
stream keys + scene names + element visibility — OBS
Studio reads it and configures the scene tree
automatically. `suggest_scene_switch(cue)` returns
director-suggested cuts ("boss_phase_changed → wide
combat", "critical_kill → tight on subject",
"world_first_nm → celebration overlay").

`director_cam_pick(scene_state)` maps a scene dictionary
(`scene_kind`, `tempo`, `focus_targets`) onto a shot
label — the same vocabulary `director_ai` already
speaks.

## Integration map

- `auth_discord` — `game_launcher` hands off to the
  Discord OAuth flow at `LauncherState.DISCORD_OAUTH_
  FLOW`. Predicate `oauth_complete` advances the
  launcher to SERVER_SELECTION.
- `character_creation` — `game_launcher.transition_to(
  CHARACTER_CREATION)` hands off the session to the
  creation steps from the prior batch. On return,
  state goes back to CHARACTER_SELECT with the new
  card registered.
- `cinematic_camera`, `lens_optics`, `film_grade` —
  `photo_mode` uses the same profile / lens / LUT ids
  the production team uses for trailer captures. The
  trailer master and the in-game player share a stack.
- `screen_effects` — `accessibility_options.should_show_
  screen_effect` is the predicate every effect spawn
  consults. REDUCED_MOTION suppresses HIT_SHAKE_HEAVY
  / DRAGON_BREATH_HEAT_HAZE / LEVITATE_BOB; REDUCED_
  FLASH suppresses MB_FLASH / PARALYZE_STATIC_CRACKLE /
  CHARM_PINK_HAZE / PETRIFICATION_GREY_FREEZE.
- `director_ai` — `spectator_mode.director_cam_pick`
  borrows the matrix vocabulary so the spectator
  director and the cutscene director cut the same way.
- `showcase_choreography` — `game_launcher` runs the
  `first_play_intro` sequence on first launch only.
- `net_replication` — `spectator_mode.push_snapshot` is
  fed by the same snapshot stream the replication tier
  emits; the rolling buffer is just the last 60s of
  network history per player.
- `dialogue_lipsync` + `voice_subtitle_track` —
  `accessibility_options.subtitle_renderable` returns
  the styled subtitle the lipsync stack reads from.
- `visible_health` — `spectator_mode.SpectatorSession`
  exposes `hp_bars_visible` so esports overlays can
  toggle the HP layer without touching the underlying
  health state.
- `zone_lighting_atlas` — `photo_mode.recommended_
  camera_for` and `game_launcher` character cards both
  read the per-zone hero shot URI.
- `hud_overlay` — `accessibility_options.apply_color_
  filter` is the last pass before the HUD pixel hits
  the framebuffer.

## Open-source toolchain

- **Input** — SDL2 for cross-platform HID, XInput for
  Windows gamepads, DirectInput for legacy / wheel /
  HOTAS, evdev on Linux, GameController.framework on
  macOS. The `InputDevice` enum names the layer that
  produces the events; the rebind layer is engine-
  agnostic.
- **Colorblindness** — Open Color Filter (OCF), the
  open-source Brettel-Vienot-Mollon LMS transform. The
  matrices in this module are placeholder coarse
  approximations; OCF supplies the canonical ones at
  runtime.
- **Screen reader** — UIA on Windows, NSAccessibility on
  macOS, AT-SPI on Linux. `SCREEN_READER_HOOKS` exposes
  the menu tree to those APIs.
- **TTS** — eSpeak NG (lightweight, system), Festival
  (BSD), Coqui TTS (neural, server-side optional).
- **Streaming** — NVIDIA NDI for LAN broadcasts, RTMP
  for Twitch / YouTube, WHEP (WebRTC-HTTP Egress
  Protocol) for low-latency browser viewers. OBS Studio
  reads the `broadcast_metadata_for` payload to build
  the scene tree automatically.
- **Photo capture** — OpenEXR for HDR export, libpng
  for PNG, FFmpeg for MP4 / GIF.

## Accessibility philosophy — every player can play

The accessibility module isn't a checklist of buttons.
It's a contract with the player: whatever you bring —
a colorblind eye, a one-handed grip, a tendency toward
motion sickness, an eye-tracker, a screen reader, an
aversion to spiders, photosensitive epilepsy — this
game has a setting for it.

Three rules:
1. **Default off, one click away.** Every flag is off by
   default so the launch experience is the intended
   one. But the settings panel is right there, every
   flag is one click, and the suggestion engine
   bubbles relevant flags up the moment the player
   reports a problem.
2. **No content gating.** Accessibility flags never lock
   content. A player on screen-reader + TTS + ASSIST_
   AIM + AUTO_FOLLOW_LEADER still beats the boss; the
   game is no easier or harder for them.
3. **Photosensitive-safe by toggle.** REDUCED_FLASH is
   the strict-safety mode. With it on, no effect in
   `screen_effects` can produce a strobe or sudden
   high-luminance pulse. Players with photosensitive
   epilepsy can play every part of the game.

## End-to-end scenario — a four-player demo session

Four players start Demoncore for the first time.

1. **Splash → title.** Each launcher boots. Splash plays
   for 1.2s and auto-advances to TITLE_SCREEN with the
   per-region background video — Japanese for player 1,
   English for players 2-4. Music swells on click.
2. **Patch + login.** All four pass PATCH_CHECK clean
   and land in LOGIN. Click "Sign in with Discord" →
   DISCORD_OAUTH_FLOW. Browser hand-off, OAuth back
   with `oauth_complete=True`, auto-advance to
   SERVER_SELECTION.
3. **Server + character.** All four pick `us_east`. All
   four are first-play, so all four go to CHARACTER_
   CREATION. They build characters via the steps from
   the prior batch.
4. **World load + cinematic intro.** WORLD_LOAD with
   `world_loaded=True` and `first_play_complete=False`
   → CINEMATIC_INTRO. The `showcase_choreography`
   `first_play_intro` sequence runs (95s).
5. **Input.** Player 1 plays JIS keyboard. Player 2 plays
   QWERTY. Player 3 plays Xbox controller. Player 4
   plays Steam Deck. Each device's default profile
   does the right thing without rebinding. Player 4
   rebinds DODGE to L4 — `rebind(char_id="p4", device=
   GAMEPAD_STEAM_DECK, action=DODGE, "L4")` is the only
   custom binding in the session.
6. **Accessibility.** Player 3 reports motion sickness
   in the launcher's onboarding poll. `suggest_flags_
   for(["motion_sickness"])` returns REDUCED_MOTION;
   the panel pre-toggles it. Player 2 has deuteranopia
   and enables COLORBLIND_DEUTERANOPIA — every HUD
   color (red for low HP, green for poison, etc.)
   flows through `apply_color_filter` before render.
7. **Photo mode.** Player 1 hits the photo-mode button
   in Bastok Markets. `enter_photo_mode("p1")` → ACTIVE_
   FREEROAM. `recommended_camera_for("bastok_markets")`
   returns (arri_alexa_35, cooke_s7i_75mm, 75mm).
   Player 1 picks `demoncore_trailer_master` as the
   filter, scrubs to 18.0 (sunset golden hour),
   overrides weather to "fog", pose-locks Player 4
   mid-skillchain, captures to PNG_8K. Sticker reads
   "Demoncore — bastok_markets — TheGalka".
8. **Spectator.** Player 1's friend Sam is watching on
   Twitch. Sam's stream client opens spectator
   session `spec1` watching player 1 in DIRECTOR_CAM
   mode. As Player 1 enters combat, `director_cam_
   pick({"scene_kind": "combat_close", "tempo":
   "fast"})` returns `handheld`. As Iron Eater enters
   phase 2, `suggest_scene_switch("boss_phase_changed")`
   returns the wide-combat scene; Sam's OBS scene tree
   cuts to it automatically.
9. **Replay.** Player 1 lands the killing magic-burst.
   `save_replay("p1", MAGIC_BURST_BOSS_KILL,
   now_ms)` returns a clip_id. The clip captures the
   last 60s ending at the kill. Sam posts it to social.
10. **Post-session.** All four players quit to
    CHARACTER_SELECT. Player 1's first-play flag is now
    True — next launch goes straight from WORLD_LOAD
    to IN_GAME, skipping CINEMATIC_INTRO.

## Three design hinges

1. **THE LAUNCHER IS A STATE MACHINE, NOT A SCRIPT.**
   Every transition is in the graph. Every USER edge is
   a button. Every AUTO edge is a predicate. Adding a
   new state ("update available, ready to apply") is
   one line in `_TRANSITIONS`. There is no hidden state
   stitched together with `if` ladders — the whole
   front-of-house is one declarative table.

2. **THE INPUT LAYER IS DEVICE-AGNOSTIC.** The game
   never asks "is W pressed". It asks "is MOVE_FORWARD
   pressed". The mapping layer translates between the
   physical input and the action. The QWERTY player and
   the AZERTY player are running the same gameplay
   code; the AZERTY player's `MOVE_FORWARD` is bound to
   Z and the QWERTY player's is bound to W. The
   gameplay code doesn't know.

3. **ACCESSIBILITY IS A PASS, NOT A FEATURE.** Color
   filter is a pass over every rendered pixel. Screen
   effect suppression is a pass over every effect
   spawn. Subtitle styling is a pass over every spoken
   line. The accessibility module never owns gameplay
   state — it owns the rendering and presentation
   passes that adapt the existing gameplay to the
   player in front of it. A player can flip every flag
   on or off mid-session and the game keeps running.

The previous batch put the *players* in the world. This
one builds the front door, the keyboard, the wheelchair
ramp, the camera, and the broadcast booth — everything
the demo needs to walk out the door as a product.
