"""5-scenario catalog from MAGIC_BURST_SCENARIOS.md.

The 5 worked combat scripts. Beat sequences are condensed to the
key inflection points each scenario tests — not every doc frame —
so the harness focuses on systems-firing assertions.
"""
from __future__ import annotations

from .scenario import Scenario, ScenarioBeat, ScenarioOutcome


SCENARIO_1_ANTI_CHEESE = Scenario(
    scenario_id="s1",
    title="The Anti-Cheese Lesson (first failed kite)",
    setup=("lvl-25 BLM/WHM facing a Naga Renja (lvl 28) in "
              "Phomiuna Aqueducts. Player thinks BLM kiting + nuking "
              "is right. Naga is sprint-NIN — the lesson is they "
              "CAN'T be kited."),
    location_zone="phomiuna_aqueducts",
    player_level_band=(25, 25),
    party_jobs=("BLM",),
    hostile_classes=("naga_renja_nin",),
    expected_outcome=ScenarioOutcome.LESSON_LEARNED,
    systems_firing=(
        "VISUAL_HEALTH_SYSTEM", "WEIGHT_PHYSICS",
        "NIN_HAND_SIGNS", "AUDIBLE_CALLOUTS",
    ),
    duration_seconds=12.0,
    beats=(
        ScenarioBeat(t_seconds=0.0, actor_id="player",
                       event_kind="check",
                       payload={"target_id": "naga", "distance": 25.0}),
        ScenarioBeat(t_seconds=0.5, actor_id="player",
                       event_kind="cast_start",
                       payload={"spell": "stoneskin"},
                       expected_systems=("WEIGHT_PHYSICS",)),
        ScenarioBeat(t_seconds=0.8, actor_id="naga",
                       event_kind="seal_begin",
                       payload={"sequence": "hyoton_ichi"},
                       expected_systems=("NIN_HAND_SIGNS",)),
        ScenarioBeat(t_seconds=1.6, actor_id="naga",
                       event_kind="ninjutsu_launch",
                       payload={"spell": "hyoton_ichi"}),
        ScenarioBeat(t_seconds=1.9, actor_id="player",
                       event_kind="visible_stage_change",
                       payload={"to": "scuffed"},
                       expected_systems=("VISUAL_HEALTH_SYSTEM",),
                       expected_callout="grunt"),
        ScenarioBeat(t_seconds=2.1, actor_id="naga",
                       event_kind="sprint_pursuit"),
        ScenarioBeat(t_seconds=3.5, actor_id="naga",
                       event_kind="bind_lands",
                       payload={"target": "player"}),
        ScenarioBeat(t_seconds=8.0, actor_id="player",
                       event_kind="sleep_lands",
                       payload={"target": "naga"}),
        ScenarioBeat(t_seconds=9.0, actor_id="player",
                       event_kind="cure_self",
                       expected_callout="Cure!"),
        ScenarioBeat(t_seconds=12.0, actor_id="player",
                       event_kind="lesson_learned"),
    ),
)


SCENARIO_2_FIRST_SC = Scenario(
    scenario_id="s2",
    title="The First Skillchain (party tutorial completion)",
    setup=("lvl 12 party of 2 (WAR + WHM) facing 2 Goblin "
              "Pickpockets + 1 Goblin Smithy. Skillchain tutorial "
              "with Cid done; the players are supposed to chain-close "
              "on the boss."),
    location_zone="bastok_mines_side_tunnel",
    player_level_band=(12, 12),
    party_jobs=("WAR", "WHM"),
    hostile_classes=("goblin_pickpocket", "goblin_smithy"),
    expected_outcome=ScenarioOutcome.TUTORIAL_COMPLETE,
    systems_firing=(
        "AOE_TELEGRAPH", "SKILLCHAIN_SYSTEM",
        "AUDIBLE_CALLOUTS", "VISUAL_HEALTH_SYSTEM",
    ),
    duration_seconds=14.0,
    beats=(
        ScenarioBeat(t_seconds=0.0, actor_id="war",
                       event_kind="provoke",
                       payload={"target": "goblin_smithy"}),
        ScenarioBeat(t_seconds=1.0, actor_id="goblin_smithy",
                       event_kind="aoe_telegraph_begin",
                       payload={"shape": "cone", "name": "hammer_slam"},
                       expected_systems=("AOE_TELEGRAPH",)),
        ScenarioBeat(t_seconds=2.0, actor_id="war",
                       event_kind="dodge_telegraph"),
        ScenarioBeat(t_seconds=3.0, actor_id="war",
                       event_kind="ws_open",
                       payload={"ws": "crescent_moon",
                                  "property": "compression"},
                       expected_callout="Skillchain open!",
                       expected_systems=("SKILLCHAIN_SYSTEM",)),
        ScenarioBeat(t_seconds=4.0, actor_id="war",
                       event_kind="callout",
                       expected_callout="Close it — transfixion!"),
        ScenarioBeat(t_seconds=5.0, actor_id="whm",
                       event_kind="ws_close",
                       payload={"ws": "hexa_strike",
                                  "chain": "compression"},
                       expected_callout="Closing — Compression!"),
        ScenarioBeat(t_seconds=5.5, actor_id="whm",
                       event_kind="mb_window_open"),
        ScenarioBeat(t_seconds=8.5, actor_id="whm",
                       event_kind="mb_window_expired"),
        ScenarioBeat(t_seconds=14.0, actor_id="goblin_smithy",
                       event_kind="visible_stage_change",
                       payload={"to": "wounded"},
                       expected_systems=("VISUAL_HEALTH_SYSTEM",)),
    ),
)


