# Music Pipeline — HD Recreation via ACE-Step

The original FFXI soundtrack is iconic but mastered for 2002-era hardware (44.1 kHz, heavily compressed, MIDI-rooted). Modern listeners expect 96/192 kHz lossless masters with full dynamic range and modernized instrumentation. This pipeline rebuilds the entire soundtrack at modern fidelity using [ACE-Step v1.5](https://github.com/ace-step/ACE-Step-1.5) — driven by chharbot so the agent can iterate on tracks autonomously.

## Why ACE-Step

- **Open source.** No commercial licensing fees, no rate limits, runs locally.
- **State of the art.** v1.5 outperforms most commercial models (Suno, Udio).
- **<2 seconds per song on A100, ~10s on RTX 3090.** Iteration is cheap, so we can batch the entire soundtrack.
- **Fine-grained control.** Voice cloning, lyric editing, remixing, accompaniment generation — all exposed as parameters.
- **LoRA-trainable.** We can train a LoRA from the original FFXI soundtrack itself to anchor style, then regenerate at higher fidelity without losing the Mizuta/Uematsu signature.

## Hardware footprint

ACE-Step needs **<4 GB VRAM** for inference. That's well within the user's box (NVIDIA workstation card visible in earlier sessions). Training a style LoRA needs more (probably 12+ GB) but is a one-time cost.

## Pipeline shape

```
Original FFXI track (loop / .it / .mod / WAV)
        │
        ▼
┌─────────────────────────────┐
│ 1. Source extraction        │
│  - dump zone music from     │
│    client                   │
│  - decode .it tracker files │
│  - normalize to WAV 44.1kHz │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 2. Style anchor             │
│  - feed original through    │
│    ACE-Step style encoder   │
│  - extract voice / timbre / │
│    instrumentation embeds   │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 3. ACE-Step inference       │
│  - prompt: "regenerate this │
│    in <style> at 96kHz with │
│    modern mastering"        │
│  - LoRA: FFXI-soundtrack    │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 4. Quality gate             │
│  - chharbot listens (or     │
│    feeds to a critic model) │
│  - regenerates if rejected  │
└─────────────────────────────┘
        │
        ▼
HD master (FLAC / WAV 96kHz)
        │
        ▼
   FFXI HD client audio bank
```

## chharbot wrapper plan

We expose ACE-Step as a chharbot MCP tool so the agent can drive the pipeline end-to-end:

```python
# in mcp_server/music_tools.py
@mcp.tool
def acestep_generate(
    prompt: str,
    style_audio_path: str | None = None,
    lora_path: str | None = None,
    output_path: str = "out.wav",
    duration_s: int = 180,
    sample_rate: int = 96000,
) -> dict:
    """Generate a music track via ACE-Step. Optionally anchor on a style audio
    file and/or apply a trained LoRA."""

@mcp.tool
def acestep_remix(input_path: str, prompt: str, output_path: str) -> dict:
    """Remix an existing track — keep melody/structure, change instrumentation
    or production style."""

@mcp.tool
def acestep_train_lora(
    style_audio_dir: str,
    lora_output_path: str,
    epochs: int = 10,
) -> dict:
    """Train a LoRA from a directory of style audio files. One-time cost; the
    resulting LoRA gets passed to acestep_generate to anchor style."""
```

The wrapper lives next to the existing `agent_tools.py` in `mcp-graphify-autotrigger/mcp_server/`. Once registered, `delegate_shell` and these tools combine: chharbot can scan for source files, generate, listen, regenerate.

## Order of operations

1. **Clone ACE-Step-1.5** into `repos/_music/`. (handled by `scripts\CLONE_REPOS.bat`)
2. **Set up a Python venv** with the ACE-Step requirements (`pip install -e .` inside the repo, plus its torch deps).
3. **Smoke test inference** on a single random prompt — verify the box can run it locally.
4. **Train an FFXI-soundtrack LoRA.** Feed in the original tracks (we'll need to dump them from the client first).
5. **Wrap as MCP tools** (the snippet above).
6. **Drive the regeneration** — chharbot iterates over the soundtrack, generating, evaluating, retrying.

## Risks / unknowns

- **Style anchoring quality.** Regenerated tracks might drift away from the originals' character. Mitigation: LoRA training on the original soundtrack should pin style; if it doesn't, we layer ControlNet-style conditioning.
- **Dynamic music.** FFXI's combat layer transitions are state-driven (the music changes when an enemy aggros). Generating a "full" track loses that. We may need to generate stems (melody / harmony / percussion / atmosphere) separately and re-assemble in the engine — that's a v2 problem.
- **Voice cloning ethics.** Some FFXI tracks have vocals (Vana'diel March etc.). We should NOT clone the original singers without permission. The LoRA can learn instrumental style only.
- **Licensing.** The originals are Square Enix's. This pipeline is for a private LSB server, not commercial distribution. We respect that boundary.

## Next concrete step

Once ACE-Step is cloned (handled by the next clone batch) and the Python venv is set up, run the inference smoke test. That's the gate for everything else in this doc.
