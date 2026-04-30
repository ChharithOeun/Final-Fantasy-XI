"""Event → mood-delta lookup table.

Static data only. No imports from the rest of the orchestrator.
Authors can extend this list without touching any other file.

The match logic:
    EVENT_DELTAS is a list of tuples; first match wins.
    role_glob "*" matches anything.
    role_glob "*vendor*" matches any role containing "vendor".
"""
from __future__ import annotations

import fnmatch
import typing as t


# Each entry: (event_kind, role_glob) -> (mood_label, intensity_delta)
# A negative intensity_delta nudges *away from* that mood.
EVENT_DELTAS: list[tuple[tuple[str, str], tuple[str, float]]] = [
    # AOE / structure damage
    (("aoe_near", "*vendor*"),                ("gruff",       +0.30)),
    (("aoe_near", "*"),                       ("alert",       +0.20)),
    (("structure_destroyed_near", "*"),       ("gruff",       +0.40)),
    (("structure_healed_near", "*pellah*"),   ("content",     +0.20)),

    # Outlaw interactions — different roles read it differently
    (("outlaw_walked_past", "*guard*"),       ("alert",       +0.50)),
    (("outlaw_walked_past", "*soldier*"),     ("alert",       +0.50)),
    (("outlaw_walked_past", "*vendor*"),      ("gruff",       +0.20)),
    (("outlaw_walked_past", "*beggar*"),      ("fearful",     +0.30)),
    (("outlaw_walked_past", "*pickpocket*"),  ("content",     +0.20)),
    (("outlaw_walked_past", "*hero*"),        ("alert",       +0.30)),

    # Friend events — relationship-aware
    (("friend_attacked", "*"),                ("furious",     +0.60)),
    (("friend_died", "*"),                    ("melancholy",  +0.70)),
    (("friend_recovered", "*"),               ("content",     +0.30)),

    # Nation / siege
    (("nation_raid_alarm", "*civilian*"),     ("fearful",     +0.60)),
    (("nation_raid_alarm", "*soldier*"),      ("alert",       +0.70)),
    (("nation_raid_alarm", "*hero*"),         ("alert",       +0.50)),
    (("nation_raid_alarm", "*"),              ("alert",       +0.40)),

    # Commerce
    (("payment_received", "*vendor*"),        ("content",     +0.20)),
    (("haggle_failed", "*vendor*"),           ("gruff",       +0.15)),
    (("rare_item_sold", "*vendor*"),          ("content",     +0.40)),

    # Repair NPC events
    (("repair_completed", "*pellah*"),        ("content",     +0.30)),
    (("repair_failed", "*pellah*"),           ("weary",       +0.20)),

    # Daily / circadian
    (("daily_loop_morning", "*tavern_drunk*"),("content",     +0.20)),
    (("daily_loop_evening", "*tavern_drunk*"),("drunk",       +0.50)),
    (("nighttime", "*pickpocket*"),           ("content",     +0.20)),
    (("daytime", "*pickpocket*"),             ("alert",       +0.20)),
    (("morning", "*street_musician*"),        ("content",     +0.10)),

    # Weather
    (("rain_started", "*"),                   ("melancholy",  +0.10)),
    (("first_snow", "*"),                     ("content",     +0.15)),
    (("clear_sky", "*tarutaru*"),             ("content",     +0.10)),

    # Ambient world events
    (("forge_visible_from_plaza", "*bastok*"),("content",     +0.08)),
    (("smokestack_extra_puff", "*bastok*"),   ("gruff",       +0.05)),
    (("festival_active", "*"),                ("content",     +0.30)),
    (("major_npc_died_today", "*"),           ("melancholy",  +0.15)),

    # Damage-stage transitions (from VISUAL_HEALTH_SYSTEM.md). When an
    # agent's visible health crosses a stage boundary, mood shifts. This
    # is what makes a wounded vendor visibly angrier and a wounded
    # soldier more alert.
    (("damage_stage_scuffed",  "*"),          ("alert",       +0.10)),
    (("damage_stage_bloodied", "*hero*"),     ("alert",       +0.30)),
    (("damage_stage_bloodied", "*soldier*"),  ("alert",       +0.40)),
    (("damage_stage_bloodied", "*vendor*"),   ("fearful",     +0.30)),
    (("damage_stage_bloodied", "*beggar*"),   ("fearful",     +0.50)),
    (("damage_stage_bloodied", "*civilian*"), ("fearful",     +0.40)),
    (("damage_stage_wounded",  "*hero*"),     ("furious",     +0.50)),
    (("damage_stage_wounded",  "*soldier*"),  ("furious",     +0.40)),
    (("damage_stage_wounded",  "*vendor*"),   ("fearful",     +0.50)),
    (("damage_stage_wounded",  "*"),          ("fearful",     +0.30)),
    (("damage_stage_grievous", "*"),          ("fearful",     +0.60)),
    (("damage_stage_broken",   "*"),          ("fearful",     +0.80)),

    # Healing back UP also matters — the world breathes
    (("damage_stage_healed_to_pristine", "*"),("content",     +0.20)),
    (("damage_stage_healed_to_scuffed",  "*"),("content",     +0.10)),

    # Weight events (from WEIGHT_PHYSICS.md). Effective weight changes
    # mood when it crosses meaningful thresholds.
    (("encumbered_critical", "*civilian*"),   ("weary",       +0.40)),
    (("encumbered_critical", "*hero*"),       ("weary",       +0.20)),
    (("encumbered_critical", "*"),            ("weary",       +0.30)),
    (("gravity_applied", "*"),                ("weary",       +0.25)),
    (("haste_applied", "*"),                  ("content",     +0.15)),
    (("mounted_with_mazurka", "*"),           ("content",     +0.10)),

    # AOE telegraph events (from AOE_TELEGRAPH.md). NPCs visibly react
    # when an AOE telegraph appears under them — bystander civilians
    # panic, soldiers go alert, heroes stay alert (combat-ready).
    (("aoe_telegraph_visible_to_self", "*civilian*"),  ("fearful", +0.40)),
    (("aoe_telegraph_visible_to_self", "*beggar*"),    ("fearful", +0.50)),
    (("aoe_telegraph_visible_to_self", "*soldier*"),   ("alert",   +0.30)),
    (("aoe_telegraph_visible_to_self", "*hero*"),      ("alert",   +0.40)),
    (("aoe_telegraph_visible_to_self", "*"),           ("alert",   +0.20)),
    (("dodged_aoe", "*hero*"),                          ("content", +0.20)),
    (("dodged_aoe", "*"),                               ("content", +0.10)),
    (("hit_by_aoe", "*hero*"),                          ("furious", +0.30)),
    (("hit_by_aoe", "*civilian*"),                      ("fearful", +0.50)),

    # Spell interrupt events (cast got broken)
    (("spell_interrupted", "*"),                       ("gruff",    +0.20)),
    (("spell_completed", "*hero*"),                    ("content",  +0.10)),

    # Skillchain / Magic Burst audible events
    # (per AUDIBLE_CALLOUTS.md). The party shouts; bystanders react;
    # bosses respond. Chain events propagate mood through the world
    # via sound, not just visuals.
    (("skillchain_called",            "*hero*"),       ("alert",    +0.20)),
    (("skillchain_closed",            "*hero*"),       ("content",  +0.20)),
    (("skillchain_closed_level_3",    "*hero*"),       ("content",  +0.40)),
    (("skillchain_closed_level_3",    "*soldier*"),    ("content",  +0.30)),
    (("magic_burst_landed",           "*hero*"),       ("content",  +0.30)),
    (("magic_burst_landed",           "*civilian*"),   ("content",  +0.10)),
    (("magic_burst_failed_element",   "*hero*"),       ("gruff",    +0.20)),
    (("magic_burst_ailment_amplified","*hero*"),       ("content",  +0.40)),
    (("party_chained_light",          "*hero*"),       ("content",  +0.50)),
    (("party_chained_darkness",       "*hero*"),       ("alert",    +0.30)),
    (("hit_by_skillchain",            "*civilian*"),   ("fearful",  +0.50)),
    (("hit_by_skillchain",            "*"          ),  ("alert",    +0.30)),

    # Audible-cue propagation: bystanders REACT to what they hear
    (("heard_panicked_call",          "*civilian*"),   ("fearful",  +0.30)),
    (("heard_panicked_call",          "*"),            ("fearful",  +0.20)),
    (("heard_skillchain_call_nearby", "*hero*"),       ("alert",    +0.15)),
    (("heard_skillchain_call_nearby", "*soldier*"),    ("alert",    +0.20)),
    (("heard_skillchain_call_nearby", "*"),            ("alert",    +0.10)),
    (("boss_cried_phase_transition",  "*civilian*"),   ("fearful",  +0.40)),
    (("boss_cried_ultimate_warning",  "*civilian*"),   ("fearful",  +0.60)),
    (("boss_cried_phase_transition",  "*soldier*"),    ("alert",    +0.50)),
    (("boss_cried_ultimate_warning",  "*soldier*"),    ("alert",    +0.70)),

    # Intervention Magic Burst events (per INTERVENTION_MB.md). The
    # save-the-wipe heroic moments. Cure/buff/debuff/song/helix/
    # luopan/enmity intervention all flow through these hooks.
    (("intervention_mb_succeeded",        "*hero*"),     ("content",   +0.50)),
    (("intervention_mb_succeeded_light",  "*hero*"),     ("content",   +0.70)),
    (("intervention_mb_failed",           "*hero*"),     ("furious",   +0.30)),
    (("intervention_mb_failed",           "*"),          ("gruff",     +0.20)),
    (("dual_cast_unlocked",               "*hero*"),     ("content",   +0.30)),
    (("dual_cast_active",                 "*hero*"),     ("alert",     +0.10)),

    # Bystanders + party members reacting to intervention saves
    (("party_member_saved_by_intervention", "*civilian*"), ("content",  +0.40)),
    (("party_member_saved_by_intervention", "*hero*"),     ("content",  +0.30)),
    (("party_member_saved_by_intervention", "*soldier*"),  ("content",  +0.30)),
    (("party_member_saved_by_intervention", "*"),          ("content",  +0.20)),

    # Player chains getting intervention-blocked by mob healers
    (("enemy_intervention_blocked_our_chain", "*hero*"),   ("furious",  +0.40)),

    # Mob healer that successfully intervenes on player chain
    (("mob_healer_intervened_on_player_chain","*"),        ("alert",    +0.20)),

    # Tank intervention enmity spike
    (("flash_burst_enmity_spike",         "*hero*"),     ("content",   +0.30)),
    (("provoke_burst_enmity_spike",       "*hero*"),     ("content",   +0.30)),

    # Equipment wear events (per EQUIPMENT_WEAR.md). Hero NPCs react
    # with anger when their gear breaks mid-fight (Maat losing wrist
    # guard at bloodied stage etc); civilians fear it; bystanders
    # admire successful master-tier repair work.
    (("equipment_broke",         "*hero*"),     ("furious",  +0.30)),
    (("equipment_broke",         "*soldier*"),  ("alert",    +0.30)),
    (("equipment_broke",         "*civilian*"), ("fearful",  +0.30)),
    (("equipment_broke",         "*"),          ("gruff",    +0.20)),
    (("equipment_repaired",      "*"),          ("content",  +0.20)),
    (("repair_npc_busy",         "*pellah*"),   ("content",  +0.10)),
    (("repair_npc_busy",         "*repair_npc*"),("content", +0.10)),
    (("master_repair_completed", "*hero*"),     ("content",  +0.40)),
    (("master_repair_completed", "*"),          ("content",  +0.30)),
    (("crit_repair_proc",        "*hero*"),     ("content",  +0.50)),
    (("crit_repair_proc",        "*"),          ("content",  +0.40)),
    (("died_with_full_durability_loss", "*"),   ("furious",  +0.50)),
    (("repair_completed_for_player",   "*pellah*"),     ("content", +0.20)),
    (("repair_completed_for_player",   "*repair_npc*"), ("content", +0.20)),
]