SCENARIO_3_THE_SAVE = Scenario(
    scenario_id="s3",
    title="The Save (Intervention MB at apex)",
    setup=("Lvl 75 party against Maat. Maat closes Distortion on "
              "tank, BLM mob winds up Blizzard IV in burst window — "
              "8000 damage incoming on 5500-HP tank. WHM Cure IV "
              "intervention saves the wipe."),
    location_zone="balgas_dais",
    player_level_band=(75, 75),
    party_jobs=("WAR", "WHM", "RDM", "BLM", "BRD", "NIN"),
    hostile_classes=("maat",),
    expected_outcome=ScenarioOutcome.HEROIC_SAVE,
    systems_firing=(
        "INTERVENTION_MB", "SKILLCHAIN_SYSTEM",
        "AUDIBLE_CALLOUTS", "VISUAL_HEALTH_SYSTEM",
        "MOOD_SYSTEM",
    ),
    duration_seconds=8.0,
    beats=(
        ScenarioBeat(t_seconds=0.0, actor_id="maat",
                       event_kind="ws_close",
                       payload={"chain_element": "distortion",
                                  "target": "tank",
                                  "predicted_mb_damage": 8000},
                       expected_systems=("INTERVENTION_MB",)),
        ScenarioBeat(t_seconds=0.5, actor_id="whm",
                       event_kind="cast_start",
                       payload={"spell": "cure_iv"}),
        ScenarioBeat(t_seconds=2.5, actor_id="whm",
                       event_kind="cure_lands_in_window",
                       payload={"amplification": 3.0,
                                  "regen_seconds": 30},
                       expected_callout="Magic Burst — Cure!",
                       expected_systems=("INTERVENTION_MB",)),
        ScenarioBeat(t_seconds=2.5, actor_id="tank",
                       event_kind="damage_cancelled",
                       payload={"would_be_damage": 8000,
                                  "actual_damage": 0}),
        ScenarioBeat(t_seconds=2.5, actor_id="whm",
                       event_kind="dual_cast_unlocked",
                       payload={"family": "cure", "duration": 30}),
        ScenarioBeat(t_seconds=8.0, actor_id="bystanders",
                       event_kind="mood_celebration",
                       payload={"mood": "content", "delta": 0.4},
                       expected_systems=("MOOD_SYSTEM",)),
    ),
)


