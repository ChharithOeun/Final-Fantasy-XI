# Player Presentation + Combat Camera

Vision
------

Last batch shipped audio + music spotting. The world looks
right, sounds right, breathes right. But the demo is still
a flythrough — the camera hovers, the player has no body,
no HUD, no targeting reticle. The world is alive; the
player is not. This batch makes the player a participant.
Five modules turn the demo from a guided tour into a
playable experience.

The five modules
----------------

**player_camera_rig** — The follow-camera state machine.
Ten modes covering every viewing situation a complete
demo needs: FIRST_PERSON, OVER_SHOULDER_TIGHT (RE4-style,
60mm), OVER_SHOULDER_WIDE (Witcher 3-style, 75mm),
THIRD_PERSON_FAR (classic FFXI 90mm at 8m back),
CINEMATIC_TRACK (handed off to director_ai during
cutscenes), FREE_LOOK (rotate camera independent of
body), CHOCOBO_RIDE (lifted higher for mount visibility),
SWIMMING_UNDERWATER (compressed FOV + fog), LEDGE_HANG
(pulled wide to read the cliff), KO_ORBIT (slow circle
around the downed body). Allowed transitions form a
directed graph — engaging combat auto-zooms
THIRD_PERSON_FAR -> OVER_SHOULDER_TIGHT over 0.4s;
mounting a chocobo swaps to CHOCOBO_RIDE; entering water
swaps to SWIMMING_UNDERWATER. Any mode can hand off to
CINEMATIC_TRACK and director_ai owns the camera until
reclaim_from_director is called. Collision avoidance
springs the boom forward when geometry would clip.

**player_body_rig** — Avatar visibility, weapon-draw
state, per-race adjustments. Six VisibilityKind values
covering FIRST_PERSON_HANDS_ONLY, FIRST_PERSON_ARMS_TORSO,
THIRD_PERSON_FULL, THIRD_PERSON_HEADLESS (helmet hides
when first-person clips), MAP_VIEW_TOP_DOWN,
CUTSCENE_PUPPETED (showcase_choreography drives bones).
Weapon draw goes SHEATHED -> DRAWING (0.35s) -> DRAWN ->
SHEATHING (0.5s) -> SHEATHED, with DUAL_DRAWN for NIN/DNC
dual wield (auto-promotes when both hands are weapons,
not when off-hand is a shield), and CASTING for
spellbook/staff pose. Per-race adjustments scale the rig
— Galka shoulders 1.3x, Mithra always shows tail, Tarutaru
hand-position lower because weapon scale is different.
draw_weapon() returns an animation_id the
character_animation module knows how to play.

**hud_overlay** — Live-action HUD (subtle, transparent,
contextual). 20 HudElement values covering all the FFXI
classics — health/MP/TP gauges, target frame, sub-target
frame, party frame (up to 6 members), casting bar, recast
timers grid, status icons row, action bar (10 slots), chat
window, minimap, wayfinder compass, conquest tally
ticker, region name banner, plus three delegating elements
(DAMAGE_NUMBERS_FLOATING, SKILLCHAIN_SUGGEST_OVERLAY,
DPS_METER_OVERLAY) that defer to their dedicated modules.
Six HudMode values (COMBAT, EXPLORATION, DIALOGUE,
CINEMATIC, MAP_OPEN, MENU_OPEN) flip per-element opacity
targets. Ghosting rule — health/MP/TP drop to 0.4 in
EXPLORATION because visible_health says "read posture, the
HUD is backup". CINEMATIC zeroes everything. DIALOGUE
hides everything except the casting bar (you still need to
see your cast through a conversation). User preference
hud_density (MINIMAL=0.4 / STANDARD=0.7 / DENSE=1.0)
multiplies on top.

**targeting_system** — Tab-target, lock-on, AOE placement,
sub-target chain. Eight TargetingMode values covering
NONE, TAB_TARGET_NEAREST, TAB_TARGET_LOCK,
AOE_GROUND_PLACE, AOE_CONE_FACING, FRIENDLY_TAB,
SUB_TARGET_CHAIN, SPECIFIC_NPC_ID. Tab cycles candidates
within radius_m sorted by camera-screen-distance — the
mob closest to screen-center is "next" because that's
what the player's looking at. Lock holds until release,
death, or unload. AOE_GROUND_PLACE clamps to a valid
surface (cliff faces are rejected) within max_range_m.
AOE_CONE_FACING uses player_facing + arc_deg. Sub-target
chain handles abilities like DRG Penta Thrust + Jump on
a flanker — set_sub_target during the main hit, the next
ability checks sub before main.

**combat_camera_director** — When combat starts, the
camera becomes a director. Eleven CombatCameraEvent
values; each maps to a CombatShot (shot_kind,
duration_s, lens_mm_hint, focus_target_priority,
hand_back_after, interrupt_priority 0..10). State machine
NORMAL -> COMBAT_AUTO -> CINEMATIC_SETPIECE ->
BACK_TO_NORMAL. Higher priority interrupts (BOSS_INTRO=10
beats CRITICAL_HIT=3); equal-or-lower priority queues for
after the current setpiece. Murch six-axis cut decisions
(emotion, story, rhythm, eye-trace, 2D plane, 3D space)
score every event 0..3 per axis; sum >= 12 triggers a
cut, sum < 12 holds. dramatic_hold scene flag raises
threshold by 1 to demand stronger justification.

