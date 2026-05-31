from typing import Protocol

from app.core.domain.events import NotificationEvent


class NotificationPort(Protocol):
    """Port for outbound notification delivery.

    Implementations receive NotificationEvent objects (which carry sensitive
    OTT token strings) and are responsible for dispatching them — e.g. by
    queuing an email, writing to an outbox, or holding them in memory for
    tests.  Events that pass through this port are never written to the
    persistent audit log.
    """

    def push(self, event: NotificationEvent) -> None:
        """Enqueue a single notification event for delivery."""
        ...

    def get_all(self) -> list[NotificationEvent]:
        """Return all pending notification events (used by consumers / tests)."""
        ...

    def clear(self) -> None:
        """Discard all pending events (used between tests)."""
        ...
