from app.core.domain.events import NotificationEvent
from app.core.ports.services.notification import NotificationPort


class InMemoryNotificationQueue(NotificationPort):
    """In-memory implementation of NotificationPort.

    Used in development and tests.  Holds notification events in a plain
    list so tests can inspect them without a real email/messaging service.

    Not thread-safe.  Not persistent.
    """

    def __init__(self) -> None:
        self._events: list[NotificationEvent] = []

    def push(self, event: NotificationEvent) -> None:
        self._events.append(event)

    def get_all(self) -> list[NotificationEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
