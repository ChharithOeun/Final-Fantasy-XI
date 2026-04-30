# GPU Compatibility

> Every tool in this stack must run on the user's GPU. Period. No "yeah but it'd be faster on an A100" — we ship what runs locally on what's in the box.

The user's machine has an **AMD GPU** (visible from Radeon ReLive / AMD Bug Report Tool / Adrenalin in installed apps). It also has NVIDIA tooling installed (NVIDIA App, NVIDIA Control Panel) but the productive GPU on this box is AMD. Most of the open-source ML stack is CUDA-first; this doc is the per-tool plan for getting around that.

## Backend options on AMD Windows

| Backend | What it is | Maturity on Windows | Notes |
|---------|------------|---------------------|-------|
| **DirectML** | Microsoft's DirectX-12 ML backend. Works with PyTorch via `torch-directml`, with ONNX Runtime, with most diffusion stacks. | Mature, the default for our stack. | Slower than ROCm on Linux but it works on AMD Windows. |
| **ROCm** | AMD's CUDA-equivalent. Works on Linux, Windows support is recent and partial. | Improving fast in 2025-2026 (HIP for Windows is finally stable on RDNA3+). | Where it works, it's the fastest. |
| **Vulkan compute** | Cross-vendor compute via Vulkan. | Niche but useful for things like llama.cpp, GGUF inference. | Best for LLM inference where it competes with ROCm. |
| **ZLUDA** | CUDA-on-AMD translation layer. | Was excellent, AMD pulled support 2024. Community fork active. | Last-resort for stubborn CUDA-only tools. |
| **CPU** | When all else fails. | Always works. | Use for small/one-off tasks; not for production loops. |

The default per tool is whichever backend has first-class support. Where multiple work, DirectML wins for compatibility, ROCm for performance.

## Per-tool status

### Voice stack

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **Higgs Audio v2** | DirectML | ✅ Works | Apache 2.0 license, runs as PyTorch. Use `torch-directml` instead of CUDA torch. Inference fits in 16-24 GB VRAM. |
| **F5-TTS** | DirectML | ✅ Works | Same path: `torch-directml`. Inference is fast (flow-matching, fewer steps). |
| **Bark** | DirectML | ✅ Works | Older PyTorch model, well-supported on DirectML. |

Setup pattern for all three:

```bash
pip install torch-directml
# in each tool's loader:
import torch_directml
device = torch_directml.device()
model = model.to(device)
```

Speed expectations on RDNA3 vs an RTX 4090: ~40-60% the throughput. Acceptable.

