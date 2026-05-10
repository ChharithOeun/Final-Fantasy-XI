# Marketing and Release

The demo is production-ready. It boots from a launcher,
runs on every keyboard layout, respects every
accessibility flag, exposes a cinematic-grade photo
mode, and broadcasts a clean spectator feed. The work
now is *getting it seen*. By investors. By publishers.
By journalists. By players. This batch is the layer
between "the demo runs" and "the demo is on every
storefront, in every press inbox, on every social
network, in every age-rating board's submission queue."

Five modules:

  server/trailer_generator/
    Auto-assemble trailers from the same ingredients
    the demo already builds — the rolling replay
    buffer from spectator_mode, the showcase sequences
    from showcase_choreography, and the director_ai
    shot grammar. Seven TrailerKind values cover every
    marketing context: TEASER_30S, STORY_60S,
    GAMEPLAY_2MIN, DEEP_DIVE_5MIN, CONVENTION_
    SIZZLE_90S, LAUNCH_PROMO_90S, FEATURE_VERTICAL_
    VIDEO_30S. Each has its own montage tempo (fast
    cuts for teasers, slow cuts for deep dives) and
    its own validation rules (TEASER must hide
    spoilers, STORY must contain intro+conflict+
    resolution, GAMEPLAY must show real mechanics).
    Edits sync to music. Title cards open, middle, and
    end the cut. trailer_for_event() is the auto-share
    hook — called by spectator_mode.save_replay() on a
    CRITICAL_KILL, it produces a 30-second vertical
    clip the player can post without opening an editor.

  server/press_kit/
    Everything a journalist needs for a cover story in
    one zip. Nineteen PressAsset kinds cover the
    canonical deliverables — every logo orientation,
    every key-art piece, gameplay screenshots, beauty
    screenshots, b-roll, the trailer bundle, factsheet,
    bio sheet, contact card, embargo notice, EULA,
    privacy policy, the four-board age-rating bundle
    (ESRB / PEGI / USK / CERO), the accessibility
    statement, and the developer FAQ. Each asset tracks
    its required formats (PNG_4K, PNG_8K, EPS, SVG,
    PDF, MP4_4K, MP4_HD, TXT, JSON) and a version
    history so the recipient always gets the latest.
    Bundles lock until embargo_until_iso. Per-recipient
    download tokens are issued only after a journalist
    is added to the whitelist. The indie outlet gets
    screenshots + factsheet; the trade rag gets the
    full bundle. Violation logs are kept.

  server/social_clip_generator/
    Per-platform clips with auto-crop, auto-caption,
    and platform-aware music. Eight Platform values
    with explicit specs: TIKTOK, INSTAGRAM_REEL,
    YOUTUBE_SHORTS, TWITTER, FACEBOOK_REEL, BLUESKY,
    MASTODON, LINKEDIN. Each spec carries aspect_ratio
    (9:16 portrait or 16:9 horizontal), max_duration_s,
    music_required (TikTok yes, LinkedIn no),
    captions_required (every modern platform yes),
    max_file_size_mb, and a hashtag_culture set —
    #FYP on TikTok, #GameDev on LinkedIn. Auto-crop
    intelligently re-frames 16:9 sources to 9:16 by
    tracking the focus point (character bounding box
    from name_plate_system, or director_ai's
    focus_xy). Auto-caption pulls dialogue from voice_
    swap_orchestrator timelines plus spell-name /
    weaponskill-name overlays. bulk_render runs the
    same set of replays through every listed platform
    in one pass.

  server/screenshot_pipeline/
    Bulk capture + auto-tag + curate. Six CapturePass
    kinds: HERO_ZONE_SET (one beauty per zone at
    golden-hour), CHARACTER_PORTRAITS (head/medium/
    wide per hero NPC), COMBAT_MOMENTS (during
    showcase_choreography beats), GROUP_SHOTS (party
    comps, formations), ENVIRONMENT_DETAIL (close-up
    texture work), MARKETING_BEAUTY (curated 12-shot
    best-of for the press kit). Auto-tagging adds
    zone, races, archetype, weather, time of day,
    has_combat, has_dialogue. Quality rating runs
    three heuristics — composition (rule-of-thirds),
    face (no closed eyes), exposure (no clipping) —
    averaged to a 0..5 star score. curated_set_for(
    MARKETING_BEAUTY, count=12) returns the top
    twelve by score; that's the press-kit hero set.

  server/release_manifest/
    Demo release packaging per-platform with age
    ratings, EULAs, and signing. Fourteen Release_
    Platform values: STEAM, EPIC_GAMES_STORE, GOG,
    PLAYSTATION_STORE_PS5, XBOX_STORE_SERIES_XS,
    NINTENDO_ESHOP_SWITCH, NINTENDO_ESHOP_SWITCH_2,
    MAC_APP_STORE, IOS_APP_STORE, ANDROID_PLAY_STORE,
    WEB_BROWSER (WebGL/WebGPU), STREAMING_GEFORCE_NOW,
    STREAMING_LUNA, STREAMING_BOOSTEROID. Each
    platform carries its tech-requirements blob,
    age-rating board (ESRB / PEGI / USK / CERO / ACB /
    GRAC), DRM kind (Steam DRM, EGS, Denuvo, platform-
    native, or None), price_usd, region-lock set,
    launch date, and the supported locale matrix.
    DemoBuildConfig wraps the per-build settings —
    time_limit_minutes (0 = unlimited), feature flags
    (TRAILER_LOOP / MULTIPLAYER / PHOTO_MODE /
    SPECTATOR), watermark (PRESS / EVENT / RETAIL /
    NONE), checksum, signing key id. validate_age_
    rating filters submitted content descriptors
    against each board's vocabulary — ESRB wants
    "violence_stylized" / "language_mild" / "gambling_
    simulated"; PEGI wants "violence_low" / "fear" /
    "online_interactions"; USK wants spelled-out
    German categories.

