# NETWORKING & MULTIPLAYER FUNDAMENTALS

## Vision

FFXI's defining moment is "you turn the corner in
La Theine and three Galkas are running past you laughing,
chatting in voice, on their way to a campaign battle". The
demo, until this batch, was a single-player walking simulator
through a beautifully presented world — combat camera,
visible HUD, foley-rich audio, but the only living thing in
the frame was the one you were piloting.

This batch lays the wire that makes the world an MMO again.
Five modules: authoritative entity replication with client
prediction; lag-compensated hit registration with anti-cheat;
real-time party state replication; cross-server zone handoff
with session continuity; and Mumble-protocol spatial voice
chat.

Together they are the difference between *the world plays*
and *players play in the world*.

## The Five Modules

### 1. `server/net_replication/`

Authoritative server entity replication with client
prediction. EntityKind covers the seven things the server
syncs (PLAYER, NPC, MOB, PROJECTILE, DROPPED_ITEM,
DESTRUCTIBLE_PROP, ENVIRONMENT_TRIGGER). Snapshot is the
on-wire frame: entity_id + kind + pos + vel + yaw + hp% +
mp% + tp + status_flags + anim_state + server_tick +
timestamp_ms.

Replication is *tiered*: LOCAL_PLAYER 60Hz, NEARBY_PLAYER
30/10/2Hz by distance, MOB_NEARBY 30Hz combat / 10Hz idle,
PROJECTILE 60Hz, STATIC on-change. Interest culling: each
client only receives entities within `interest_radius_m`
(default 200m). Party/alliance members extend the radius
1.5x because the social link is the gameplay.

Client prediction: client extrapolates LOCAL_PLAYER and
PROJECTILE positions using last velocity + the 100ms
snapshot interval; server reconciles on each snapshot;
client snaps if delta > 50cm, otherwise blends to authority
over 100ms.

Snapshot interpolation: remote entities render 100ms in the
past — the client always has two snapshots bracketing render
time and lerps between them. This is the trick that makes
10Hz updates look like 60Hz smooth motion.

### 2. `server/net_lag_compensation/`

