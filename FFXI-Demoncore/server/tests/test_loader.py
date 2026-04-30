"""Tests for the YAML loader.

Run:  python -m pytest server/tests/test_loader.py -v
"""
import pathlib
import textwrap

import pytest

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.loader import (
    load_agent_yaml,
    load_all_agents,
    load_batch_yaml,
    AgentProfile,
    ProfileError,
)


def write(tmp_path: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


# ------------------------------ valid cases ------------------------------

def test_loads_tier2_minimal(tmp_path):
    f = write(tmp_path, "vendor_a.yaml", """
        id: vendor_a
        name: Vendor A
        zone: bastok_markets
        position: [100, 200, 300]
        tier: 2_reflection
        role: vendor_a
        race: hume
        gender: m
        personality: "Blunt"
        starting_memory: "I sold a fish"
        mood_axes: [content, gruff]
        bark_pool:
          content: ["Hi"]
        schedule:
          - [06:00, "stall", "idle"]
    """)
    p = load_agent_yaml(f)
    assert p.id == "vendor_a"
    assert p.tier == "2_reflection"
    assert p.position == (100.0, 200.0, 300.0)
    assert p.is_llm_driven


def test_loads_tier3_full(tmp_path):
    f = write(tmp_path, "cid.yaml", """
        id: hero_cid
        name: Cid
        zone: bastok_markets
        position: [3000, 2200, 150]
        tier: 3_hero
        role: hero_cid
        race: hume
        gender: m
        personality: "Brilliant, tired"
        backstory: "Born in Bastok Mines"
        goals:
          - "Finish the airship"
        schedule:
          - [06:00, "workshop", "calculations"]
        relationships:
          hero_volker: "best friend"
        journal_seed: "Day 0. Got the math right."
    """)
    p = load_agent_yaml(f)
    assert p.id == "hero_cid"
    assert p.tier == "3_hero"
    assert p.is_llm_driven


# ------------------------------ failure cases ------------------------------

def test_missing_file(tmp_path):
    with pytest.raises(ProfileError, match="does not exist"):
        load_agent_yaml(tmp_path / "no.yaml")


def test_invalid_tier(tmp_path):
    f = write(tmp_path, "bad.yaml", """
        id: x
        name: X
        zone: z
        position: [0, 0, 0]
        tier: 99_omega
        role: r
        race: hume
        gender: m
    """)
    with pytest.raises(ProfileError, match="tier '99_omega' invalid"):
        load_agent_yaml(f)


def test_missing_tier_required_field(tmp_path):
    # Tier 2 but no personality / memory / mood_axes / bark_pool / schedule
    f = write(tmp_path, "bad.yaml", """
        id: x
        name: X
        zone: z
        position: [0, 0, 0]
        tier: 2_reflection
        role: r
        race: hume
        gender: m
    """)
    with pytest.raises(ProfileError, match="tier 2_reflection requires fields"):
        load_agent_yaml(f)


def test_bad_position(tmp_path):
    f = write(tmp_path, "bad.yaml", """
        id: x
        name: X
        zone: z
        position: [0, 0]
        tier: 1_scripted
        role: r
        race: hume
        gender: m
        schedule: []
        bark_pool: []
    """)
    with pytest.raises(ProfileError, match="position must be"):
        load_agent_yaml(f)


def test_invalid_race(tmp_path):
    f = write(tmp_path, "bad.yaml", """
        id: x
        name: X
        zone: z
        position: [0, 0, 0]
        tier: 1_scripted
        role: r
        race: half_elf
        gender: m
        schedule: []
        bark_pool: []
    """)
    with pytest.raises(ProfileError, match="race 'half_elf' invalid"):
        load_agent_yaml(f)


def test_load_all_skips_underscore_files(tmp_path):
    write(tmp_path, "_SCHEMA.md", "# schema doc — skipped")
    write(tmp_path, "_index.yaml", "should: be skipped")
    write(tmp_path, "good.yaml", """
        id: good
        name: Good
        zone: z
        position: [0, 0, 0]
        tier: 1_scripted
        role: r
        race: hume
        gender: m
        schedule: []
        bark_pool: []
    """)
    profiles = load_all_agents(tmp_path)
    assert len(profiles) == 1
    assert profiles[0].id == "good"


def test_load_all_collects_errors(tmp_path):
    write(tmp_path, "good.yaml", """
        id: good
        name: G
        zone: z
        position: [0, 0, 0]
        tier: 1_scripted
        role: r
        race: hume
        gender: m
        schedule: []
        bark_pool: []
    """)
    write(tmp_path, "bad1.yaml", """
        id: bad1
        name: B1
        zone: z
        position: [0, 0, 0]
        tier: 99_invalid
        role: r
        race: hume
        gender: m
    """)
    write(tmp_path, "bad2.yaml", """
        id: bad2
        position: [0, 0, 0]
    """)  # missing many fields
    with pytest.raises(ProfileError, match="2 profile.s. invalid"):
        load_all_agents(tmp_path)


def test_duplicate_ids_rejected(tmp_path):
    body = """
        id: same_id
        name: A
        zone: z
        position: [0, 0, 0]
        tier: 1_scripted
        role: r
        race: hume
        gender: m
        schedule: []
        bark_pool: []
    """
    write(tmp_path, "a.yaml", body)
    write(tmp_path, "b.yaml", body.replace("name: A", "name: B"))
    with pytest.raises(ProfileError, match="duplicate id 'same_id'"):
        load_all_agents(tmp_path)


def test_load_batch_yaml_tier0(tmp_path):
    """Tier 0 ambient wildlife batch — multiple agents in one file."""
    write(tmp_path, "_tier0.yaml", """
        agents:
          - id: rat_a
            name: rat
            zone: bastok_markets
            position: [0, 0, 0]
            tier: 0_reactive
            role: rat
            race: wildlife
            gender: n
            behavior_tree: /Game/AI/BT/Wildlife_Rat
            flee_radius_cm: 250
          - id: rat_b
            name: rat
            zone: bastok_markets
            position: [10, 10, 0]
            tier: 0_reactive
            role: rat
            race: wildlife
            gender: n
            behavior_tree: /Game/AI/BT/Wildlife_Rat
            flee_radius_cm: 250
    """)
    profiles = load_batch_yaml(tmp_path / "_tier0.yaml")
    assert len(profiles) == 2
    assert profiles[0].id == "rat_a"
    assert profiles[1].id == "rat_b"
    assert all(p.tier == "0_reactive" for p in profiles)


def test_load_all_picks_up_batch_files(tmp_path):
    """load_all_agents must merge regular + _tier*.yaml batch files."""
    # individual file
    write(tmp_path, "named_npc.yaml", """
        id: named
        name: Named
        zone: z
        position: [0, 0, 0]
        tier: 1_scripted
        role: r
        race: hume
        gender: m
        schedule: []
        bark_pool: []
    """)
    # batch file
    write(tmp_path, "_tier0_ambient.yaml", """
        agents:
          - id: rat_one
            name: rat
            zone: z
            position: [0, 0, 0]
            tier: 0_reactive
            role: rat
            race: wildlife
            gender: n
            behavior_tree: /Game/AI/BT/Rat
            flee_radius_cm: 200
    """)
    # underscore non-batch (should still be skipped)
    write(tmp_path, "_SCHEMA.md", "# schema doc")
    profiles = load_all_agents(tmp_path)
    ids = {p.id for p in profiles}
    assert ids == {"named", "rat_one"}


def test_batch_collects_errors_per_entry(tmp_path):
    """One bad entry in a batch shouldn't poison the batch — error
    message should pinpoint the bad entry by index."""
    f = write(tmp_path, "_tier1.yaml", """
        agents:
          - id: good
            name: G
            zone: z
            position: [0, 0, 0]
            tier: 1_scripted
            role: r
            race: hume
            gender: m
            schedule: []
            bark_pool: []
          - id: bad
            position: [0, 0, 0]
    """)
    with pytest.raises(ProfileError, match="agents\\[1\\]"):
        load_batch_yaml(f)


def test_real_zaldon_profile(tmp_path):
    """Smoke-test against a profile shaped like the actual zaldon.yaml."""
    f = write(tmp_path, "zaldon.yaml", """
        id: vendor_zaldon
        name: Zaldon
        zone: bastok_markets
        position: [-2400, -2400, 130]
        tier: 2_reflection
        role: vendor_zaldon
        race: hume
        gender: m
        voice_profile: /Content/Voices/profiles/zaldon.wav
        appearance: "Weathered fisherman"
        personality: "Blunt, proud of his catch"
        starting_memory: "Sold a frostfish to a galkan warrior yesterday"
        mood_axes: [content, gruff, melancholy]
        bark_pool:
          content:
            - "Fresh from Bibiki Bay this morning."
          gruff:
            - "Not selling to you today."
          melancholy:
            - "Just take whatever."
        schedule:
          - [06:00, "stall_position", "setup_stall"]
        relationships:
          cid: "old drinking buddy"
    """)
    p = load_agent_yaml(f)
    assert p.name == "Zaldon"
    assert p.voice_profile == "/Content/Voices/profiles/zaldon.wav"
    assert p.raw["mood_axes"] == ["content", "gruff", "melancholy"]