## Integration with the existing stacks

The marketing layer is *consumption* — it reads from
the cinematic, spectator, photo, showcase, and world-
demo-packaging stacks and emits artifacts the team
can hand to investors, publishers, journalists, and
players.

  trailer_generator ← spectator_mode.replay_buffer +
                       showcase_choreography +
                       director_ai shot grammar +
                       scene_pacing.murch_six_axis +
                       music_spotting cue tracks +
                       voice_role_registry credits

  press_kit         ← screenshot_pipeline curated sets +
                       trailer_generator output +
                       voice_role_registry bios +
                       accessibility_options statement +
                       release_manifest rating bundle

  social_clip_      ← spectator_mode replays +
   generator         trailer_generator outputs +
                       music_pipeline royalty-free cues +
                       voice_swap_orchestrator captions +
                       name_plate_system bounding boxes

  screenshot_       ← photo_mode camera + lens catalog +
   pipeline          zone_lighting_atlas golden-hour +
                       character_model_library NPCs +
                       showcase_choreography beat-aligned
                       capture triggers

  release_manifest  ← world_demo_packaging base manifest +
                       demo_packaging build artifacts +
                       accessibility_options statement +
                       auth_discord per-platform account
                       link policies

## The press-kit philosophy

"Everything they need for a cover story in one zip."
The dopresskit.com convention is six required assets
the moment you hit Download — primary logo, hero key
art, a gameplay screenshot, a factsheet, a contact
card, and the embargo notice. Anything else is gravy.
The kit assembler enforces those six on validate_
kit(); a recipient with embargo access and a download
token gets a single self-contained zip with no follow-
up emails required.

Embargo is a hard gate. is_embargo_active(kit_id,
now_iso) is the only thing CDN edge nodes ever ask;
before that timestamp, no asset is served to anyone
who isn't on the whitelist. Every download is logged
against the journalist whitelist; violations are
recorded but not prevented (the trust contract is the
embargo, not DRM).

## Open-source toolchain

