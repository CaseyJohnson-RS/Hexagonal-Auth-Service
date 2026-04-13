from datetime import datetime
from pydantic import BaseModel, Field
from app.core.utils.time import utc_now


class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)


class DomainEvent(BaseEvent):
    pass
