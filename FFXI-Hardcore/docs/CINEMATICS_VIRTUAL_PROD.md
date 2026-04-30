# Virtual Production — borrowing from The Mandalorian

> "We don't have an LED volume. We have UE5 and a brain."

The Mandalorian's StageCraft setup — actors performing in front of curved LED walls displaying real-time UE5 environments — is the cleanest example of UE-driven virtual production in the wild. We can't replicate the hardware (a 270° LED wall is several hundred thousand dollars and a sound stage). But we can replicate the **grammar** — the lensing, the parallax, the integrated lighting, the in-camera composite — using what UE5 ships in the box.

This doc is the addendum to `CINEMATICS.md` covering specifically what we steal from StageCraft and how it fits our pipeline.

## What StageCraft actually does

The Mandalorian's volume runs UE5 displaying a real-time 3D environment. A camera with tracking markers moves through the physical set; UE5's nDisplay system updates the LED wall's frustum (the projected perspective) so that what the camera sees has correct parallax for that camera's exact position. The actors are *physically* on a small set with practical props; the wall behind them sells the illusion that they're on Tatooine. Lighting from the LED wall actually lights the actors — the orange of the Mandalorian's helmet picking up Tatooine's binary suns is real environmental lighting from the wall, not post.

Three primitives matter:

1. **Real-time UE5 environment** — the world the camera is "in"
2. **Camera tracking** — the system knows where the camera is in physical space, frame-by-frame
3. **Frustum-correct rendering** — UE renders the wall image specifically for that camera's perspective; from anywhere else the image looks distorted, but through the lens it's perfect

## What we adapt for FFXI Demoncore

We're making *cutscenes*, not live-action film. We don't need a wall at all. But we DO need the same primitives. Here's the mapping:

| StageCraft thing | Our equivalent |
|------------------|----------------|
| LED wall displaying UE5 | Just UE5 — we render the cutscene entirely in-engine |
| Physical actor on a set | A MetaHuman / FFXI character driven by mocap or animation curves |
| Camera tracking (Vive/StarTracker) | UE5 Cine Camera with hand-keyed paths, OR a webcam-tracked virtual camera (UE5 supports this natively via the Live Link plugin + iPhone/Android Virtual Camera app) |
| Frustum-correct rendering | UE5 Sequencer + Movie Render Queue do this natively |

What's left over — the lensing grammar, the lighting integration, the in-camera composite feel — we adopt directly.

## The plugins we turn on

UE5.7 ships with the relevant plugins; we just enable them per project:

- **In-Camera VFX** — the ICVFX template. Even without a physical wall, this template ships with a virtual frustum + content layer separation that's useful for our hero cutscenes.
- **Virtual Camera** — turns an iPhone or Android phone into a tracked handheld camera. Plug Live Link into it; the phone's gyro + position drive a Cine Camera in UE. We can do real handheld camera moves with no rig.
- **Live Link** — the data backbone. Cameras, actors, faces all stream live position/rotation/morph data into UE through this.
- **nDisplay** — for multi-screen projector setups. We probably never need this, but documenting it for completeness.
- **Sequencer + Movie Render Queue** — the pre-rendered hero shots. Already covered in `CINEMATICS.md`.

## The grammar we import

Things StageCraft taught the industry that we copy regardless of hardware:

### Real-time previz IS the shot

The director on Mandalorian doesn't shoot a take, send dailies to VFX, get a comp back days later, and review. They look at the wall. The shot exists in real time. We adopt the same: every cutscene shot is dressed and reviewed in the UE5 viewport at near-final quality. Movie Render Queue gives us the *export* fidelity, but the *creative call* happens live.

### Lighting is the world

In Mandalorian's volume, the wall lights the actors — the same orange dawn that's in the background is on the actor's face. There's no separate "light the actor" step. We do this naturally because everything is in UE5: Lumen propagates the scene's GI to every character automatically. No flat overhead studio light pretending to be the sun.

### Parallax sells reality more than texture detail