Integration
-----------

* **director_ai** — handoff_to_director hands the rig to
  the cinematic system; reclaim_from_director takes it
  back. CINEMATIC_TRACK mode means "director owns the
  rig". The combat_camera_director's CombatShot.shot_kind
  field uses director_ai's shot vocabulary directly.

* **scene_pacing** — should_cut_for delegates to
  scene_pacing's Murch axis logic (six-axis cut decisions
  govern whether to cut to a new combat shot or hold).
  Combat shots are cuts; dramatic holds (long pulls
  through skillchain finishers) are intentional non-cuts.

* **showcase_choreography** — During a beat,
  player_camera_rig is in CINEMATIC_TRACK and the body
  rig's visibility_kind is CUTSCENE_PUPPETED — the
  choreographer drives bones, the rig just reports the
  body is visible.

* **cinematic_camera** — Same handoff path as director_ai
  but for non-combat cinematics (zone-intro shots,
  dialogue close-ups). When cinematic_camera takes over,
  hud_overlay.set_mode(CINEMATIC) zeroes the entire HUD.

* **screen_effects** — KO_ORBIT camera mode sits in front
  of KO_FADEOUT screen effect. The two compose: the
  camera does a slow circle while the screen vignettes
  toward black. Combat hits trigger HIT_SHAKE_* effects
  while the camera runs OVER_SHOULDER_TIGHT.

* **visible_health** — HUD ghosting rule pulls directly
  from the visible_health philosophy: posture, breath,
  blood decals, and limp-on-low-HP read the world; the
  bar is backup. EXPLORATION ghosts gauges to 0.4 to
  enforce the read-the-world rule.

* **engage_disengage** — engage state change triggers
  player_camera_rig.engage_zoom() (THIRD_PERSON_FAR ->
  OVER_SHOULDER_TIGHT over 0.4s) and
  player_body_rig.draw_weapon(main). Disengage triggers
  disengage_pullout() and sheathe_weapon(main).

* **equipment_set_manager + equipment_appearance** —
  player_body_rig.equip_main_hand records the weapon_id;
  draw_weapon emits an animation_id the
  character_animation module plays. equipment_appearance
  decides what mesh actually shows; player_body_rig owns
  the visibility flags.

* **character_model_library + character_animation** —
  per-race shoulder_scale and hand_height_offset feed
  into character_model_library's bone scaling.
  draw_weapon's returned animation_id is consumed by
  character_animation.

* **floating_damage_numbers / name_plate_system /
  spell_timer_display / dps_meter** — hud_overlay's
  three delegating elements (DAMAGE_NUMBERS_FLOATING,
  SKILLCHAIN_SUGGEST_OVERLAY, DPS_METER_OVERLAY)
  participate in the opacity-mode rules — they hide in
  CINEMATIC, ghost in EXPLORATION — but the actual
  rendering lives in those modules. Same for
  RECAST_TIMERS_GRID delegating to spell_timer_display.

* **minimap_engine + minimap_layout + widescan_system** —
  hud_overlay's MINIMAP element controls opacity; the
  actual minimap content comes from minimap_engine, the
  layout from minimap_layout. WAYFINDER_COMPASS opacity
  is independent.

* **macro_system** — ACTION_BAR element (10 slots) is
  the macro palette / radial. hud_overlay decides whether
  it's drawn; macro_system decides what's in each slot.

* **weapon_skills + spell_catalog** — sub-target chain in
  targeting_system enables ability sequences like Penta
  Thrust + Jump or Magic Burst chains. weapon_skills
  consults targeting_system.target_of_target to read the
  enmity table.

* **aoe_telegraph** — AOE_GROUND_PLACE in
  targeting_system places the reticle; aoe_telegraph
  draws the actual telegraph circle. The two share the
  ground_pos contract.

Open-source toolchain
---------------------

* UE5's built-in Camera Manager + Spring Arm component
  cover the full player_camera_rig functionality —
  collision avoidance, lerp_speed, FOV transitions, modal
  switching all map to existing UE5 features. We do not
  reinvent the rig; we wrap it with the deterministic
  state machine the demo grammar requires.

* UE5 Slate / UMG covers the HUD (HudElement -> Slate
  Widget tree). Per-element opacity_current is fed to a
  WidgetTreeOpacity binding. Mode transitions tween the
  bound float. Alternative path: ImGui for debug HUD,
  Slate for ship HUD.

* UE5 Niagara owns floating damage numbers and any
  particle-driven HUD elements (skillchain glyphs).

* targeting_system is engine-agnostic Python — the
  underlying spatial query is a per-frame loop over
  candidates filtered by distance and screen-distance.
  An UE5 implementation would back the candidates list
  with the engine's overlap query and the
  screen_distance_px from the player camera projection.

