import asyncio
import json
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from ..core.security import get_token_from_cookie, decode_jwt

router = APIRouter(prefix="/events", tags=["events"])

user_queues: dict[str, list[asyncio.Queue]] = {}


def push_event(user_id: str, event: dict):
    queues = user_queues.get(user_id, [])
    for q in queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


@router.get("/runs")
async def sse_runs(request: Request):
    token = get_token_from_cookie(request)
    if not token:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    payload = decode_jwt(token)
    user_id = payload["user_id"]

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    user_queues.setdefault(user_id, []).append(queue)

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield {"event": "run_update", "data": json.dumps(data)}
        except asyncio.CancelledError:
            pass
        finally:
            queues = user_queues.get(user_id, [])
            if queue in queues:
                queues.remove(queue)

    return EventSourceResponse(event_generator())
