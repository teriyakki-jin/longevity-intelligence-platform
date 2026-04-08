"""AI health coach streaming endpoint."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from longevity.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_history: list[dict] = Field(default_factory=list)
    health_context: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    conversation_id: str | None = None


async def _stream_response(message: str, history: list[dict], health_context: str | None) -> AsyncGenerator[str, None]:
    """Generate SSE stream from Claude response."""
    try:
        from longevity.coach.client import HealthCoachClient

        client = HealthCoachClient()
        messages = history + [{"role": "user", "content": message}]

        for token in client.stream_chat(messages, health_context=health_context):
            yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error("coach_stream_error", error=str(e))
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@router.post("/chat")
async def chat_with_coach(req: ChatRequest):
    """Chat with the AI health coach. Supports streaming SSE."""
    if req.stream:
        return StreamingResponse(
            _stream_response(req.message, req.conversation_history, req.health_context),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming fallback
    try:
        from longevity.coach.client import HealthCoachClient
        client = HealthCoachClient()
        messages = req.conversation_history + [{"role": "user", "content": req.message}]
        response = client.chat(messages, health_context=req.health_context)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error("coach_chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