The marketing pipeline composes off-the-shelf tools,
not custom binaries. The release picks the same
toolchain every indie team uses, so contractors and
freelancers can drop in without learning a bespoke
stack:

  FFmpeg                — clip generation, crop,
                          caption burn-in, transcode.
                          The social clip generator
                          emits FFmpeg-compatible
                          filter graphs.
  ImageMagick           — batch screenshot conversion
                          (PNG_8K → JPG_WEB), sticker
                          overlay rendering.
  DaVinci Resolve       — color grading and timeline-
                          based trailer assembly, with
                          XML export the trailer_
                          generator's shot list maps
                          onto.
  OBS Studio            — capture device for stream-
                          to-trailer raw footage,
                          consumes the broadcast
                          metadata from spectator_
                          mode.
  NDI                   — multi-machine broadcast
                          interconnect (one machine
                          captures, one renders, one
                          publishes).
  Twitch IRC            — chat overlay binding for
                          esports spectator output.
  OpenPressKit (the     — JSON format reference for
   dopresskit.com)        the press-kit bundle layout.
                          Every kit emitted is
                          compatible with the open
                          press-kit specification so
                          third-party aggregators
                          (IndieDB, Game Developer
                          newsletters) can scrape it
                          automatically.

## End-to-end scenario — March 2026 reveal

  1. Marketing schedules the reveal for March 15 at
     17:00 UTC. PressKit.build_kit("March 2026
     Reveal", embargo_until_iso="2026-03-15T17:00:00Z",
     ...) creates kit_1.

  2. The screenshot pipeline runs HERO_ZONE_SET (one
     per zone) and MARKETING_BEAUTY (forty candidates).
     rate_quality scores each. curated_set_for(
     MARKETING_BEAUTY, count=12) selects the top
     twelve. Those twelve register as KEY_ART_HERO +
     SCREENSHOT_BEAUTY in the press kit.

  3. The trailer generator builds the reveal package:
     TEASER_30S for the embargo break, STORY_60S for
     the press release, GAMEPLAY_2MIN for the deep-
     dive YouTube embed, CONVENTION_SIZZLE_90S for the
     GDC booth. validate() runs on each — TEASER
     spoiler check passes, STORY structure check
     passes.

  4. The social clip generator bulk_renders TEASER_30S
     across all eight platforms — same source, eight
     output specs. TikTok gets 9:16 with auto-crop
     centered on the hero character, captions
     burned in, hashtag culture #FFXI #FFXIDemoncore
     #FYP. LinkedIn gets 16:9, no music, professional
     pacing, #GameDev #IndieGame.

  5. Press kit grants access. Kotaku gets the full
     bundle. The indie outlet gets screenshots +
     factsheet only. Tokens generated. Embargo
     active.

  6. March 15, 17:00 UTC. is_embargo_active returns
     False. Download tokens unlock. The bundle ships.

  7. ReleaseManifest.build_release goes out to all
     fourteen storefronts. validate_age_rating runs
     per-board with the descriptors the team
     submitted — ESRB gets "violence_stylized" +
     "language_mild" + "gambling_simulated" (chocobo
     races); USK gets "gewalt_stilisiert" and
     "gluecksspiel"; CERO gets "violence_stylized" +
     "gambling". sign_build with key_2026_release.
     The build is ready for store submission.

## Three design hinges

1. EVERY MARKETING ARTIFACT IS DERIVED, NOT AUTHORED.
   The trailer is not a hand-cut Premiere project —
   it's an auto-assembled cut from the same replay
   buffer that spectator_mode already records. The
   press-kit screenshots are not hand-curated PNGs —
   they're the top-twelve auto-scored shots from
   MARKETING_BEAUTY. The social clips are not bespoke
   exports — they're per-platform-spec re-frames of
   the trailer. Re-running marketing is one function
   call, not one week of artist time.

2. EMBARGO IS A TIMESTAMP, NOT A POLICY DOCUMENT.
   is_embargo_active(kit_id, now_iso) returns a bool.
   The CDN edge node asks it on every download
   request. Before the embargo, no one outside the
   whitelist gets a byte. After the embargo, anyone
   with a valid token does. The whole social contract
   is reduced to one comparison; the trust failure
   mode (the journalist leaks anyway) is logged but
   not prevented in software.

3. EVERY PLATFORM IS A SPEC, NOT A SPECIAL CASE. The
   social clip generator does not have special code
   for TikTok. It has a PlatformSpec for TikTok.
   Adding a new platform (BeReal? Threads? Lemmy?) is
   one register_platform_spec call. The release
   manifest does not have special code for Switch 2.
   It has a PlatformSpec for Switch 2. Adding a new
   storefront (the next console generation, a new
   streaming service) is one register_platform call.

The previous batch built the polish layer that turned
the tech demo into a shippable product. This one
builds the layer between the shippable product and
the journalist's inbox.
