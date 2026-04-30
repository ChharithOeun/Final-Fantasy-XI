"""LSB → orchestrator HTTP bridge + outbound Redis publisher.

The HTTP side uses FastAPI but degrades gracefully if FastAPI isn't
installed (returns a small WSGI-ish handler instead, sufficient for
embedding in chharbot's existing HTTP server). The Redis side uses
the standard redis-py client.

Tested without FastAPI / Redis present via dependency injection of
mock objects — see tests/test_lsb_bridge.py.
"""
from __future__ import annotations

import hmac
import json
import logging
import time
import typing as t


log = logging.getLogger("demoncore.lsb_bridge")


# ---------------------------------------------------------------------------
# Outbound publisher
# ---------------------------------------------------------------------------

class BridgePublisher:
    """Pushes orchestrator state changes to LSB via Redis pub/sub.

    The redis_client must implement `.publish(topic, message)`. Real
    redis-py clients work; tests inject a mock that records calls.
    """

    def __init__(self, redis_client: t.Any):
        self.redis = redis_client

    def publish_agent_move(self, agent_id: str, location: str,
                           animation: str) -> int:
        """Notify LSB that an agent should move + change idle anim."""
        topic = f"demoncore:agent:{agent_id}:move"
        msg = json.dumps({
            "agent_id": agent_id,
            "location": location,
            "animation": animation,
            "ts": time.time(),
        })
        return self._publish(topic, msg)

    def publish_bark_pool_changed(self, agent_id: str, new_mood: str) -> int:
        """Tell LSB to invalidate the agent's cached bark."""
        topic = f"demoncore:agent:{agent_id}:bark_pool_changed"
        msg = json.dumps({
            "agent_id": agent_id,
            "new_mood": new_mood,
            "ts": time.time(),
        })
        return self._publish(topic, msg)

    def publish_zone_env_event(self, zone: str, event_kind: str,
                                payload: t.Optional[dict] = None) -> int:
        """Broadcast a zone-wide environmental event."""
        topic = f"demoncore:zone:{zone}:env_event"
        msg = json.dumps({
            "zone": zone,
            "event_kind": event_kind,
            "payload": payload or {},
            "ts": time.time(),
        })
        return self._publish(topic, msg)

    def publish_critic_hint(self, agent_id: str, hint: dict) -> int:
        """Send Tier-3 critic LLM strategy hints back to LSB."""
        topic = f"demoncore:agent:{agent_id}:critic_hints"
        msg = json.dumps({
            "agent_id": agent_id,
            "hint": hint,
            "ts": time.time(),
        })
        return self._publish(topic, msg)

    def _publish(self, topic: str, msg: str) -> int:
        try:
            self.redis.publish(topic, msg)
            return 1
        except Exception as e:
            log.warning("redis publish failed for %s: %s", topic, e)
            return 0


# ---------------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------------

def _check_token(provided: t.Optional[str], expected: str) -> bool:
    """Constant-time token comparison."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


class BridgeHandler:
    """Pure-Python event handler, decoupled from any web framework.

    Routes LSB events into the orchestrator's apply_event +
    push_event pipeline, returns the resulting state change.
    """

    def __init__(self, orchestrator: t.Any, token: str,
                 publisher: t.Optional[BridgePublisher] = None):
        self.orchestrator = orchestrator
        self.token = token
        self.publisher = publisher

    def handle(self, *, headers: dict, body: dict) -> tuple[int, dict]:
        """Process one incoming LSB event. Returns (status_code, body)."""
        provided_token = headers.get("X-Demoncore-Bridge-Token") \
                         or headers.get("x-demoncore-bridge-token")
        if not _check_token(provided_token, self.token):
            return 401, {"ok": False, "error": "invalid or missing token"}

        agent_id = body.get("agent_id")
        event_kind = body.get("event_kind")
        if not agent_id or not event_kind:
            return 400, {"ok": False, "error": "agent_id and event_kind required"}

        payload = body.get("payload")
        ts = body.get("timestamp")

        # Route through the orchestrator
        try:
            from agent_orchestrator.mcp_tools import tool_push_event
            result = tool_push_event(
                self.orchestrator, agent_id, event_kind,
                json.dumps(payload) if payload else None,
            )
            if not result.get("ok"):
                return 400, result

            # Populate new_mood whenever the mood actually changed, so
            # callers can read it without needing a publisher.
            if result.get("mood_changed"):
                state = self.orchestrator.db.get_tier2_state(agent_id)
                if state is not None:
                    result["new_mood"] = state.mood
                    if self.publisher is not None:
                        self.publisher.publish_bark_pool_changed(
                            agent_id, state.mood
                        )

            return 200, result
        except Exception as e:
            log.exception("handler error for %s/%s: %s",
                          agent_id, event_kind, e)
            return 500, {"ok": False, "error": str(e)}


def create_bridge_app(orchestrator: t.Any, token: str,
                       publisher: t.Optional[BridgePublisher] = None) -> t.Any:
    """Build a FastAPI app exposing the bridge endpoint.

    Falls back to returning the BridgeHandler directly if FastAPI isn't
    installed; the caller can wire it into their preferred HTTP server
    (e.g. Starlette, aiohttp).
    """
    try:
        from fastapi import FastAPI, Header, Request, HTTPException
    except ImportError:
        log.info("FastAPI not installed; returning bare handler")
        return BridgeHandler(orchestrator, token, publisher)

    handler = BridgeHandler(orchestrator, token, publisher)
    app = FastAPI(title="Demoncore LSB Bridge", version="1.0")

    @app.post("/lsb/event")
    async def event_endpoint(
        request: Request,
        x_demoncore_bridge_token: t.Optional[str] = Header(default=None),
    ):
        body = await request.json()
        status, response = handler.handle(
            headers={"X-Demoncore-Bridge-Token": x_demoncore_bridge_token},
            body=body,
        )
        if status >= 400:
            raise HTTPException(status_code=status, detail=response)
        return response

    @app.get("/lsb/healthz")
    async def healthz():
        return {"ok": True, "ts": time.time()}

    @app.get("/lsb/agents")
    async def list_agents(
        x_demoncore_bridge_token: t.Optional[str] = Header(default=None),
    ):
        if not _check_token(x_demoncore_bridge_token, token):
            raise HTTPException(status_code=401, detail="invalid token")
        rows = orchestrator.list_agents()
        return {"ok": True, "count": len(rows), "agents": rows}

    return app
