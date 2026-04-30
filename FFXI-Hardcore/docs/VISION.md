# Vision

## One-liner

Take the 2002 FFXI world we already host on LSB and rebuild the **client side** — geometry, characters, animation, lighting — at modern HD/4K fidelity, using AI tooling everywhere a 2026-era pipeline would.

The server stays. The data stays. The MMO logic stays. What changes is the layer the player sees.

## What we are NOT building

- **Not** a new game. Story, zones, jobs, mobs, items — all upstream from LSB.
- **Not** a private fork of an existing remaster. We're building tools first, art second.
- **Not** a closed-source product. The toolchain is meant to be reusable for any FFXI HD effort.

## Why now

Three things converged:

1. **Asset extraction is solved.** `xathei/Pathfinder` and `LandSandBoat/FFXI-NavMesh-Builder` already pull complete zone geometry out of the running server's collision data as OBJ + navmesh. *Silmaril 2 — Building NavMeshes and how it works* shows the path end-to-end.
2. **Engine automation is solved.** `flopperam/unreal-engine-mcp` exposes Unreal Engine 5 to an LLM via MCP — zone assembly, asset import, blueprint wiring all become tool calls. We can drive UE5 from chharbot the same way we drive shells.
3. **AI character motion is solved.** `facebookresearch/ai4animationpy` produces high-quality locomotion / combat / idle motion from skeleton + intent. No more 24-frame loops; characters move like 2026 characters.

Combine those three and the bottleneck stops being *"can a tiny team rebuild thousands of FFXI assets"* and starts being *"in what order do we run the pipelines."* That's the gap this project closes.

## Tone & feel

- **HD, not reimagined.** Keep silhouettes, palette, mood. Don't redesign Vana'diel — re-shoot it.
- **Hardcore.** The original was patient, lonely, and rewarding. The remake honors that. No QoL homogenization.
- **Faithful to LSB.** If the server says you can do it, the client must let you do it. If LSB doesn't simulate it, the client doesn't pretend it exists.

## Success looks like

A player launches an FFXI HD client, logs into our existing LSB server, walks out of Bastok in 4K with AI-driven idle motion, fights a mob using server-authoritative damage with modernized particle work, and is unable to tell that the server underneath is the same 2002-era pipeline we've been running all year.

## Order of operations (rough)

1. **Pull geometry** — get every accessible zone out of LSB collision data as OBJ. (Pathfinder / FFXI-NavMesh-Builder)
2. **Stage in UE5** — bring zones into Unreal Engine 5 with correct collision + navmesh, driven by `unreal-engine-mcp` so iteration is scripted.
3. **AI animation pass** — wire `ai4animationpy` to the player skeleton + a few mob skeletons. Replace the most visible idle/walk/run loops first.
4. **Texture / lighting pass** — upscale or regenerate textures, set up modern PBR + global illumination per zone.
5. **Network bridge** — connect the UE5 client to LSB via the existing client protocol (the hardest unknown — may need a translation shim).
6. **Vertical slice** — Bastok Markets, fully playable, server-authoritative.

Each step has its own doc in `docs/` once it's actively being worked.

## Anti-goals

- **No competing with retail.** Retail FFXI exists. This is for the LSB / private-server scene.
- **No ship date.** This is a research project. It ships when slices are good enough to share, not on a calendar.
- **No solo-LLM-vibe-coded shortcuts.** Real engineering work, audited end-to-end. The LLM drives, but everything is reproducible from the manifest.
