from typing import Protocol

from app.core.domain.events import BaseEvent


class EventQueuePort(Protocol):
    async def push(self, event: BaseEvent) -> None: ...

    async def get(
        self, offset: int, limit: int, desc: bool = False
    ) -> list[BaseEvent]: ...