### Visual stack

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **Real-ESRGAN** | DirectML | ✅ Works | Pure-PyTorch upscaler; DirectML is a drop-in. Or use ONNX Runtime DirectML for even cleaner integration. |
| **ComfyUI** | DirectML | ✅ Works | First-class DirectML support via the [`comfyui-directml-for-amd`](https://github.com/patientx/ComfyUI-Zluda) community variant or stock ComfyUI with `--directml` flag. Stock supports AMD on Windows in 2026. |
| **Motion Diffusion Model** | DirectML | ⚠️ Possible workaround | Original repo is CUDA-only. PyTorch port to DirectML via the standard pattern. Some custom CUDA kernels in the rendering side may need Vulkan fallback — flag if hit. |

### Animation

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **ai4animationpy** | DirectML or CPU | ⚠️ Possible workaround | Facebook research code, CUDA-first. Inference on a trained model is pure PyTorch matmuls — DirectML works. Training on AMD is a separate question; we'll likely train smaller models elsewhere or use the pretrained checkpoints. |

### Music

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **ACE-Step v1.5** | DirectML | ✅ Works | Diffusion Transformer, standard PyTorch. The README explicitly mentions AMD support. ~4 GB VRAM. Fast on RDNA3. |

### AI orchestration

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **generative_agents** | LLM-API only | ✅ Works (no local GPU) | The Stanford repo calls an LLM (originally GPT-4). We swap that for our local Ollama which already runs on CPU+GPU with what fits. No direct GPU dependency in the agent code itself. |
| **Neural MMO 2.0** | DirectML for inference, CPU for training | ⚠️ Possible workaround | RL training is the heavy part. Inference of a trained policy is tiny — runs anywhere. We train policies offline (could use cloud GPU for that one job) and ship the inference graph. |
| **PettingZoo** | CPU | ✅ Works | Pure-Python multi-agent env. No GPU needed at the framework layer. |

### Unreal Engine

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **Unreal Engine 5.7** | DirectX 12 native | ✅ Works | UE5 is GPU-vendor agnostic. AMD GPUs render UE5 great. Lumen and Nanite both run. |
| **MetaHuman Creator** | DirectX 12 | ✅ Works | Same as UE5. |
| **KawaiiPhysics** | UE5 native | ✅ Works | Pure CPU/UE simulation, no ML. |
| **UnrealGenAISupport** | UE5 + LLM-API | ✅ Works | Calls external LLMs / TTS via API. The UE side is rendering — vendor-neutral. |

### Code knowledge graph

| Tool | Backend | Status | Notes |
|------|---------|--------|-------|
| **graphify** | CPU | ✅ Works | Tree-sitter AST extraction, no GPU. |
| **chharbot agent** | DirectML for the local LLM, CPU for the rest | ✅ Works | Ollama already running with GPU offload on the user's box. |

## When something doesn't work

If a tool's CUDA-only and we can't move it:

1. **Check the issue tracker**, see if anyone's done the DirectML port. Usually yes for popular projects.
2. **Try ZLUDA** if the codebase is small. Community fork at [vosen/ZLUDA](https://github.com/vosen/ZLUDA).
3. **Run the heavy part on CPU**, ship the inference graph to GPU. RL training is the most common case.
4. **Run that one tool on the rented cloud box** (we have remote ops capability via chharbot's `delegate_shell`). Train remote, deploy local.
5. **Find an alternative.** There's almost always one.

## Environment template

We pin a known-good Python env for the AI side:

```yaml
# environment/amd-windows.yml
name: ffxi-hardcore-ai
channels: [conda-forge, pytorch]
dependencies:
  - python=3.11
  - pip
  - pip:
    - torch==2.5.0
    - torch-directml==0.2.5
    - onnxruntime-directml
    - transformers
    - diffusers
    - accelerate
    # tool-specific
    - higgs-audio
    - f5-tts
    - bark
    - realesrgan
    - acestep-1.5
```

Each tool gets its own `pyenv` / `venv` to avoid cross-version torch conflicts (DirectML torch is pinned to specific versions). The `environment/` dir under FFXI-Hardcore holds these.

## Test gates

Before committing to a tool we run a smoke test on the user's GPU:

- **Voice**: synthesize one 5-second line in <10 seconds wall-clock.
- **Visual**: upscale one 512x512 texture to 4K in <30 seconds.
- **Music**: generate one 60-second track in <90 seconds.
- **Animation**: produce one walk cycle from a text prompt in <60 seconds.

If a tool fails its smoke test on the user's GPU, we either find the workaround above or replace the tool. We do not paper over performance — slow inference becomes a production blocker fast.

## Hardware ceiling notes

The user's box is the hot path. When we hit GPU saturation (multiple voice synths + RL inference + UE5 rendering simultaneously), the real bottleneck is **VRAM**, not compute. Mitigations in priority order:

1. **Quantize models.** 4-bit quantization typically loses <2% quality and saves 75% VRAM.
2. **Stagger workloads.** Voice synth happens on demand; pre-render what you can offline.
3. **Off-box one model.** Run the LLM critic for boss fights on cloud, everything else local.
4. **Add GPU memory.** 24 GB is the practical floor for this stack at full tilt; 32+ GB makes it trivial.

The external HD coming online doesn't help VRAM, but it does buy us model storage room — we can keep more candidate checkpoints around without rotating.

## Next concrete step

When UE5 finishes installing, the first verification is:

```bash
# in a fresh AMD-aware Python env
python -c "import torch_directml; t = torch_directml.device(); print(torch.tensor([1.0]).to(t))"
```

That single line confirms torch-directml is alive and the GPU is reachable. If it works, we move on to per-tool smoke tests. If it doesn't, the rest of this doc kicks in.
