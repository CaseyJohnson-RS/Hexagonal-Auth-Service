from typing import List, Protocol
from app.core.domain.events import BaseEvent


class EventPublisherPort(Protocol):
    async def publish(self, events: List[BaseEvent]):
        pass
