import logging
from typing import List

from app.core.domain.events import BaseEvent, NotificationEvent
from app.core.ports.services.event_queue import EventQueuePort
from app.core.ports.services.event_publisher import EventPublisherPort
from app.core.ports.services.notification import NotificationPort


logger = logging.getLogger(__name__)


class EventPublisher(EventPublisherPort):
    """Routes domain events to the correct outbound port.

    - NotificationEvent  → NotificationPort  (tokens, never persisted)
    - everything else    → EventQueuePort    (persistent audit log)
    """

    def __init__(self, queue: EventQueuePort, notifications: NotificationPort) -> None:
        self._queue = queue
        self._notifications = notifications

    async def publish(self, events: List[BaseEvent]) -> None:
        if not events:
            logger.debug("No events to publish.")
            return

        logger.info("Publishing %d events.", len(events))

        for event in events:
            if isinstance(event, NotificationEvent):
                logger.debug("Notification event: %s", type(event).__name__)
                self._notifications.push(event)
            else:
                logger.debug("Audit event: %s", type(event).__name__)
                await self._queue.push(event)

        logger.info("All events dispatched.")