* combat_camera_director is engine-agnostic — it emits
  shot kinds the director_ai vocabulary already knows,
  so the rendered shot is whatever director_ai chooses
  to map onto.

HUD philosophy
--------------

Read the world physically. The HUD is backup. The whole
visible_health module exists because we want the player
to look at the avatar's posture for HP, the avatar's
breath for fatigue, the avatar's stance for stagger. The
gauges in EXPLORATION are at 0.4 opacity for that reason
— they're there if you need them, but they're not the
primary read. In COMBAT the gauges go full because the
numbers matter. In CINEMATIC and DIALOGUE the gauges go
black because the camera owns the frame; if you need
information, the dialogue/cutscene is supposed to deliver
it.

The HUD is also a confession: every UI element on screen
is a piece of information we couldn't deliver another way.
The chat window is text we couldn't deliver as voice;
the recast timer is a clock we couldn't deliver as a
character animation; the target frame is an enemy state
we couldn't deliver as a posture cue. Most modern AAA
games hide their HUDs in CINEMATIC + DIALOGUE because the
absence of the HUD is the proof that the moment is in the
fiction. We do the same.

Cross-module flow — bandit raid with player presentation
--------------------------------------------------------

1. Player enters Bastok Markets. player_camera_rig is in
   THIRD_PERSON_FAR (90mm at 8m). hud_overlay is in
   EXPLORATION; health/MP/TP at 0.28 opacity (0.7 density
   * 0.4 ghost), region_name_banner at 0.7. player_body_rig
   visibility = THIRD_PERSON_FULL.

2. A goblin raider aggros the player at 12m.
   targeting_system.tab_target finds it (single eligible
   candidate). engage_disengage flips to engaged ->
   player_camera_rig.engage_zoom() runs THIRD_PERSON_FAR
   -> OVER_SHOULDER_TIGHT over 0.4s. player_body_rig.
   draw_weapon("main") returns "anim_draw_main_hume".
   hud_overlay.set_mode(COMBAT) raises gauges to 0.7
   opacity, target_frame appears at 0.7.

3. combat_camera_director.trigger(ENGAGE_START, ctx)
   returns a 1.5s push_in_two_shot at 50mm. State goes
   NORMAL -> CINEMATIC_SETPIECE. Player's rig hands off
   to director (handoff_to_director with shot_kind=
   "push_in_two_shot"). Director runs the shot, ticks
   to completion, ends_setpiece, reclaim_from_director,
   rig back to OVER_SHOULDER_TIGHT.

4. Player chains a skillchain. trigger(SKILLCHAIN_OPEN)
   returns a 1.2s low_angle_close at 85mm — priority 5,
   beats nothing currently running, becomes the new
   setpiece.

5. Magic Burst connects. trigger(MAGIC_BURST_FIRED)
   returns priority-6 impact_hold — interrupts the
   skillchain shot mid-stream because 6 > 5. The
   skillchain shot is *not* queued (lower priority);
   only the burst plays.

6. Critical hit lands. trigger(CRITICAL_HIT) returns
   priority-3 quick_zoom — but should_cut_for(
   CRITICAL_HIT, time_since_last=0.1) returns False
   (too soon) AND (Murch score 9 < 12). Held; the
   burst-shot continues uninterrupted.

7. Iron Eater intro fires. trigger(BOSS_INTRO) returns
   priority-10 establishing_pullback at 24mm — interrupts
   everything. 4-second pullback. Held against any other
   event.

8. Player goes down. trigger(PLAYER_DOWN) returns
   priority-9 ko_orbit_slow with hand_back_after=False —
   so when the shot ends, rig stays in CINEMATIC_TRACK,
   waiting for raise. screen_effects fires KO_FADEOUT
   in parallel; the two compose.

9. Raise begins. trigger(RAISE_BEGIN) returns priority-2
   rise_up_pan; the player's HUD comes back from the
   CINEMATIC zero, gauges retarget to 0.7 (combat is
   still active because re-engage hasn't disengaged).

Three design hinges
-------------------

1. THE RIG IS THE STATE MACHINE, THE BODY IS THE PUPPET.
   player_camera_rig owns the where-is-the-camera
   decision; player_body_rig owns the what-is-the-body-
   doing decision; the two are decoupled. A first-person
   camera with a third-person body, or a third-person
   camera with a CUTSCENE_PUPPETED body, are both valid
   states because the modules don't know about each
   other. Coupling them would break the cinematic
   handoff.

2. THE HUD GHOSTS, NEVER POPS. Every opacity transition
   is eased through tick(dt) at the element's
   fade_speed_s. Mode changes don't jump the alpha; they
   set the target and let the tick smooth it. The same
   philosophy as music_spotting fades — you should never
   notice the system change state, only the resulting
   feel.

3. THE COMBAT DIRECTOR INTERRUPTS BY PRIORITY, NOT BY
   ORDER. A boss intro fires mid-skillchain — boss intro
   wins because it scored 18 on the Murch axes and the
   skillchain scored 12. The system reads the *meaning*
   of the event, not its arrival time. The director is
   trained to favor the most cinematic moment available
   in the current beat.

The previous batch made the world breathe. This one puts
the player in the world.
