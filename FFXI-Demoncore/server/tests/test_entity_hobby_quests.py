"""Tests for entity_hobby_quests."""
from __future__ import annotations

from server.entity_hobby_quests import (
    EntityHobbyQuestsSystem, QuestState,
)
from server.entity_hobbies import HobbyKind


def _post(
    s: EntityHobbyQuestsSystem,
    is_rare: bool = False,
    secret: str = "",
) -> str:
    return s.post_need(
        npc_id="volker", hobby=HobbyKind.FISHING,
        requested_item="lucky_lure", posted_day=10,
        deadline_day=20, is_rare=is_rare,
        secret_on_delivery=secret,
    )


def test_post_happy():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    assert qid is not None


def test_post_empty_npc_blocked():
    s = EntityHobbyQuestsSystem()
    assert s.post_need(
        npc_id="", hobby=HobbyKind.FISHING,
        requested_item="x", posted_day=10,
        deadline_day=20,
    ) is None


def test_post_empty_item_blocked():
    s = EntityHobbyQuestsSystem()
    assert s.post_need(
        npc_id="volker", hobby=HobbyKind.FISHING,
        requested_item="", posted_day=10,
        deadline_day=20,
    ) is None


def test_post_deadline_before_post_blocked():
    s = EntityHobbyQuestsSystem()
    assert s.post_need(
        npc_id="volker", hobby=HobbyKind.FISHING,
        requested_item="x", posted_day=20,
        deadline_day=10,
    ) is None


def test_accept_happy():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    assert s.accept(
        quest_id=qid, player_id="naji",
    ) is True


def test_accept_self_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    # NPC can't accept their own quest
    assert s.accept(
        quest_id=qid, player_id="volker",
    ) is False


def test_accept_double_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    s.accept(quest_id=qid, player_id="naji")
    assert s.accept(
        quest_id=qid, player_id="bob",
    ) is False


def test_deliver_happy():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    s.accept(quest_id=qid, player_id="naji")
    gain = s.deliver(
        quest_id=qid, player_id="naji",
        current_day=15,
    )
    assert gain == 10


def test_deliver_rare_bonus():
    s = EntityHobbyQuestsSystem()
    qid = _post(s, is_rare=True)
    s.accept(quest_id=qid, player_id="naji")
    gain = s.deliver(
        quest_id=qid, player_id="naji",
        current_day=15,
    )
    # 10 base + 25 rare bonus = 35
    assert gain == 35


def test_deliver_wrong_player_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    s.accept(quest_id=qid, player_id="naji")
    assert s.deliver(
        quest_id=qid, player_id="bob",
        current_day=15,
    ) is None


def test_deliver_after_deadline_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    s.accept(quest_id=qid, player_id="naji")
    assert s.deliver(
        quest_id=qid, player_id="naji",
        current_day=25,
    ) is None


def test_deliver_before_accept_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    assert s.deliver(
        quest_id=qid, player_id="naji",
        current_day=15,
    ) is None


def test_auto_expire_after_deadline():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    assert s.auto_expire(
        quest_id=qid, current_day=25,
    ) is True
    assert s.quest(
        quest_id=qid,
    ).state == QuestState.EXPIRED


def test_auto_expire_before_deadline_blocked():
    s = EntityHobbyQuestsSystem()
    qid = _post(s)
    assert s.auto_expire(
        quest_id=qid, current_day=15,
    ) is False


def test_secret_unlocks_on_delivery():
    s = EntityHobbyQuestsSystem()
    qid = _post(s, secret="secret_fishing_spot_at_dawn")
    s.accept(quest_id=qid, player_id="naji")
    s.deliver(
        quest_id=qid, player_id="naji",
        current_day=15,
    )
    secret = s.secret_for(
        quest_id=qid, player_id="naji",
    )
    assert secret == "secret_fishing_spot_at_dawn"


def test_secret_only_for_deliverer():
    s = EntityHobbyQuestsSystem()
    qid = _post(s, secret="secret_X")
    s.accept(quest_id=qid, player_id="naji")
    s.deliver(
        quest_id=qid, player_id="naji",
        current_day=15,
    )
    # Bob can't read the secret
    assert s.secret_for(
        quest_id=qid, player_id="bob",
    ) is None


def test_secret_undelivered_none():
    s = EntityHobbyQuestsSystem()
    qid = _post(s, secret="x")
    s.accept(quest_id=qid, player_id="naji")
    assert s.secret_for(
        quest_id=qid, player_id="naji",
    ) is None


def test_open_needs_for_npc():
    s = EntityHobbyQuestsSystem()
    q1 = _post(s)
    q2 = _post(s)
    s.accept(quest_id=q1, player_id="naji")
    needs = s.open_needs_for(npc_id="volker")
    assert len(needs) == 1
    assert needs[0].quest_id == q2


def test_player_history():
    s = EntityHobbyQuestsSystem()
    q1 = _post(s)
    q2 = _post(s)
    s.accept(quest_id=q1, player_id="naji")
    s.accept(quest_id=q2, player_id="naji")
    hist = s.player_history(player_id="naji")
    assert len(hist) == 2


def test_unknown_quest():
    s = EntityHobbyQuestsSystem()
    assert s.quest(quest_id="ghost") is None


def test_enum_count():
    assert len(list(QuestState)) == 4
