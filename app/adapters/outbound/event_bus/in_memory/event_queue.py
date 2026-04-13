from typing import Iterable, List
from app.core.domain.events import BaseEvent
from app.core.ports.services.event_queue import EventQueuePort


class InMemoryEventQueue(EventQueuePort):
    """
    In-memory append-only event queue.

    Semantics:
    - push / extend append events to the end
    - get(offset, limit) returns a slice without removing events

    Redis-like behavior:
    - offset == 0 → from beginning
    - offset >= len → empty list

    Not thread-safe.
    Not persistent.
    """

    def __init__(self) -> None:
        self._events: List[BaseEvent] = []

    def push(self, event: BaseEvent) -> None:
        """Append single event to the queue."""
        self._events.append(event)

    def extend(self, events: Iterable[BaseEvent]) -> None:
        """Append multiple events to the queue preserving order."""
        self._events.extend(events)

    def get(self, offset: int, limit: int, desc: bool = False) -> list[BaseEvent]:
        """
        Read events starting from offset.

        Does NOT mutate the queue.
        """
        if offset < 0 or limit <= 0:
            return []

        print()

        if desc:
            return self._events[::-1][offset : offset + limit]
        else:
            return self._events[offset : offset + limit]
