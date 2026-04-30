# Cinematics

> "Live-action theatrics" — the cutscenes look like film. Not anime cutscene, not game cutscene — film.

This sets the bar above where most game remasters land. Most games copy 90s cinematic language and translate it to modern fidelity. We do the opposite: borrow film grammar (lens choices, blocking, lighting, edit cadence) and put FFXI characters and zones inside it. Players should feel like they're watching the movie someone would have made of their save file.

## What "live-action theatrics" means concretely

- **Real lenses.** Wide for establishing, 35mm for blocking, 50/85mm for hero shots, 200mm for compression. UE5 Cine Camera in every shot.
- **Anamorphic when it serves the story.** 2.39:1 letterbox during dramatic beats; back to 16:9 for in-game and casual cutscenes.
- **Real lighting.** Lumen + path tracing. Three-point lighting for character moments; volumetric god rays through Maat's morning windows; fire-lit faces in the Bastok smithy. No flat ambient; no "everything is fully visible."
- **Real grain and bloom.** Subtle film grain LUT. Bloom kept under control — modern, not 2007 anime. ACES color pipeline.
- **Real depth of field.** Aperture-driven, not "blur the background fixed amount." Hero in focus, geometry behind racks out of focus realistically.
- **Real performance.** Faces emote. Hands gesture. Eyes look where they're supposed to. MetaHuman Animator drives this end-to-end.
- **Real audio.** Diegetic sound design, not the original game's MIDI stings. Voice acting via the voice pipeline. Score lifts at hits, sits under dialogue.

## The pipeline

```
Storyboard / shot list
    │
    ▼
┌─────────────────────────────┐
│ UE5 Sequencer               │
│  - master timeline           │
│  - per-shot Cine Cameras     │
│  - takes & versions          │
└─────────────────────────────┘
    │
    ├────► Hero characters
    │       MetaHuman Creator → MetaHuman Animator
    │       (face capture or speech-driven facial mocap)
    │
    ├────► Character motion
    │       motion-diffusion-model + ai4animationpy + IK
    │       (text prompt → keyframes; mocap files when better)
    │
    ├────► Voice
    │       Higgs Audio v2 cloned voice
    │       (subtitles auto-baked into render via UnrealGenAISupport)
    │
    ├────► World
    │       UE5 zone import from Pathfinder/FFXI-NavMesh-Builder
    │       Lumen GI, Nanite geometry, volumetric clouds, atmospheric
    │
    ├────► Practical effects
    │       Niagara particle systems hand-tuned per spell/effect
    │       (FFXI signature spells re-authored at film fidelity)
    │
    └────► Music
            ACE-Step regenerated soundtrack
            (per-cutscene cue selection from the regenerated score)
    │
    ▼
┌─────────────────────────────┐
│ Movie Render Queue          │
│  - path-traced render        │
│  - per-shot quality preset   │
│  - 4K H.265 export           │
└─────────────────────────────┘
    │
    ▼
Cutscene asset → shipped with client
```

Real-time cutscenes (interruptable, in-engine, sub-1ms per frame) use the same pipeline minus path tracing — they run at engine quality. The big "story moment" cutscenes are pre-rendered at film quality and play as video.

## Toolset (additions to what's already cloned)

