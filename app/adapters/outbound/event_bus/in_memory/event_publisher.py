import logging
from typing import List

from app.core.domain.events import BaseEvent
from app.core.ports.services.event_queue import EventQueuePort
from app.core.ports.services.event_publisher import EventPublisherPort


logger = logging.getLogger(__name__)


class EventPublisher(EventPublisherPort):
    """
    Publishes domain/application events to an event queue.

    Acts as an infrastructure adapter.
    """

    def __init__(self, queue: EventQueuePort):
        self.queue = queue

    async def publish(self, events: List[BaseEvent]) -> None:
        """
        Publish a list of domain events to the event queue.

        Args:
            events (List[BaseEvent]): Domain events to publish.
        """
        if not events:
            logger.debug("No events to publish.")
            return

        logger.info("Publishing %d events.", len(events))
        for event in events:
            logger.debug("Publishing event: %s", event)

        self.queue.extend(events)
        logger.info("Events successfully added to the queue.")
