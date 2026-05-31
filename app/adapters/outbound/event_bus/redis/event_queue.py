import logging

import redis.asyncio as aioredis

from app.core.domain.events import BaseEvent, DomainEvent
from app.core.domain.events.serializer import deserialize, serialize
from app.core.ports.services.event_queue import EventQueuePort


logger = logging.getLogger(__name__)

_DEFAULT_KEY = "auth:events"


class RedisEventQueue(EventQueuePort):
    """Persistent event queue backed by a Redis list.

    Each DomainEvent is serialized to JSON and appended via RPUSH
    (newest at tail).  Reads use LRANGE so the list is never mutated.

    Redis key
    ---------
    ``auth:events`` — one JSON string per DomainEvent.

    Concurrency
    -----------
    The redis-py asyncio client uses a connection pool and is safe for
    concurrent coroutines.
    """

    def __init__(
        self,
        client: aioredis.Redis,
        key: str = _DEFAULT_KEY,
    ) -> None:
        self._client = client
        self._key = key

    async def push(self, event: BaseEvent) -> None:
        if not isinstance(event, DomainEvent):
            logger.warning(
                "RedisEventQueue received a non-DomainEvent (%s); skipping.",
                type(event).__name__,
            )
            return
        raw = serialize(event)
        await self._client.rpush(self._key, raw)
        logger.debug("Stored %s in Redis.", type(event).__name__)

    async def get(
        self, offset: int, limit: int, desc: bool = False
    ) -> list[BaseEvent]:
        if offset < 0 or limit <= 0:
            return []

        total: int = await self._client.llen(self._key)
        if total == 0 or offset >= total:
            return []

        if desc:
            # Newest-first: work backwards from the tail.
            start = total - 1 - offset
            stop = max(start - limit + 1, 0)
            raw_items: list[str] = await self._client.lrange(self._key, stop, start)
            raw_items = list(reversed(raw_items))
        else:
            start = offset
            stop = offset + limit - 1
            raw_items = await self._client.lrange(self._key, start, stop)

        events: list[BaseEvent] = []
        for raw in raw_items:
            try:
                events.append(deserialize(raw))
            except Exception:
                logger.exception("Failed to deserialize event: %s", raw)

        return events
