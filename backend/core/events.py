import json
import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from core.config import get_settings

logger = logging.getLogger(__name__)

# Event channel names
CHANNEL_MOD_ADDED = "mod_added"
CHANNEL_MOD_REMOVED = "mod_removed"
CHANNEL_MOD_UPDATED = "mod_updated"
CHANNEL_VOTE_CREATED = "vote_created"
CHANNEL_VOTE_CAST = "vote_cast"
CHANNEL_VOTE_RESOLVED = "vote_resolved"
CHANNEL_UPLOAD_PENDING = "upload_pending"
CHANNEL_UPLOAD_RESOLVED = "upload_resolved"
CHANNEL_SERVER_STATUS = "server_status"
CHANNEL_SERVER_UPDATE = "server_update"

PREFIX = "mineshare:"


class EventBus:
    def __init__(self):
        settings = get_settings()
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def publish(self, channel: str, data: dict) -> None:
        try:
            await self._redis.publish(f"{PREFIX}{channel}", json.dumps(data))
        except Exception:
            logger.exception("Failed to publish event to %s", channel)

    async def subscribe(self, *channels: str) -> AsyncGenerator[dict, None]:
        pubsub = self._redis.pubsub()
        prefixed = [f"{PREFIX}{ch}" for ch in channels]
        await pubsub.subscribe(*prefixed)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {
                        "channel": message["channel"].removeprefix(PREFIX),
                        "data": json.loads(message["data"]),
                    }
        finally:
            await pubsub.unsubscribe(*prefixed)
            await pubsub.aclose()

    async def close(self) -> None:
        await self._redis.aclose()


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
