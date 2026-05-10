# World streaming + Bastok-pattern propagation

## Vision

The previous batch shipped one zone at Bastok-Markets quality —
fully dressed, fully cast, fully choreographed, packaged into
one demo manifest the producer could hand to a publisher.
This batch makes Bastok the *baseline*, not the *target*.

The grand demo we're aiming at is a single five-minute camera
move that starts at Cid's anvil in Bastok Mines, walks out the
North Arch into Bastok Markets, leaves the city through the
gate, crosses North Gustaberg, drops into Pashhow Marshlands,
lifts off on the airship, lands in Port Jeuno, walks the plaza,
boards another airship, lands in Port Sandy, threads through
the cathedral, takes a third airship, lands at Port Windurst,
and finishes in the canopy. **Three nations. Five zones. Zero
load screens.**

To get there we need two things:

  1. Every zone has to look as good as Bastok Markets — not
     by hand-building 41 zones the way we hand-built one, but
     by *codifying the Bastok pattern* and propagating it.
  2. The engine has to stream the world tile by tile so the
     player never sees a load screen — UE5 World Partition,
     One File Per Actor (OFPA), Streaming Source Components,
     Levels of Detail (LOD) per-tile.

This batch is the five-module backbone for both.

## The five modules

### `server/zone_pattern_template/` (30+ tests)

Codifies the Bastok-Markets demo pattern as a reusable
template applied to every other zone. Six archetypes —
NATION_CAPITAL (Bastok itself; dense, cinematic, vendor-
heavy), OUTPOST_TOWN (Selbina/Norg/Mhaura; small, cozy, rest-
stop), OPEN_FIELD (Konschtat-style; wide, atmospheric, low
NPC), DUNGEON_DARK (Crawler's Nest; claustrophobic, deep
shadows), BEASTMAN_FORTRESS (Davoi/Beadeaux/Castle Oztroja;
green-tinted, hostile, prop-heavy), ENDGAME_INSTANCE (Sky/
Sea/Limbus/Dynamis; exotic, surreal lighting). Each archetype
has a default template recording target dressing count, target
roster size, NPC archetype mix, mob archetype mix, lighting
profile, atmosphere preset, render preset, choreography beat
target, asset-upgrade priority. `archetype_for(zone_id)`
maps any zone_id to its archetype using a hand-tuned override
table for the canonical FFXI zones plus a name-based heuristic
for anything not in the table. `apply_template_to(zone_id,
archetype)` registers a per-zone application and reports
completeness, computed from dependency-injected lookups
against zone_dressing's count and character_model_library's
roster size — defaults to zero so unit tests don't need the
whole project graph wired. `all_zones_progress()` returns
zone_id -> completeness_pct for a producer dashboard.

### `server/world_streaming/` (30+ tests)

UE5 World Partition / OFPA tile-streaming math. A `StreamTile`
is the unit of streaming — a few hundred meters per tile, with
bounds, asset cost in MB, LOD-level count, and explicit
neighbor IDs. As the player moves, tiles inside the prefetch
radius (default 200 m) start LOADING; tiles inside the keep
radius (default 500 m) are kept ACTIVE; tiles outside the
evict radius (default 1500 m) move to COOLING and get dropped
when memory pressure rises. The state machine is
UNLOADED -> LOADING -> LOADED -> ACTIVE -> COOLING -> UNLOADED.
`plan_streaming_for(player_pos, platform)` returns the list of
(tile_id, action) decisions and mutates the internal state
machine. Eviction picks the cheapest cooling tile under
pressure, ties broken by furthest distance. Memory budgets:

| Platform        | Budget    |
|-----------------|-----------|
| PC_ULTRA        |  24 GB    |
| PC_HIGH         |  16 GB    |
| PS5             |  12 GB    |
| XBOX_SERIES_X   |  12 GB    |
| XBOX_SERIES_S   |   8 GB    |

### `server/zone_handoff/` (30+ tests)

The seamless boundary crossing. A `ZoneBoundary` is a volume
between zone_a and zone_b with a prefetch distance and a
predicted player velocity. `handoff_for(player_pos, velocity,
current_zone)` returns one decision per boundary touching the
current zone — most are NO_ACTION; the interesting ones are
PREFETCH (player is in the prefetch ring; start streaming the
target zone), CROSS (player is inside the boundary volume;
swap zone tag), or HITCH (prefetch failed; we accept a 200 ms
stall rather than fall back to a load screen). NPCs mid-pursuit
(Fomor, beastmen) carry their session_id across — the boundary
is a tag change for them, not a teleport. Multiplayer note: in
the authoritative server model the boundary crossing is purely
client-side prediction; the server holds the canonical position.

