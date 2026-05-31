from typing import List

from app.core.domain.events import BaseEvent
from app.core.ports.services.event_queue import EventQueuePort


class InMemoryEventQueue(EventQueuePort):
    """In-memory append-only event queue for development and tests.

    Semantics
    ---------
    - push appends events to the end of the list
    - get returns a slice without removing events (read-only)

    Not thread-safe.  Not persistent.
    """

    def __init__(self) -> None:
        self._events: List[BaseEvent] = []

    async def push(self, event: BaseEvent) -> None:
        self._events.append(event)

    async def get(
        self, offset: int, limit: int, desc: bool = False
    ) -> list[BaseEvent]:
        if offset < 0 or limit <= 0:
            return []

        if desc:
            return self._events[::-1][offset: offset + limit]
        return self._events[offset: offset + limit]