Rewinds server time to verify hits based on what the client
saw. The Counter-Strike / Overwatch / Valorant pattern,
applied to FFXI's combat: server keeps `HISTORY_WINDOW_MS=
1000` of past snapshots; on hit claim, rewinds the target
to the time the client saw it, validates geometry (in range,
LoS, not behind cover), accepts or rejects.

Anti-cheat signals: TELEPORT_HACK (attacker position not
physically reachable from last snapshot), IMPOSSIBLE_REACH
(weapon out of range), PING_TOO_HIGH (>500ms),
RAPID_FIRE_BEYOND_RATE (faster than weapon catalog allows),
OUT_OF_RANGE_REPEATED (3 strikes), POSITION_MISMATCH (client
claim diverges from server rewind by >30cm), BROKEN_LOS,
REWIND_PAST_HISTORY. Signals are logged per-player;
anti_cheese subscribes and escalates.

Weapon catalog: dagger 2.5m, sword/katana 3m, great-sword
3.5m, polearm 4.5m, bow 25m, crossbow 22m, spell-short 20m,
spell-long 35m, h2h 2m, staff 3.5m. Min-interval per weapon
kind enforces rate-of-fire.

### 3. `server/net_party_sync/`

Real-time party state replication. PartyMemberState carries
HP/MP/TP, zone_id, position, status_effects, current_target,
is_pulling, role (TANK/HEAL/DD/SUPPORT/UTILITY). Sync 5Hz
in same zone, 1Hz cross-zone — cross-zone strips position
(no minimap pin for a healer in Sandy) but keeps HP/MP/TP/
zone/role/status so the party-frame HUD stays live.

Follow-the-leader: set_following(member, leader) routes the
follower's movement input to "pathfind toward leader"; break
when distance exceeds `following_radius` (default 5m).
Auto-formation: TANK 8m forward of group center, HEAL 8m
back, DD 4m flanks left/right, SUPPORT behind, UTILITY
behind-flank. Off by default; toggled per-party.

party_health_summary returns (player_id, hp, mp, tp) tuples
ordered leader-first then alphabetical — direct input for
the hud_overlay party frame from the prior batch.

### 4. `server/net_zone_handoff/`

Cross-*server* zone handoff. zone_handoff (prior batch)
handles same-server cinematic-fade transitions. This module
covers the case where the target zone is on a *different*
game server — and pulls it off without a load screen.

Six-step protocol: SOURCE flags HANDING_OFF and locks state;
SOURCE serializes inventory + buffs + party_id + friends +
quest_progress + voice_chat_session_id with a SHA-256
checksum; TARGET receives blob, verifies checksum, moves
LOADING_IN; SOURCE destroys local entity; TARGET sends
LOAD_COMPLETE; CLIENT renders the same 200ms cinematic fade
zone_handoff uses for same-server cases.

Failure modes: target unreachable → snap back to source;
checksum / serialization mismatch → kick to safe zone (Mog
House if you have one, Ru'Lude Gardens otherwise); network
split → reconnect picks up from last ack. Pending handoffs
are observable so monitoring can spot stuck transitions.

### 5. `server/net_voice_chat/`

Mumble-protocol spatial voice chat. Seven channels:
ZONE_PROXIMITY (30m spatial, same-zone, 3D), PARTY (any
zone), LINKSHELL (LS members online), ALLIANCE (60m
proximity), WHISPER_DIRECT (point-to-point), STAFF_GM,
PUBLIC_AUCTION (Jeuno AH only).

Spatial falloff: 0-3m full gain, 3-15m lerp to -6 dB,
15-30m lerp to -24 dB, >30m culled. Wall occlusion reduces
gain by reverb_zones damping. VAD at -40 dB drops silent
packets at the source.

Ducking: when a PARTY or WHISPER packet arrives, all
ZONE_PROXIMITY voices duck -6 dB so the important channel
reads. Per-player mute + admin-managed global blacklist.
packets_for(receiver) returns an ordered list — GM > whisper
> party > alliance > LS > AH > proximity — with gain pre-
applied so the client just decodes and mixes.

## Integration

### LSB existing UDP/TCP transport

LSB (LandSandBoat) currently runs TCP for auth/chat and UDP
for game traffic. The five modules in this batch are
*transport-agnostic*: they ship schemas and algorithms.
The integration path is twofold:

1. **LSB adopts the schemas directly** — the C++ team
   re-implements Snapshot / HitClaim / PartyMemberState in
   the existing UDP packet handlers, calling out to a
   Python sidecar for the validation paths (rewind, cheat
   detection, replication-tier decisions).
2. **Python test rig drives end-to-end scenarios** — every
   module here can be wired into a pytest-based world
   simulator that asserts "if player A claims hit on B at
   T=1000ms with 80ms ping, the server rewinds B by 80ms
   and accepts" without any C++ in the loop.

### Cross-module wiring

```
party_system (membership)  -->  net_party_sync (replication)
                                       |
                                       v
                                hud_overlay party frame
                                       ^
                                       |
visible_health, dps_meter, hp/mp/tp bars

zone_handoff (same-server)
       +
world_streaming (geometry prefetch)
       +
net_zone_handoff (cross-server)
       |
       v
seamless_world (no load screens, ever)

aggro_system + targeting_system
       |
       v
net_replication (mob tier scaling 30Hz / 10Hz)
       |
       v
net_lag_compensation (hit claim verification)
       |
       v
anti_cheese (escalation: warn → shadowban → ban)

voice_profile_registry + audio_listener_config + reverb_zones
       |
       v
net_voice_chat (spatial gain + wall damping)
       |
       v
