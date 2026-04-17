from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.ports.services import EventQueuePort
from app.adapters.nexus import get_event_queue


router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(directory="app/adapters/inbound/http/templates")


def get_event_timestamp(event) -> str:
    """Extract timestamp from an event"""
    for attr in ['timestamp', 'created_at', 'occurred_at']:
        if hasattr(event, attr):
            ts = getattr(event, attr)
            if ts:
                if isinstance(ts, datetime):
                    return ts.strftime('%Y-%m-%d %H:%M:%S')
                return str(ts)
    return 'N/A'


def serialize_value(value: Any) -> str:
    """Serialize a value into a human-readable string"""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, (list, tuple)):
        return f"[{len(value)} items]"
    elif isinstance(value, dict):
        return f"{{dict with {len(value)} keys}}"
    elif value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return value if len(value) <= 150 else value[:150] + "..."
    else:
        return str(value)


def event_to_dict(event) -> dict[str, str]:
    """
    Convert an event into a key-value dict for display.
    Supports objects with __dict__.
    """
    result = {}
    
    if hasattr(event, '__dict__'):
        for key, value in event.__dict__.items():
            if key.startswith('_'):
                continue
            result[key] = serialize_value(value)
        return result
    
    
    return result if result else {"raw": str(event)}


@router.get("/", response_class=HTMLResponse)
async def events_page(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    event_queue: EventQueuePort = Depends(get_event_queue),
):
    """
    Render events page with pagination.
    """
    per_page = 10
    offset = (page - 1) * per_page
    
    # Fetch events
    events = event_queue.get(offset=offset, limit=per_page, desc=True)

    # Prepare template data
    events_data = [
        {
            'type': event.__class__.__name__,
            'timestamp': get_event_timestamp(event),
            'fields': event_to_dict(event),
        }
        for event in events
    ]
    
    # Check if next page exists
    next_page_events = event_queue.get(offset=offset + per_page, limit=1)
    has_next = len(next_page_events) > 0
    has_prev = page > 1
    
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "events": events_data,
            "page": page,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1,
            "prev_page": page - 1,
        },
    )