def lookup_delta(event_kind: str, role: str) -> t.Optional[tuple[str, float]]:
    """Return the first matching (mood_label, intensity_delta), or None."""
    for (k_pat, r_pat), result in EVENT_DELTAS:
        if k_pat != event_kind:
            continue
        if r_pat == "*" or fnmatch.fnmatchcase(role, r_pat):
            return result
    return None


# When an event's prescribed mood isn't in an agent's `mood_axes`, fall
# back to the agent's nearest declared mood per this proximity map.
MOOD_PROXIMITY: dict[str, list[str]] = {
    # negatives
    "furious":      ["gruff", "alert", "alarm", "weary"],
    "fearful":      ["alert", "weary", "melancholy"],
    "alarm":        ["alert", "fearful", "gruff"],
    "alert":        ["gruff", "alarm", "weary"],
    "gruff":        ["alert", "weary"],
    "weary":        ["melancholy", "gruff"],
    "melancholy":   ["weary", "contemplative"],
    "contemplative":["weary", "melancholy"],
    "drunk":        ["mischievous", "content"],
    # positives
    "content":      ["mischievous", "contemplative"],
    "mischievous":  ["content"],
}


def nearest_in_axes(target_mood: str, mood_axes: list[str]) -> t.Optional[str]:
    """Return the closest mood in `mood_axes` to `target_mood`."""
    if target_mood in mood_axes:
        return target_mood
    for candidate in MOOD_PROXIMITY.get(target_mood, []):
        if candidate in mood_axes:
            return candidate
    # No proximity match — give up rather than pick wrongly
    return None