### `server/zone_lighting_atlas/` (30+ tests)

Per-zone cinematic lighting profile catalog. A
`LightingProfile` records mood descriptor, key/fill/back
kelvin and intensity, sky dome URI, HDRI URI, sun angle at
noon, fog density and color, god-ray strength, atmospheric-
perspective falloff distance, plus recommended LUT, camera
profile, and lens profile (cross-referencing film_grade,
cinematic_camera, lens_optics). Twelve hand-tuned distinctive
zones:

| Zone               | Mood                                | LUT             | Camera           |
|--------------------|-------------------------------------|-----------------|------------------|
| bastok_mines       | smelter-warm industrial twilight    | Vision3 500T    | ALEXA 35         |
| bastok_markets     | industrial daylight, dust shafts    | Vision3 250D    | ALEXA 35         |
| south_sandoria     | medieval-warm cathedral             | Eterna          | RED V-Raptor     |
| windurst_woods     | jewel-tone candy color              | Cinestyle       | Sony Venice 2    |
| lower_jeuno        | cosmopolitan neutral grade          | Demoncore Std   | ALEXA 35         |
| norg               | twilight pirate cove                 | Bleach Bypass   | BMD Ursa 12K     |
| north_gustaberg    | golden hour rolling plains          | Vision3 250D    | ALEXA 35         |
| pashhow_marshlands | overcast green-grey, low haze       | Eterna          | Sony Venice 2    |
| tahrongi_canyon    | red-rock dusk, monolithic shadows   | Vision3 500T    | ALEXA 35         |
| davoi              | sickly green-tint orcish swamp      | Bleach Bypass   | RED V-Raptor     |
| crawlers_nest      | subterranean amber, pheromone glow  | Day-for-Night   | BMD Ursa 12K     |
| beadeaux           | cold-blue moonlight on quadav stone | Day-for-Night   | ALEXA 35         |

Other zones get archetype-default profiles via `derive_for(
zone_id, archetype)`. The atlas validates fill_ratio in [0,1],
fog_density in [0,1], god_ray_strength in [0,1], fog_color in
[0,255]^3, atmospheric_perspective_meters > 0.

### `server/world_demo_packaging/` (30+ tests)

The multi-zone manifest packager. A `WorldDemoBuildManifest`
holds `zone_ids`, `entry_zone_id`, the `exit_zone_ids` camera-
path sequence, choreography per zone, the boundary handoffs
required, the streaming strategy (ALL_RESIDENT for small demos
where every zone fits in memory, RING_PRELOAD for known camera
paths where we prefetch the ring ahead, ON_DEMAND for the
open-world drone-camera flythrough), the target platform, the
total estimated size in GB, and the validation status. Three
predefined demos: `bastok_to_konschtat_walkthrough` (3 zones,
RING_PRELOAD, fits PC_ULTRA easily); `three_nations_grand_tour`
(5 zones — Bastok / Sandy / Windy with Jeuno airship transit,
ALL_RESIDENT for the trailer master); `full_world_flythrough`
(every zone, ON_DEMAND, drone-camera mode for the trailer's
opening). Validation cross-checks zone existence in zone_atlas,
boundary existence in zone_handoff, lighting profile existence
in zone_lighting_atlas, and platform memory budget — all four
existence-check callables are dependency-injected.

## Integration with the rest of the stack

