"""Server-Sent Events endpoint for live updates to the web frontend."""

import json

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from api.deps import get_current_user
from core.events import (
    CHANNEL_MOD_ADDED,
    CHANNEL_MOD_REMOVED,
    CHANNEL_MOD_UPDATED,
    CHANNEL_SERVER_STATUS,
    CHANNEL_SERVER_UPDATE,
    CHANNEL_UPLOAD_PENDING,
    CHANNEL_UPLOAD_RESOLVED,
    CHANNEL_VOTE_CAST,
    CHANNEL_VOTE_CREATED,
    CHANNEL_VOTE_RESOLVED,
    get_event_bus,
)
from models import User

router = APIRouter(tags=["sse"])

ALL_CHANNELS = [
    CHANNEL_MOD_ADDED,
    CHANNEL_MOD_REMOVED,
    CHANNEL_MOD_UPDATED,
    CHANNEL_VOTE_CREATED,
    CHANNEL_VOTE_CAST,
    CHANNEL_VOTE_RESOLVED,
    CHANNEL_UPLOAD_PENDING,
    CHANNEL_UPLOAD_RESOLVED,
    CHANNEL_SERVER_STATUS,
    CHANNEL_SERVER_UPDATE,
]


@router.get("/events/stream")
async def event_stream(request: Request):
    """SSE endpoint. Streams all event channels to connected web clients."""
    bus = get_event_bus()

    async def generate():
        async for event in bus.subscribe(*ALL_CHANNELS):
            if await request.is_disconnected():
                break
            yield {
                "event": event["channel"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(generate())
