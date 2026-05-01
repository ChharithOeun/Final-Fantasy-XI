"""Tests for the boss critic.

Run:  python -m pytest server/tests/test_boss_critic.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from boss_critic import (
    BossCritic,
    EncounterSnapshot,
    StrategyHint,
)
from boss_critic.critic import (
    OllamaBackend,
    PartyMember,
    StubBackend,
    _compose_critic_prompt,
    _parse_llm_response,
    _rule_based_strategy,
)


# ----------------------- helpers -----------------------

def _basic_snap(**overrides) -> EncounterSnapshot:
    base = EncounterSnapshot(
        boss_id="hero_maat",
        boss_phase="bloodied",
        boss_hp_pct=0.55,
        boss_mood="gruff",
        party=[
            PartyMember(agent_id="war_alice", job="WAR", level=75),
            PartyMember(agent_id="whm_bob",   job="WHM", level=75, is_back_row=True),
            PartyMember(agent_id="blm_carl",  job="BLM", level=75, is_back_row=True),
        ],
        skillchains_last_30s=[],
        magic_bursts_last_30s=[],
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


# ----------------------- rule-based critic -----------------------

def test_blm_cheese_triggers_gap_close():
    snap = _basic_snap(
        boss_phase="pristine",
        magic_bursts_last_30s=[
            {"element": "ice", "target": "boss"},
            {"element": "ice", "target": "boss"},
            {"element": "ice", "target": "boss"},
        ],
    )
    hint = _rule_based_strategy(snap)
    assert hint.next_attack_priority == "tornado_kick"
    assert hint.next_target_player == "blm_carl"
    assert hint.boss_mood_shift == "gruff"
    assert "Tarutaru" in (hint.contextual_bark or "")


def test_l3_skillchain_shifts_boss_to_contemplative():
    snap = _basic_snap(
        skillchains_last_30s=[
            {"element": "light", "level": 3, "contributors": ["a", "b", "c"]},
        ],
    )
    hint = _rule_based_strategy(snap)
    assert hint.boss_mood_shift == "contemplative"
    assert "Light" in (hint.contextual_bark or "")
    assert hint.next_attack_priority == "counterstance"


def test_skillchain_without_ailment_burst_silences_blm():
    """Party chains hard but doesn't ail-burst → boss silences the BLM."""
    snap = _basic_snap(
        skillchains_last_30s=[
            {"element": "compression", "level": 1, "contributors": ["a", "b"]},
            {"element": "induration", "level": 1, "contributors": ["c", "d"]},
        ],
        magic_bursts_last_30s=[
            # Only direct-damage MBs, no amplified ailments
            {"element": "ice", "target": "boss", "was_amplified": False},
        ],
    )
    hint = _rule_based_strategy(snap)
    assert hint.silence_priority_player == "blm_carl"
    assert hint.next_attack_priority == "silence_aoe"


def test_ailment_stack_triggers_erase():
    """Multiple amplified ailments → boss pops Erase next phase."""
    snap = _basic_snap(
        magic_bursts_last_30s=[
            {"element": "slow", "target": "boss", "was_amplified": True},
            {"element": "bind", "target": "boss", "was_amplified": True},
            {"element": "silence", "target": "boss", "was_amplified": True},
        ],
    )
    hint = _rule_based_strategy(snap)
    assert hint.next_attack_priority == "erase_self"
    assert hint.boss_mood_shift == "gruff"
    assert "OFF" in (hint.contextual_bark or "")


def test_party_panicked_presses_for_kill():
    snap = _basic_snap(
        party=[
            PartyMember(agent_id="war_alice", job="WAR", current_mood="fearful"),
            PartyMember(agent_id="whm_bob",   job="WHM", current_mood="fearful",
                         is_back_row=True),
            PartyMember(agent_id="blm_carl",  job="BLM", current_mood="alert",
                         is_back_row=True),
        ],
        boss_phase="wounded",
        boss_hp_pct=0.40,
    )
    hint = _rule_based_strategy(snap)
    assert hint.boss_mood_shift == "furious"
    assert hint.should_use_ultimate is True
    assert hint.next_target_player == "whm_bob"


def test_intervention_blocked_escalates_to_furious():
    snap = _basic_snap(boss_was_intervention_blocked=True)
    hint = _rule_based_strategy(snap)
    assert hint.boss_mood_shift == "furious"
    assert hint.contextual_bark == "YOU DARE!"