```
                player position
                       |
                       v
           +-------------------------+
           |   world_streaming       |
           |   (StreamTile + LOD     |
           |    + memory budget)     |
           +-------------------------+
                       |
                       v
           +-------------------------+
           |   zone_handoff          |
           |   (boundary + prefetch  |
           |    + NPC pursuit)       |
           +-------------------------+
                |             |
                v             v
   +----------------+   +-----------------------+
   | seamless_world |   | aggro_system / mob_   |
   | (#154 cross-   |   | respawn / weather /   |
   |  zone aggro)   |   | time-of-day continuity|
   +----------------+   +-----------------------+
                       |
                       v
           +-------------------------+
           |   zone_pattern_template |
           |   (Bastok pattern at    |
           |    archetype scale)     |
           +-------------------------+
                |             |
                v             v
   +----------------+   +-----------------------+
   | zone_dressing  |   | character_model_      |
   | (per-zone set- |   | library (per-zone     |
   |  decoration)   |   |  roster + LODs)       |
   +----------------+   +-----------------------+
                       |
                       v
           +-------------------------+
           |   zone_lighting_atlas   |
           |   (per-zone mood +      |
           |    camera + LUT)        |
           +-------------------------+
                       |
                       v
   +-----------------+ +-----------------------+
   | atmospheric_    | | film_grade /          |
   | render / god    | | cinematic_camera /    |
   | rays / LED feel | | lens_optics           |
   +-----------------+ +-----------------------+
                       |
                       v
           +-------------------------+
           |   showcase_choreography |
           |   + director_ai +       |
           |   + render_queue        |
           +-------------------------+
                       |
                       v
           +-------------------------+
           |   world_demo_packaging  |
           |   (multi-zone manifest) |
           +-------------------------+
```

## UE5 reference

  - **World Partition** — UE5's open-world streaming. Splits
    a level into a 3D grid of cells; cells are loaded based on
    Streaming Source position(s). Replaces the older
    LevelStreaming volumes.
  - **One File Per Actor (OFPA)** — every actor stored as a
    separate `.uasset`. Lets multiple devs work on one zone
    without lock collisions; lets the runtime load actors
    individually rather than the whole level.
  - **Streaming Source Components** — what the streamer
    follows. Player pawn carries one; cinematic cameras carry
    one when active. Multiple sources stream a union of cells.
  - **Hierarchical Levels of Detail (HLOD)** — the
    pre-baked far-distance proxy mesh for whole regions of the
    world. We map it to our `lod_levels` field on `StreamTile`.
  - **Mass AI / Mass Entity** — UE5's data-oriented entity
    framework. Crowd simulation in nation capitals targets
    Mass Entity for thousand-NPC scenes.

## Pre-fetch tuning notes

  - 200 m prefetch radius assumes player walking velocity
    18 km/h (5 m/s). At chocobo gallop velocity 36 km/h
    (10 m/s), bump to 400 m. At airship cruise 100 km/h,
    bump to 1500 m and warn the streamer.
  - Boundary prefetch volumes should overlap world-streaming
    prefetch radii. Specifically, boundary prefetch ring
    should ALWAYS be larger than the in-zone tile prefetch
    ring, so we start preloading the *next zone* before the
    *current zone* ends streaming local tiles.
  - On XBOX_SERIES_S we drop the keep radius from 500 m to
    300 m. The player loses tile resolution during sprints
    but never loses the world.
  - HITCH fallback (default 200 ms) is the *graceful
    degradation* path. Better than a load screen; worse than
    a clean crossing. The producer's dashboard warns if more
    than 1% of crossings hitch in QA.

## Memory budget table (tile-level)

| Platform        | Budget   | Tiles @ 200 MB | Tiles @ 100 MB |
|-----------------|----------|----------------|----------------|
| PC_ULTRA        |  24 GB   |     ~120       |    ~240        |
| PC_HIGH         |  16 GB   |      ~80       |    ~160        |
| PS5             |  12 GB   |      ~60       |    ~120        |
| XBOX_SERIES_X   |  12 GB   |      ~60       |    ~120        |
| XBOX_SERIES_S   |   8 GB   |      ~40       |     ~80        |

A typical FFXI zone is 3-8 tiles. The XBOX_SERIES_S can hold
~5 zones of NATION_CAPITAL density resident, ~10 zones of
OPEN_FIELD density. The three-nations grand tour (5 zones,
ALL_RESIDENT) fits PC_ULTRA at 21.5 GB; on XBOX_SERIES_S the
strategy automatically downshifts to RING_PRELOAD.

## What this batch unlocks

The producer can hand the engineer one call —
`pkg.three_nations_grand_tour_default()` — and get back a
manifest that says: here are the five zones, here are the
boundary handoffs, here is the choreography per zone, here
is the streaming strategy, here is the estimated GB and
whether it fits the target platform. `validate(manifest_id)`
cross-checks every zone exists in zone_atlas, every boundary
exists in zone_handoff, every zone has a lighting profile in
zone_lighting_atlas. If anything is missing, the report says
*exactly what*. If the manifest passes, the render farm can
go.

The next batch is the actual content build — applying the
templates to all 41 zones, registering boundaries for every
adjacent pair, populating lighting profiles for the remaining
~30 zones — but the framework is now in place. From here, it's
data, not code.