| Tool | Where it slots | Status |
|------|----------------|--------|
| **UE5 Sequencer** | Built into UE5 (already installing) | ✅ Native |
| **UE5 Movie Render Queue** | Built into UE5 plugin | ✅ Native, enable per project |
| **MetaHuman Creator + MetaHuman Animator** | UE5 (we requested this in install options) | ✅ Installed alongside engine |
| **UE5 Cine Camera + Camera Rig Rail** | Built into UE5 | ✅ Native |
| **NVIDIA Audio2Face** (optional) | Speech → facial animation | ⚠️ NVIDIA-only; we use MetaHuman Animator's speech-to-face instead, which works on AMD |
| **Faceware Studio** | Real-time facial mocap from webcam | 💸 Commercial; only if we shoot real reference |
| **FreeMoCap** | Open-source markerless mocap from video | ✅ Works on any GPU; consider for body mocap |
| **Quixel Megascans** (queued in Epic launcher) | Set dressing — rocks, vegetation, ground textures | ✅ Free for UE projects |
| **DaVinci Resolve** (already installed on user's box) | Final color grading + audio mix on rendered output | ✅ Free version sufficient |

## Shot grammar (the rules our cutscenes obey)

These are not invented. They're the standard film grammar that's invisible because every movie uses them:

- **180-degree rule** is sacred. Never cross it.
- **Opening wide, closing close.** Establishing shot first, then push in over the cutscene's beats.
- **Eye lines match.** Two characters in dialogue look at each other across cuts. UE5 has a Look-At constraint; use it always.
- **Cuts on motion.** When in doubt, cut on a character's gesture or the camera's movement, not on a still frame.
- **No more than 3-second held wides** unless the wide is the point (a vista, an army, a god revealing itself).
- **Cutscene length cap**: 90 seconds for routine story beats; 3-5 minutes for major plot moments. Anything longer is a *scene*, not a *cutscene* — break it.

The user is the final arbiter on storyboards. The agent stack proposes shot lists; the human picks.

## Hero moments — what we treat as film-quality

Some FFXI moments deserve the full path-traced, 90-day-render-queue treatment. Initial list:

1. **The opening cinematic** of any character creation — your character wakes up in their starting nation, a Vana'diel morning. This is the player's first impression. Spend.
2. **CoP's pivotal moments** — the Tavnazian survivors, the first encounter with Promyvion, the Garlaige confrontation. These are the most emotionally-loaded sequences in the game.
3. **ToAU's political beats** — Aphmau's coronation, Salaheem's bazaar, Aht Urhgan's falafel-stained intrigue. ToAU lived on dialogue; do it justice.
4. **Boss intros for the top-tier NMs and avatars** — Bahamut's awakening, Absolute Virtue's reveal, Pandemonium Warden's first phase. Each is a 30-60 second pre-rendered intro that plays once per fight.
5. **Player-fomor reveals** — when one of *your party's former members* spawns as a fomor for the first time. This needs to land. Maybe 15 seconds, low-key, devastating.

Routine NPC dialogue is real-time in-engine. Hero moments get the offline render. The line between "real-time" and "pre-rendered" is a judgment call per scene and one of the bigger creative decisions we'll make.

## Camera AI

We hand-direct hero shots. Routine cutscenes get camera direction from an LLM agent that:

- Reads the scene script (who says what, who's where, what happens)
- Knows the shot grammar above
- Proposes a Sequencer shot list (camera positions, lens choices, durations)
- Renders a low-res preview
- We review, accept or revise, lock the shot list, render at quality

This makes mass-produced reactive cutscenes (the LLM-generated quest dialogue from REACTIVE_WORLD.md) feel directed even though they're synthesized. The same agent doesn't direct the hero moments — those are too important.

The camera AI lives in `src/cinematics/camera_director.py` once we build it. It's a thin LLM wrapper that emits Sequencer JSON.

## Risks

- **Quality drift across hundreds of cutscenes.** Mitigation: define a strict template (LUT, lens preset, camera rules) the camera AI must obey. Hero shots break the template intentionally.
- **Render time.** Path-traced 4K cutscenes render at single-digit frames per minute on a workstation GPU. A 60-second scene might be a 12-hour render. We schedule these on the box at night.
- **Voice + facial animation desync.** Higgs Audio gives us the voice; MetaHuman Animator drives the lips. If the synth audio runs through pitch-shifts (for monster voices), facial sync breaks. Mitigation: lip-sync drives off the *unprocessed* audio, then we apply effects to the audio stream after. Same lip motion, monster voice.
- **Uncanny valley.** Hand-directed hero MetaHumans look great. Auto-generated 1500-NPC ambient scene MetaHumans look weird. Mitigation: don't use MetaHuman for ambient NPCs — use the original FFXI character meshes upscaled; reserve MetaHuman for hero characters who hold the camera.

## Order of build

1. **One hero shot, end-to-end.** Pick a single moment (Bastok smithy, Cid talking to a young Lion). Build it as a vertical slice: world, MetaHuman, voice, music, lens, lighting, render. See how it looks. Iterate the template based on it.
2. **Routine cutscene template.** Lock the camera AI shot grammar, the LUT, the lens kit. Ship a 30-second routine cutscene at 5x lower budget than the hero.
3. **Reactive cutscenes.** Wire the LLM-driven scene generator (REACTIVE_WORLD.md) to the camera AI. The cooks' guild master complaining about cornette prices generates a 10-second cinematic, real-time-in-engine.
4. **Hero moment slate.** Build the 5-shot list above for the marquee story beats.
5. **Production pipeline.** Once steps 1-4 prove out, we pre-render the marquee cutscenes overnight on a rolling schedule.

The slowest step is rendering. Everything else is a few weeks. Plan accordingly.
