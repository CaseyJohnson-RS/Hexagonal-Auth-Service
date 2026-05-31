"""JSON serialization for DomainEvent objects stored in Redis.

Only DomainEvent (audit) subclasses are serialized.
NotificationEvent subclasses carry sensitive token data and are never
written to any persistent store, so they are intentionally excluded.

Format
------
Each event is a JSON object with a ``__type__`` discriminator field that
holds the class name.  All other fields come from Pydantic's model_dump.

Example
-------
    {
        "__type__": "UserCreated",
        "user_id": "...",
        "email": "user@example.com",
        "timestamp": "2026-01-01T00:00:00Z"
    }
"""

import json
from typing import Type

from app.core.domain.events import DomainEvent


def _build_registry() -> dict[str, Type[DomainEvent]]:
    from app.core.domain.events.user import (
        UserCreated,
        UserActivated,
        UserDeactivated,
        UserEmailVerified,
        UserPasswordChanged,
        UserPasswordRecovered,
    )
    from app.core.domain.events.token import (
        RefreshTokenCreated,
        RefreshTokenRevoked,
    )

    classes: list[Type[DomainEvent]] = [
        UserCreated,
        UserActivated,
        UserDeactivated,
        UserEmailVerified,
        UserPasswordChanged,
        UserPasswordRecovered,
        RefreshTokenCreated,
        RefreshTokenRevoked,
    ]
    return {cls.__name__: cls for cls in classes}


_REGISTRY: dict[str, Type[DomainEvent]] = _build_registry()


def serialize(event: DomainEvent) -> str:
    """Serialize a DomainEvent to a JSON string."""
    data = event.model_dump(mode="json")
    data["__type__"] = type(event).__name__
    return json.dumps(data)


def deserialize(raw: str) -> DomainEvent:
    """Deserialize a JSON string back to the correct DomainEvent subclass.

    Raises:
        KeyError: if ``__type__`` is missing or unknown.
        ValidationError: if the payload does not match the event schema.
    """
    data = json.loads(raw)
    type_name = data.pop("__type__")
    cls = _REGISTRY[type_name]
    return cls.model_validate(data)
