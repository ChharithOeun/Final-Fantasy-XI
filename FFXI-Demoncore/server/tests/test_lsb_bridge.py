"""Tests for the LSB bridge.

Run:  python -m pytest server/tests/test_lsb_bridge.py -v
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator import AgentOrchestrator
from agent_orchestrator.orchestrator import OrchestratorConfig
from lsb_bridge.bridge import (
    BridgeHandler,
    BridgePublisher,
    _check_token,
    create_bridge_app,
)


# ---------------------------------------------------------------------------
# Token check
# ---------------------------------------------------------------------------

def test_check_token_valid():
    assert _check_token("secret", "secret") is True


def test_check_token_mismatch():
    assert _check_token("wrong", "secret") is False


def test_check_token_empty():
    assert _check_token("", "secret") is False
    assert _check_token(None, "secret") is False


# ---------------------------------------------------------------------------
# BridgePublisher
# ---------------------------------------------------------------------------

class FakeRedis:
    """Mock redis client that records publish() calls."""
    def __init__(self):
        self.published: list[tuple[str, str]] = []

    def publish(self, topic, msg):
        self.published.append((topic, msg))
        return 1


def test_publish_agent_move():
    redis = FakeRedis()
    pub = BridgePublisher(redis)
    pub.publish_agent_move("vendor_zaldon", "stall_position", "vendor_idle")
    assert len(redis.published) == 1
    topic, msg = redis.published[0]
    assert topic == "demoncore:agent:vendor_zaldon:move"
    parsed = json.loads(msg)
    assert parsed["agent_id"] == "vendor_zaldon"
    assert parsed["location"] == "stall_position"


def test_publish_bark_pool_changed():
    redis = FakeRedis()
    pub = BridgePublisher(redis)
    pub.publish_bark_pool_changed("hero_cid", "alert")
    topic, msg = redis.published[0]
    assert "bark_pool_changed" in topic
    assert json.loads(msg)["new_mood"] == "alert"


def test_publish_zone_env_event():
    redis = FakeRedis()
    pub = BridgePublisher(redis)
    pub.publish_zone_env_event("bastok_markets", "rain_started")
    topic, msg = redis.published[0]
    assert topic == "demoncore:zone:bastok_markets:env_event"


def test_publish_critic_hint():
    redis = FakeRedis()
    pub = BridgePublisher(redis)
    pub.publish_critic_hint("hero_maat", {"strategy": "silence_blm"})
    topic, msg = redis.published[0]
    assert "critic_hints" in topic
    parsed = json.loads(msg)
    assert parsed["hint"]["strategy"] == "silence_blm"


def test_publisher_handles_redis_failure():
    """If redis.publish() raises, the publisher logs but doesn't crash."""
    class BrokenRedis:
        def publish(self, topic, msg):
            raise ConnectionError("redis down")
    pub = BridgePublisher(BrokenRedis())
    result = pub.publish_agent_move("x", "loc", "anim")
    assert result == 0  # publish failed gracefully


# ---------------------------------------------------------------------------
# BridgeHandler — integration with the real orchestrator
# ---------------------------------------------------------------------------

@pytest.fixture
def orch(tmp_path):
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "agents",
        here.parent / "agents",
    ]
    agents_dir = next((p for p in candidates if p.is_dir()), None)
    if agents_dir is None:
        pytest.skip(f"no agents dir found")
    cfg = OrchestratorConfig(
        agents_dir=str(agents_dir),
        db_path=str(tmp_path / "test.sqlite"),
    )
    o = AgentOrchestrator(cfg)
    o.load_all()
    yield o
    o.db.close()


def test_handler_rejects_bad_token(orch):
    handler = BridgeHandler(orch, token="secret")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "wrong"},
        body={"agent_id": "vendor_zaldon", "event_kind": "aoe_near"},
    )
    assert status == 401
    assert body["ok"] is False


def test_handler_missing_fields(orch):
    handler = BridgeHandler(orch, token="secret")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "secret"},
        body={},
    )
    assert status == 400


def test_handler_processes_aoe_event(orch):
    handler = BridgeHandler(orch, token="secret")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "secret"},
        body={
            "agent_id": "vendor_zaldon",
            "event_kind": "aoe_near",
        },
    )
    assert status == 200
    assert body["ok"] is True
    assert body["mood_changed"] is True
    assert body["new_mood"] == "gruff"


def test_handler_publishes_bark_pool_changed_on_mood_change(orch):
    """When the handler flips a mood, it should publish to Redis."""
    redis = FakeRedis()
    pub = BridgePublisher(redis)
    handler = BridgeHandler(orch, token="secret", publisher=pub)
    handler.handle(
        headers={"X-Demoncore-Bridge-Token": "secret"},
        body={"agent_id": "vendor_zaldon", "event_kind": "aoe_near"},
    )
    # bark_pool_changed should have been published
    topics = [t for (t, _) in redis.published]
    assert any("bark_pool_changed" in t for t in topics)


def test_handler_unknown_agent(orch):
    handler = BridgeHandler(orch, token="secret")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "secret"},
        body={"agent_id": "ghost_agent", "event_kind": "aoe_near"},
    )
    assert status == 400


def test_handler_payload_passed_through(orch):
    handler = BridgeHandler(orch, token="secret")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "secret"},
        body={
            "agent_id": "vendor_zaldon",
            "event_kind": "outlaw_walked_past",
            "payload": {"distance_m": 3, "outlaw_id": "alice"},
        },
    )
    assert status == 200


# ---------------------------------------------------------------------------
# create_bridge_app fallback (no FastAPI in test env)
# ---------------------------------------------------------------------------

def test_create_bridge_app_returns_handler_without_fastapi(orch):
    """If FastAPI isn't installed, falls back to bare BridgeHandler."""
    # Force the import error path by stashing fastapi if present
    import sys
    saved = sys.modules.pop("fastapi", None)
    sys.modules["fastapi"] = None  # makes the import fail
    try:
        result = create_bridge_app(orch, token="secret")
        # When fastapi import fails, returns the bare handler
        assert isinstance(result, BridgeHandler)
    finally:
        if saved is not None:
            sys.modules["fastapi"] = saved
        else:
            sys.modules.pop("fastapi", None)