SCENARIO_4_MOB_HEALER = Scenario(
    scenario_id="s4",
    title="The Mob-Healer Block (player chain failure)",
    setup=("Player party chains a Quadav Helmsman; an adjacent "
              "Quadav Healer reads the chain, casts Cure IV, and "
              "lands in the player chain's window. The chain is "
              "intercepted."),
    location_zone="beadeaux",
    player_level_band=(50, 60),
    party_jobs=("WAR", "NIN", "WHM", "BLM"),
    hostile_classes=("quadav_helmsman", "quadav_healer"),
    expected_outcome=ScenarioOutcome.CHAIN_BLOCKED,
    systems_firing=(
        "INTERVENTION_MB", "SKILLCHAIN_SYSTEM",
        "AUDIBLE_CALLOUTS",
    ),
    duration_seconds=6.0,
    beats=(
        ScenarioBeat(t_seconds=0.0, actor_id="war",
                       event_kind="ws_open",
                       expected_callout="Skillchain open!"),
        ScenarioBeat(t_seconds=1.5, actor_id="nin",
                       event_kind="ws_close",
                       payload={"chain_element": "distortion"}),
        ScenarioBeat(t_seconds=1.7, actor_id="quadav_healer",
                       event_kind="cast_start",
                       payload={"spell": "cure_iv",
                                  "target": "quadav_helmsman"}),
        ScenarioBeat(t_seconds=4.0, actor_id="quadav_healer",
                       event_kind="cure_lands_in_window",
                       payload={"amplification": 3.0},
                       expected_callout="[quadav_healer voice] Cure burst!"),
        ScenarioBeat(t_seconds=4.0, actor_id="quadav_helmsman",
                       event_kind="damage_cancelled",
                       payload={"would_be_damage": 4000,
                                  "actual_damage": 0}),
        ScenarioBeat(t_seconds=4.0, actor_id="quadav_healer",
                       event_kind="dual_cast_unlocked",
                       payload={"family": "cure"}),
        ScenarioBeat(t_seconds=4.5, actor_id="player_party",
                       event_kind="mood_furious",
                       payload={"mood_delta": 0.4}),
    ),
)


SCENARIO_5_OPEN_WORLD = Scenario(
    scenario_id="s5",
    title="The Open World Tense (random encounter)",
    setup=("Lone lvl-40 RNG running across La Theine Plateau. "
              "Wanders too close to a Greater Colibri pair. The "
              "world ambushes — terrain wind buff on the Colibris, "
              "Sprint not available, no Reraise."),
    location_zone="la_theine_plateau",
    player_level_band=(40, 40),
    party_jobs=("RNG",),
    hostile_classes=("greater_colibri",),
    expected_outcome=ScenarioOutcome.SURVIVAL,
    systems_firing=(
        "TERRAIN_WEATHER", "AGGRO_SYSTEM",
        "VISUAL_HEALTH_SYSTEM", "MOOD_SYSTEM",
        "AUDIBLE_CALLOUTS",
    ),
    duration_seconds=15.0,
    beats=(
        ScenarioBeat(t_seconds=0.0, actor_id="player",
                       event_kind="enter_zone",
                       payload={"zone": "la_theine_plateau",
                                  "weather": "clear"}),
        ScenarioBeat(t_seconds=2.0, actor_id="colibri_a",
                       event_kind="aggro_acquired",
                       payload={"sense": "sight"},
                       expected_systems=("AGGRO_SYSTEM",)),
        ScenarioBeat(t_seconds=3.0, actor_id="colibri_b",
                       event_kind="aggro_acquired",
                       payload={"sense": "scent"}),
        ScenarioBeat(t_seconds=5.0, actor_id="terrain",
                       event_kind="terrain_buff",
                       payload={"affinity": "wind",
                                  "applies_to": "colibris"},
                       expected_systems=("TERRAIN_WEATHER",)),
        ScenarioBeat(t_seconds=8.0, actor_id="player",
                       event_kind="visible_stage_change",
                       payload={"to": "wounded"},
                       expected_systems=("VISUAL_HEALTH_SYSTEM",)),
        ScenarioBeat(t_seconds=10.0, actor_id="player",
                       event_kind="callout",
                       expected_callout="grunt of pain"),
        ScenarioBeat(t_seconds=15.0, actor_id="player",
                       event_kind="survives_or_flees"),
    ),
)


SCENARIOS: tuple[Scenario, ...] = (
    SCENARIO_1_ANTI_CHEESE,
    SCENARIO_2_FIRST_SC,
    SCENARIO_3_THE_SAVE,
    SCENARIO_4_MOB_HEALER,
    SCENARIO_5_OPEN_WORLD,
)


SCENARIOS_BY_ID: dict[str, Scenario] = {s.scenario_id: s
                                              for s in SCENARIOS}


def get_scenario(scenario_id: str) -> Scenario:
    """Look up a scenario by id. Raises KeyError on unknown."""
    return SCENARIOS_BY_ID[scenario_id]


def scenarios_using_system(system_id: str) -> tuple[Scenario, ...]:
    """Return all scenarios whose 'systems firing' list contains `system_id`."""
    return tuple(s for s in SCENARIOS if s.involves_system(system_id))
