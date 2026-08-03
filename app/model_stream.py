import json
import asyncio
from fastapi import WebSocket, Depends
from app.database.engine import Session, get_db
from main import groq_client
from database.models import UserMessage, AssistantMessage
from display_conversation import get_chat_history_db, count_tokens

MAX_ALLOWED_CONTEXT = 125000  # Safe buffer below Groq's 131,072 max limit
RESERVED_FOR_RESPONSE = 1024

async def stream_llm_response(websocket: WebSocket, chat_id, db: Session = Depends(get_db)) -> str:
    
    raw_history = get_chat_history_db(db, chat_id)

    messages = [{"role": msg.role, "content": msg.content} for msg in raw_history]
    
    prompt_tokens = sum(count_tokens(m["content"]) for m in messages)
    
    while (prompt_tokens + RESERVED_FOR_RESPONSE) > MAX_ALLOWED_CONTEXT and len(messages) > 1:
        removed_msg = messages.pop(0) # if any system prompt then pop(1)
        prompt_tokens -= count_tokens(removed_msg["content"])
    
    accumulated_text = ""
    
    response_stream = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=RESERVED_FOR_RESPONSE,
    )

    async for chunk in response_stream:
        delta = chunk.choices[0].delta.content
        if delta:
            accumulated_text += delta
            await websocket.send_json({"type": "token", "content": delta})

    await websocket.send_json({"type": "end"})
    return {
        "full_response": accumulated_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": count_tokens(accumulated_text)
    }

async def listen_for_interrupt_or_complete(websocket: WebSocket, stream_task: asyncio.Task) -> str:
    while not stream_task.done():
        try:
            raw_data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            data = json.loads(raw_data)
            if data.get("action") == "stop":
                stream_task.cancel()
                await websocket.send_json({"type": "stopped"})
                break
        except asyncio.TimeoutError:
            continue

    try:
        return await stream_task
    except asyncio.CancelledError:
        return ""