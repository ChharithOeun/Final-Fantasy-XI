"""LSB ↔ orchestrator bridge.

HTTP webhook endpoint + Redis pub/sub publisher. Lets the running
LandSandBoat FFXI server feed in-game events into the orchestrator
mood/memory pipeline.

Public surface:
    create_bridge_app(orchestrator, token) -> FastAPI app
    BridgePublisher(redis_client) -> outbound message helper
"""
from .bridge import BridgePublisher, create_bridge_app

__all__ = ["BridgePublisher", "create_bridge_app"]
