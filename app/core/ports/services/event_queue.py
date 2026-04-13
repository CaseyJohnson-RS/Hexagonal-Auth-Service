from typing import Iterable, Protocol
from app.core.domain.events import BaseEvent


class EventQueuePort(Protocol):
    def push(self, event: BaseEvent) -> None:
        pass

    def extend(self, events: Iterable[BaseEvent]) -> None:
        pass

    def get(self, offset: int, limit: int, desc: bool) -> list[BaseEvent]:
        pass