A wall full of 4K texture but no parallax reads as a poster. A wall with mid-fidelity textures but accurate parallax reads as a place. UE5 gives us parallax for free (we're rendering 3D, not displaying flat images). We just need to remember to USE depth — don't compose the cutscene as if everything is at the same Z.

### Lens choices over color grades

Mandalorian's signature look isn't a LUT (well, it has a LUT, but that's not why it looks like Mandalorian). It's lens choices: anamorphic widescreen, distinct optical compression on hero shots, deliberate use of long focal lengths for emotional moments. We bake these lens decisions into our shot grammar — see `CINEMATICS.md` for the lens kit. The color grade is the topcoat, the lensing is the structure.

### Practical effects on a virtual set

Mandalorian shot real fire, real smoke, real water on the volume floor — the wall provided the wide environment, the floor + foreground provided the immediate physical world. We adopt the same: each scene has a hero **near layer** (high-detail, hand-tuned, animated, expensive) and a **far layer** (the world's UE5 zone, dressed but not bespoke). When the camera pushes in for an emotional beat, we're focusing on the near layer; the far layer is just present, parallactic, lit-correctly, and lower-cost.

## The webcam virtual camera trick

This is the affordable-magic. UE5 + Live Link + the **Unreal Virtual Camera** app (free, iOS/Android) means:

- The phone in your hand becomes a tracked Cine Camera in UE5.
- Gyro + IMU give you 6DOF camera position.
- You watch the UE viewport on your phone screen as you move.
- The motion you record is REAL handheld camera motion.

For Demoncore's hero shots, this means we can do *handheld in Vana'diel*. Pick up the phone, walk through Bastok Markets while the rendered camera in UE follows your motion. The resulting camera move feels human because it WAS a human moving — not a hand-keyed Bezier curve trying to fake it.

Mandalorian uses high-end equivalents (StarTracker, Mo-Sys). The phone version is 90% of the result for 0% of the cost. We use this for any cutscene with documentary-feel handheld energy.

## When we use static / robotic camera moves

Counterpoint: not every shot benefits from handheld. Spec sheet for when the camera should be:

| Move | Use for |
|------|---------|
| **Locked off (tripod)** | Reverent shots — the establishing on a god-tier NM, the first reveal of a city, mission-critical moments |
| **Slow push-in (dolly)** | Emotional beats — close-up on a character realizing something |
| **Slow pull-out (dolly out)** | Reveal of consequence — "and now the whole city is on fire" |
| **Handheld (phone-cam)** | Documentary feel — chases, panic, intimacy |
| **Boom / crane** | Sweeping reveals — flying into a zone, descending to a battle |
| **Camera Rig Rail (predefined)** | Routine cutscenes generated by the camera AI; consistent quality across many auto-shots |

The camera AI from `CINEMATICS.md` defaults to Camera Rig Rail moves for routine shots. Hero shots are hand-directed using one of the above. Handheld is the most powerful and most overused — discipline.

## The boundary: when to render real-time vs offline

| Scene type | Render path |
|------------|-------------|
| **In-game cutscenes** (the cooks' guild master comments on cornette prices) | Real-time in UE5 at engine quality. Sub-frame-time. |
| **Routine missions / intra-zone story beats** | Real-time at high engine quality (Lumen on, Nanite on). |
| **Hero moments** (opening cinematic, marquee NM intros, the player-fomor reveal) | Pre-rendered offline via Movie Render Queue. Path tracing on. Hours of render per shot. |

The line is creative: how much does this shot *matter*? If the answer is "this is the moment players will remember," it's offline-rendered. Otherwise it's real-time.

## What's missing if we wanted full Mandalorian-grade

We don't need it, but for completeness:

- An LED volume (won't happen)
- Mo-Sys / StarTracker high-precision camera tracking (we use phone or hand-keyed)
- A practical set with foreground props (we render everything, even hero foreground props)
- Real actors (we use MetaHuman + voice cloning)
- A second-unit team to shoot inserts (the camera AI handles this for routine shots)

We're trading hardware capital for engine-time capital. UE5 gives us enough that the trade pencils out for our scale.

## Build order (where this slots into the bigger plan)

The base `CINEMATICS.md` build order has 5 steps. Virtual production fits into them:

- **Step 1 (one hero shot, end-to-end)** — use phone-cam for the camera move; this is the cheap-magic test
- **Step 2 (routine cutscene template)** — use Camera Rig Rail; this is the volume-production approach
- **Step 3 (reactive cutscenes)** — camera AI uses Rig Rail; routine quality, lots of throughput
- **Step 4 (hero moment slate)** — phone-cam OR hand-keyed Sequencer paths; per-shot creative call
- **Step 5 (production pipeline)** — Movie Render Queue overnight rendering for hero shots; real-time engine for everything else

By step 4 we've internalized the Mandalorian grammar. The grammar matters more than the hardware.