surround_audio_mixer
```

## Anti-cheat philosophy: trust the server, verify the client

The client can claim anything. The server validates everything.

- Every hit goes through `submit_claim` with the client's
  stated time + position. The server rewinds the target,
  measures geometry, and decides.
- Every cheat signal is logged. A single TELEPORT_HACK
  might be packet loss; three IMPOSSIBLE_REACH in 30 seconds
  is a confirmed hack. The `anti_cheese` module subscribes
  to `detect_cheats_for` and runs the escalation policy
  (warn → kick → 24h ban → permaban).
- Tolerances are tuned for honest play: 30cm position
  tolerance covers normal network jitter; 1m reach
  tolerance covers melee hitbox slack; 0.8x rapid-fire
  tolerance covers slight server jitter on weapon recasts.
  Cheaters trip the tolerances; honest players don't.

## Open-source stack

| Component         | Library                  | License       |
| ----------------- | ------------------------ | ------------- |
| UDP transport     | ENet                     | MIT           |
| Higher-level net  | Yojimbo (Glenn Fiedler)  | BSD-3-Clause  |
| WebRTC fallback   | libdatachannel           | MPL-2.0       |
| Voice codec       | Opus (RFC 6716)          | BSD-3-Clause  |
| Voice protocol    | Mumble positional        | BSD-3-Clause  |
| Crypto checksums  | SHA-256 (stdlib)         | PSL           |
| Snapshot encoding | flatbuffers / msgpack    | Apache-2 / MIT|

ENet for the UDP socket layer is what most indie MMOs run.
Yojimbo wraps ENet with the channel/reliability primitives
Quake III pioneered and Glenn Fiedler documented for the
modern era. libdatachannel is the WebRTC fallback for
browser-based clients (Demoncore-in-the-browser is a future
batch, but the protocol bridge is ready). Opus is mandatory
— it's the only codec that handles 8kbps voice at 20ms
latency. Mumble's positional audio extensions are a stable
wire format anyone can implement; the alternative would be
inventing one and we don't need that headache.

## One scenario, end to end

Three players in a party — Tank in Bastok Mines, Healer in
Sandoria, DD also in Bastok Mines — coordinating a Fomor
mission run.

1. **Voice**: Tank speaks. `net_voice_chat` routes the
   packet — PARTY channel, scope `party_xyz`. DD receives
   it at full gain. Healer, in a different zone, also
   receives at full gain (PARTY is not spatial). VAD passes
   because Tank's mic activity is -18 dB. The proximity
   chat from a passing goblin near DD (-30 dB activity, in
   Bastok Mines, 8m away from DD) is ducked -6 dB because a
   PARTY packet is in the same batch.
2. **Replication**: DD's `net_replication` system gets 30Hz
   updates of the Tank (same zone, 12m away,
   NEARBY_PLAYER_CLOSE tier) and 10Hz updates of the
   Healer's cross-zone shell snapshot. The goblin (idle,
   mob, 15m) ships 10Hz; if it engages, flips to 30Hz.
3. **Combat**: Tank claims a hit on the goblin —
   `submit_claim` rewinds the goblin 60ms, validates
   sword-range 3m, accepts. Healer in Sandoria sees Tank's
   HP drop on her party frame (1Hz cross-zone sync).
4. **Cross-server move**: DD steps through a zone line
   into Pashhow Marshlands, which is on a different game
   server. `net_zone_handoff.initiate_handoff` runs the
   six-step protocol. Voice session ID is carried in the
   serialized state — the new server rejoins the same
   PARTY channel and DD's chat never drops a word.
5. **Cheater detected**: A separate player tries an
   IMPOSSIBLE_REACH on a 50m sword swing. Cheat signal
   logged. Three more within 90s → OUT_OF_RANGE_REPEATED.
   `anti_cheese` reads the signal log, escalates to
   shadowban. The honest party never noticed.

## Three design hinges

1. **The server is the truth, the client is the
   interpretation.** Every position, every HP, every hit is
   server-authoritative. The client predicts and extrapolates
   for *feel*; the server reconciles and corrects. When
   they disagree, the server wins — but the disagreement is
   blended over 100ms so the player perceives only a
   slight correction, not a jarring snap.

2. **The wire format is a delta, not a state dump.** A
   Snapshot is the same shape for every entity kind because
   it's a row in a table. The deserializer is one path. The
   replication tier decides *how often* to send a row, not
   *what shape* a row has. This is what keeps the bandwidth
   sane when 30 players pile on a HNM.

3. **The social link extends the world.** Interest radius
   isn't just "what I can see in front of me" — it's also
   "what my party and alliance can see, because we're
   coordinating". Voice respects the same hierarchy: party
   ducks proximity because the friend you're chatting with
   matters more than the goblin nearby. The MMO is the
   relationships, not the geometry.

The previous batch put the player in the world. This one
puts the *players* in the world.
