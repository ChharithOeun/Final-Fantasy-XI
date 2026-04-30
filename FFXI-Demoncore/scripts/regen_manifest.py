"""Regenerate MANIFEST.md for FFXI-Hardcore from whatever's currently in repos/.

Walks repos/<category>/<project> dirs, reads .git/HEAD + packed-refs to extract
HEAD commit, and emits a Markdown table grouped by category.

Usage:
    python regen_manifest.py <path-to-FFXI-Hardcore>
"""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path


CATEGORIES = {
    "_navmesh":   "Zone geometry → 3D mesh",
    "_ue":        "Unreal Engine 5 — AI agent control + plugins",
    "_animation": "AI-driven character motion",
    "_visual":    "4K textures + generative art",
    "_music":     "HD music recreation",
    "_agents":    "Generative agents (LLM-driven autonomous NPCs)",
    "_combat_rl": "Multi-agent reinforcement learning for combat AI",
    "_auth":      "Discord OAuth + moderator (replacing PlayOnline)",
}

UPSTREAM_URLS = {
    # navmesh
    "Pathfinder":              "https://github.com/xathei/Pathfinder",
    "FFXI-NavMesh-Builder":    "https://github.com/LandSandBoat/FFXI-NavMesh-Builder",
    # ue
    "unreal-engine-mcp":       "https://github.com/flopperam/unreal-engine-mcp",
    "chongdashu-unreal-mcp":   "https://github.com/chongdashu/unreal-mcp",
    "kvick-UnrealMCP":         "https://github.com/kvick-games/UnrealMCP",
    "KawaiiPhysics":           "https://github.com/pafuhana1213/KawaiiPhysics",
    "UnrealGenAISupport":      "https://github.com/prajwalshettydev/UnrealGenAISupport",
    "Convai-UnrealEngine-SDK": "https://github.com/Conv-AI/Convai-UnrealEngine-SDK",
    # animation
    "ai4animationpy":          "https://github.com/facebookresearch/ai4animationpy",
    "motion-diffusion-model":  "https://github.com/GuyTevet/motion-diffusion-model",
    # visual
    "Real-ESRGAN":             "https://github.com/xinntao/Real-ESRGAN",
    "ComfyUI":                 "https://github.com/comfyanonymous/ComfyUI",
    # music
    "ACE-Step-1.5":            "https://github.com/ace-step/ACE-Step-1.5",
    # agents
    "generative_agents":       "https://github.com/joonspk-research/generative_agents",
    # combat_rl
    "PettingZoo":              "https://github.com/Farama-Foundation/PettingZoo",
    "neural-mmo":              "https://github.com/openai/neural-mmo",
    # auth
    "discord-oauth2-example":  "https://github.com/discord/discord-oauth2-example",
    "discord-oauth2.py":       "https://github.com/treeben77/discord-oauth2.py",
}


def head_sha(git_dir: Path) -> str:
    head_file = git_dir / "HEAD"
    if not head_file.exists():
        return "?"
    try:
        head = head_file.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return "?"
    if head.startswith("ref: "):
        ref = head[5:]
        ref_path = git_dir / ref
        if ref_path.exists():
            return ref_path.read_text(errors="replace").strip()[:12]
        # packed-refs fallback
        packed = git_dir / "packed-refs"
        if packed.exists():
            for line in packed.read_text(errors="replace").splitlines():
                if line.endswith(" " + ref):
                    return line.split()[0][:12]
    else:
        return head[:12]
    return "?"


def folder_size(path: Path) -> str:
    """Compute folder size by walking tree."""
    try:
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except Exception:
                    pass
        for unit in ("B", "KB", "MB", "GB"):
            if total < 1024:
                return f"{total:.1f} {unit}"
            total /= 1024
        return f"{total:.1f} TB"
    except Exception:
        return "?"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: regen_manifest.py <FFXI-Hardcore-path>")
        return 1
    root = Path(sys.argv[1]).resolve()
    repos = root / "repos"
    manifest = root / "MANIFEST.md"

    out = [
        "# FFXI Hardcore — upstream manifest",
        "",
        "Snapshot of the upstream repos and their HEAD commits at the time we cloned them.",
        "Re-run `scripts\\CLONE_REPOS.bat` to refresh; this manifest is regenerated on every clone.",
        "",
        f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
        "",
    ]

    for cat_dir, cat_label in CATEGORIES.items():
        cat_path = repos / cat_dir
        if not cat_path.exists():
            continue
        out.append(f"## {cat_label}")
        out.append("")
        out.append("| Repo | Upstream | HEAD | Local size |")
        out.append("|------|----------|------|------------|")
        for child in sorted(cat_path.iterdir()):
            if not child.is_dir():
                continue
            git_dir = child / ".git"
            sha = head_sha(git_dir) if git_dir.exists() else "(no .git)"
            url = UPSTREAM_URLS.get(child.name, "?")
            size = folder_size(child)
            out.append(f"| `{child.name}` | {url} | `{sha}` | {size} |")
        out.append("")

    manifest.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
