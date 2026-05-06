"""Tests for subtle_dialogue_inserts."""
from __future__ import annotations

from server.lore_hint_registry import (
    HintLocation, LoreHint, LoreHintRegistry,
)
from server.hint_attentiveness_tracker import (
    HintAttentivenessTracker,
)
from server.puzzle_assembly_journal import PuzzleAssemblyJournal
from server.subtle_dialogue_inserts import (
    AMBIENT_COOLDOWN_SECONDS,
    SubtleDialogueInserts,
)


def _setup_full(
    extra_hints: list[LoreHint] | None = None,
):
    reg = LoreHintRegistry()
    att = HintAttentivenessTracker()
    journal = PuzzleAssemblyJournal()
    journal.define_piece(piece_id="p_alpha", label="alpha")
    inserts = SubtleDialogueInserts(
        hint_registry=reg, attentiveness=att, journal=journal,
    )
    if extra_hints:
        for h in extra_hints:
            reg.register(h)
    return reg, att, journal, inserts


def _enlightened(att: HintAttentivenessTracker, player_id="alice"):
    for ch in range(1, 31):
        att.award_msq_chapter(player_id=player_id, chapter=ch)
    for q in range(20):
        att.award_side_quest(player_id=player_id, quest_id=f"sq{q}")


def test_zone_enter_fires_poster():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_p", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER,
            zone_id="bar", text="Marauder first.",
            subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert len(out) == 1
    assert out[0].hint_id == "h_p"


def test_zone_enter_blocks_oblivious():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_p", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER,
            zone_id="bar", text="Marauder first.",
            subtlety=8,
        ),
    ])
    out = inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert out == ()


def test_npc_interact_fires_dialogue():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_npc", puzzle_piece_id="p_alpha",
            location=HintLocation.NPC_DIALOGUE,
            zone_id="bastok", text="My grandfather said...",
            npc_id="old_fisherman", subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_npc_interact(
        player_id="alice", npc_id="old_fisherman", zone_id="bastok",
    )
    assert len(out) == 1


def test_npc_interact_wrong_npc():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_npc", puzzle_piece_id="p_alpha",
            location=HintLocation.NPC_DIALOGUE,
            zone_id="bastok", text="...",
            npc_id="old_fisherman", subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_npc_interact(
        player_id="alice", npc_id="other_npc", zone_id="bastok",
    )
    assert out == ()


def test_cutscene_fires_background():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_cs", puzzle_piece_id="p_alpha",
            location=HintLocation.CUTSCENE_BACKGROUND,
            zone_id="lower_jeuno",
            text="kill both pets fast or one will rage",
            cutscene_id="cs_jeuno_council_03", subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_cutscene_play(
        player_id="alice", cutscene_id="cs_jeuno_council_03",
        zone_id="lower_jeuno",
    )
    assert len(out) == 1


def test_ambient_bark_fires_then_cools_down():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_amb", puzzle_piece_id="p_alpha",
            location=HintLocation.AMBIENT_BARK,
            zone_id="docks", text="The Marauder. Always.",
            npc_id="dock_drunk", subtlety=4,
        ),
    ])
    _enlightened(att)
    first = inserts.on_ambient_tick(
        player_id="alice", zone_id="docks", now_seconds=10,
    )
    assert len(first) == 1
    # too soon — cooldown blocks
    second = inserts.on_ambient_tick(
        player_id="alice", zone_id="docks", now_seconds=20,
    )
    assert second == ()
    # past cooldown — fires again (but already-seen hint still goes
    # through the journal, journal will silently dedup)
    third = inserts.on_ambient_tick(
        player_id="alice", zone_id="docks",
        now_seconds=10 + AMBIENT_COOLDOWN_SECONDS + 1,
    )
    assert len(third) == 1


def test_item_inspect_fires_item_description():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_item", puzzle_piece_id="p_alpha",
            location=HintLocation.ITEM_DESCRIPTION,
            zone_id="anywhere",
            text="(carved on the hilt) ...the Captain falls...",
            item_id="rusted_sahagin_dagger", subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_item_inspect(
        player_id="alice",
        item_id="rusted_sahagin_dagger", zone_id="bastok",
    )
    assert len(out) == 1


def test_journal_records_observed_hint():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_p", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER,
            zone_id="bar", text="Marauder first.",
            subtlety=4,
        ),
    ])
    _enlightened(att)
    inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert journal.piece_confirmed(
        player_id="alice", piece_id="p_alpha",
    ) is True


def test_msq_gate_blocks_even_attentive():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_p", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER,
            zone_id="bar", text="Marauder first.",
            required_msq_chapter=10, subtlety=4,
        ),
    ])
    # attentive but only ch 1
    att.award_msq_chapter(player_id="alice", chapter=1)
    for q in range(20):
        att.award_side_quest(player_id="alice", quest_id=f"sq{q}")
    for ch in range(2, 11):
        # boost score but don't satisfy MSQ chapter floor unless...
        # actually, awarding chapter 10 satisfies; so test the gate
        # by NOT awarding chapter 10
        pass
    out = inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert out == ()


def test_unmapped_hint_uses_hint_puzzle_piece():
    """If no explicit hint→piece mapping, the hint's own
    puzzle_piece_id is used."""
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h_p", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER,
            zone_id="bar", text="...", subtlety=4,
        ),
    ])
    _enlightened(att)
    out = inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert out[0].puzzle_piece_id == "p_alpha"


def test_register_mapping():
    reg, att, journal, inserts = _setup_full()
    assert inserts.register_mapping(
        hint_id="h1", piece_id="p1",
    ) is True
    assert inserts.register_mapping(
        hint_id="h1", piece_id="p2",
    ) is False  # dup hint
    assert inserts.register_mapping(
        hint_id="", piece_id="p1",
    ) is False


def test_zone_with_no_hints_returns_empty():
    reg, att, journal, inserts = _setup_full()
    _enlightened(att)
    assert inserts.on_zone_enter(
        player_id="alice", zone_id="empty_zone",
    ) == ()


def test_multiple_zone_hints_all_emitted():
    reg, att, journal, inserts = _setup_full([
        LoreHint(
            hint_id="h1", puzzle_piece_id="p_alpha",
            location=HintLocation.POSTER, zone_id="bar",
            text="t1", subtlety=2,
        ),
        LoreHint(
            hint_id="h2", puzzle_piece_id="p_alpha",
            location=HintLocation.SCRIBBLED_NOTE, zone_id="bar",
            text="t2", subtlety=2,
        ),
        LoreHint(
            hint_id="h3", puzzle_piece_id="p_alpha",
            location=HintLocation.JOURNAL_ENTRY, zone_id="bar",
            text="t3", subtlety=2,
        ),
    ])
    _enlightened(att)
    out = inserts.on_zone_enter(player_id="alice", zone_id="bar")
    assert len(out) == 3
