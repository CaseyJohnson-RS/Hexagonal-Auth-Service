from datetime import datetime
from pydantic import BaseModel, Field
from app.core.utils.time import utc_now


class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)


class DomainEvent(BaseEvent):
    """Audit-safe event — stored in the persistent event log."""
    pass


class NotificationEvent(BaseEvent):
    """Carries sensitive token data (OTT strings).

    Routed to NotificationPort only — never written to the audit log
    or any persistent store.
    """
    pass