def test_apex_party_play_triggers_yield():
    """Boss in broken phase + party showed L3 + ailment burst + first kill → yield."""
    snap = _basic_snap(
        boss_phase="broken",
        boss_hp_pct=0.05,
        skillchains_last_30s=[
            {"element": "light", "level": 3, "contributors": ["a", "b", "c"]},
        ],
        magic_bursts_last_30s=[
            {"element": "slow", "target": "boss", "was_amplified": True},
        ],
        boss_kill_count_by_party=0,
    )
    hint = _rule_based_strategy(snap)
    assert hint.should_yield is True
    assert hint.boss_mood_shift == "contemplative"
    assert "earned" in (hint.contextual_bark or "")


def test_default_rotation_when_no_pattern():
    snap = _basic_snap()
    hint = _rule_based_strategy(snap)
    assert hint.next_attack_priority == "asuran_fists"
    assert hint.confidence >= 0.5


# ----------------------- prompt + parser -----------------------

def test_compose_prompt_includes_party_jobs():
    snap = _basic_snap()
    prompt = _compose_critic_prompt(snap, personality="Stern monk",
                                      backstory="Crystal War vet")
    assert "WAR" in prompt
    assert "WHM" in prompt
    assert "BLM" in prompt
    assert "Stern monk" in prompt


def test_compose_prompt_summarizes_skillchains():
    snap = _basic_snap(
        skillchains_last_30s=[
            {"element": "fusion", "level": 2, "contributors": ["a", "b"]},
        ],
    )
    prompt = _compose_critic_prompt(snap)
    assert "fusion" in prompt or "L2" in prompt


def test_parse_llm_response_extracts_json():
    snap = _basic_snap()
    response = """
    Here's my decision:
    {
      "next_attack_priority": "tornado_kick",
      "next_target_player": "blm_carl",
      "silence_priority_player": null,
      "should_use_ultimate": false,
      "should_yield": false,
      "contextual_bark": "Test!",
      "boss_mood_shift": "gruff",
      "strategy_reason": "test reason",
      "confidence": 0.85
    }
    """
    hint = _parse_llm_response(response, fallback=snap)
    assert hint.next_attack_priority == "tornado_kick"
    assert hint.next_target_player == "blm_carl"
    assert hint.contextual_bark == "Test!"
    assert hint.confidence == 0.85


def test_parse_llm_response_handles_markdown_fences():
    snap = _basic_snap()
    response = """```json
{
  "next_attack_priority": "asuran_fists",
  "next_target_player": "tank",
  "should_use_ultimate": false,
  "should_yield": false,
  "contextual_bark": "...",
  "boss_mood_shift": "alert",
  "strategy_reason": "wrapped in fence",
  "confidence": 0.5
}
```"""
    hint = _parse_llm_response(response, fallback=snap)
    assert hint.next_attack_priority == "asuran_fists"


def test_parse_llm_response_falls_back_on_garbage():
    snap = _basic_snap()
    hint = _parse_llm_response("not json at all", fallback=snap)
    # Should fall back to rules-based; since snap is bloodied + no special
    # signals, we get the default rotation
    assert hint.next_attack_priority == "asuran_fists"


# ----------------------- BossCritic class -----------------------

def test_boss_critic_stub_evaluation():
    critic = BossCritic(boss_id="hero_maat", backend="stub")
    snap = _basic_snap()
    hint = critic.evaluate_sync(snap, now=10.0)
    assert hint.next_attack_priority is not None


def test_boss_critic_rate_limited():
    """Calling within min_seconds_between_calls returns cached hint."""
    critic = BossCritic(boss_id="hero_maat", backend="stub",
                          min_seconds_between_calls=30.0)
    snap1 = _basic_snap(boss_phase="pristine")
    hint1 = critic.evaluate_sync(snap1, now=10.0)

    # Second call within 30s → returns cached
    snap2 = _basic_snap(boss_phase="wounded")
    hint2 = critic.evaluate_sync(snap2, now=15.0)
    assert hint2 is hint1   # same object (cached)

    # Third call after 30s elapsed → fresh evaluation
    hint3 = critic.evaluate_sync(snap2, now=50.0)
    assert hint3 is not hint1


def test_boss_critic_unknown_backend_raises():
    with pytest.raises(ValueError, match="unknown critic backend"):
        BossCritic(boss_id="x", backend="not_real")


def test_ollama_backend_unreachable_falls_back_to_stub():
    """If Ollama is down, the critic still produces a hint (rule-based)."""
    import asyncio
    backend = OllamaBackend(url="http://localhost:1", timeout_seconds=0.1)
    snap = _basic_snap()

    async def run():
        return await backend.decide_async(snap)
    hint = asyncio.run(run())
    # Falls back to rules-based; should produce a valid hint
    assert isinstance(hint, StrategyHint)
    assert hint.next_attack_priority is not None
