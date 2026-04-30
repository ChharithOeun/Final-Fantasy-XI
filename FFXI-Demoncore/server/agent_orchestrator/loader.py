"""YAML loader + schema validation for Demoncore agent profiles.

Validates against the contract in agents/_SCHEMA.md. Raises ProfileError
with a path-context-aware message so authoring mistakes surface in
seconds (not at runtime when an LLM reflection fails on a missing key).
"""
from __future__ import annotations

import dataclasses
import pathlib
import typing as t

import yaml


VALID_TIERS = {"0_reactive", "1_scripted", "2_reflection", "3_hero", "4_rl"}

VALID_RACES = {
    "hume", "elvaan", "tarutaru", "mithra", "galka",
    "beastman_quadav", "beastman_orc", "beastman_yagudo",
    "beastman_goblin", "beastman_tonberry", "beastman_kindred",
    "wildlife", "spirit", "demon",
}

VALID_GENDERS = {"m", "f", "n"}

# Required fields shared across all tiers
COMMON_REQUIRED = {"id", "name", "zone", "position", "tier", "role", "race", "gender"}

# Tier-specific required fields
TIER_REQUIRED = {
    "0_reactive":   {"behavior_tree", "flee_radius_cm"},
    "1_scripted":   {"schedule", "bark_pool"},
    "2_reflection": {"personality", "starting_memory", "mood_axes",
                     "bark_pool", "schedule"},
    "3_hero":       {"personality", "backstory", "goals", "schedule",
                     "relationships", "journal_seed"},
    "4_rl":         {"mob_class", "policy_onnx", "state_features",
                     "action_space"},
}


class ProfileError(Exception):
    """Raised when an agent YAML is malformed or violates the schema."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclasses.dataclass
class AgentProfile:
    """In-memory representation of one agent's YAML profile.

    Stays close to the YAML structure to make round-tripping easy. The
    `raw` dict holds the full payload so tier-specific code can pull
    arbitrary fields without us having to mirror every optional key.
    """
    id: str
    name: str
    zone: str
    position: tuple[float, float, float]
    tier: str
    role: str
    race: str
    gender: str
    voice_profile: t.Optional[str]
    appearance: t.Optional[str]
    raw: dict

    @property
    def is_llm_driven(self) -> bool:
        return self.tier in ("2_reflection", "3_hero")


def load_agent_yaml(path: str | pathlib.Path) -> AgentProfile:
    """Parse and validate a single agent YAML file.

    Raises ProfileError if the file is missing, malformed, or violates
    the schema. The error message always includes the path and the
    specific field involved so authors can fix in one pass.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise ProfileError(str(p), "file does not exist")

    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ProfileError(str(p), f"YAML parse failed: {e}") from e

    if not isinstance(data, dict):
        raise ProfileError(str(p), "top-level must be a mapping")

    return _profile_from_dict(data, str(p))


def _profile_from_dict(data: dict, source: str) -> AgentProfile:
    """Validate and construct one AgentProfile from a dict (shared helper)."""
    missing = COMMON_REQUIRED - data.keys()
    if missing:
        raise ProfileError(source, f"missing required fields: {sorted(missing)}")

    tier = data["tier"]
    if tier not in VALID_TIERS:
        raise ProfileError(
            source,
            f"tier '{tier}' invalid; expected one of {sorted(VALID_TIERS)}",
        )

    tier_missing = TIER_REQUIRED.get(tier, set()) - data.keys()
    if tier_missing:
        raise ProfileError(
            source,
            f"tier {tier} requires fields: {sorted(tier_missing)}",
        )

    pos = data["position"]
    if not (isinstance(pos, (list, tuple)) and len(pos) == 3
            and all(isinstance(x, (int, float)) for x in pos)):
        raise ProfileError(
            source,
            "position must be [x, y, z] with three numeric values",
        )

    if data["race"] not in VALID_RACES:
        raise ProfileError(
            source,
            f"race '{data['race']}' invalid; expected one of {sorted(VALID_RACES)}",
        )
    if data["gender"] not in VALID_GENDERS:
        raise ProfileError(
            source,
            f"gender '{data['gender']}' invalid; expected one of {VALID_GENDERS}",
        )

    return AgentProfile(
        id=data["id"],
        name=data["name"],
        zone=data["zone"],
        position=tuple(float(x) for x in pos),  # type: ignore[arg-type]
        tier=tier,
        role=data["role"],
        race=data["race"],
        gender=data["gender"],
        voice_profile=data.get("voice_profile"),
        appearance=data.get("appearance"),
        raw=data,
    )


def load_batch_yaml(path: str | pathlib.Path) -> list[AgentProfile]:
    """Parse a multi-agent batch file with top-level `agents:` list.

    Used for Tier 0 ambient wildlife and Tier 1 crowd NPCs where each
    agent is a few lines of YAML and bundling reduces filesystem chatter.
    """
    p = pathlib.Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ProfileError(str(p), f"YAML parse failed: {e}") from e

    if not isinstance(data, dict) or "agents" not in data:
        raise ProfileError(str(p), "batch file must have top-level 'agents:' list")

    agents = data["agents"]
    if not isinstance(agents, list):
        raise ProfileError(str(p), "'agents' must be a list")

    profiles: list[AgentProfile] = []
    errors: list[ProfileError] = []
    for i, entry in enumerate(agents):
        source = f"{p}#agents[{i}]"
        if not isinstance(entry, dict):
            errors.append(ProfileError(source, "entry must be a mapping"))
            continue
        try:
            profiles.append(_profile_from_dict(entry, source))
        except ProfileError as e:
            errors.append(e)

    if errors:
        msg = "\n".join(f"  - {e}" for e in errors)
        raise ProfileError(str(p), f"{len(errors)} profile(s) invalid:\n{msg}")

    return profiles


def load_all_agents(agents_dir: str | pathlib.Path) -> list[AgentProfile]:
    """Walk a directory of agent YAMLs and return every parsed profile.

    File handling:
      - Standard YAMLs (no leading underscore): loaded as one profile each
      - `_tier*.yaml`: loaded as batch files with top-level `agents:` list
        (used for Tier 0 ambient wildlife and Tier 1 crowd NPCs)
      - All other `_*.yaml` and `_*.md`: skipped (docs, indexes, etc.)

    Per-file errors are collected and re-raised together so an author
    sees every mistake in one pass.
    """
    d = pathlib.Path(agents_dir)
    if not d.is_dir():
        raise ProfileError(str(d), "agents directory does not exist")

    profiles: list[AgentProfile] = []
    errors: list[ProfileError] = []
    for f in sorted(d.glob("*.yaml")):
        if f.name.startswith("_"):
            # Batch files use _tier<N>_<name>.yaml convention
            if f.name.startswith("_tier"):
                try:
                    profiles.extend(load_batch_yaml(f))
                except ProfileError as e:
                    errors.append(e)
            # Other underscore files (e.g. _index.yaml) are intentionally skipped
            continue
        try:
            profiles.append(load_agent_yaml(f))
        except ProfileError as e:
            errors.append(e)

    if errors:
        msg = "\n".join(f"  - {e}" for e in errors)
        raise ProfileError(str(d), f"{len(errors)} profile(s) invalid:\n{msg}")

    # Detect duplicate IDs
    ids: dict[str, str] = {}
    for prof in profiles:
        if prof.id in ids:
            raise ProfileError(
                str(d),
                f"duplicate id '{prof.id}': declared in both "
                f"{ids[prof.id]} and matching path",
            )
        ids[prof.id] = prof.name

    return profiles
