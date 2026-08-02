import json
import asyncio
from fastapi import WebSocket, Depends
from database.database import Session, get_db
from main import groq_client
from database.models import UserMessage, AssistantMessage


async def stream_llm_response(websocket: WebSocket, chat_id, db: Session = Depends(get_db)) -> str:
    
    user_content = db.query(UserMessage).filter(UserMessage.chat_id == chat_id).first().content
    
    assistant_content = db.query(AssistantMessage).filter(AssistantMessage.chat_id == chat_id).first().content()
    both_side_message_list = [user_content, assistant_content]
    
    accumulated_text = ""
    
    response_stream = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=both_side_message_list,
        stream=True,
        temperature=0.7,
        max_tokens=1024,
    )

    async for chunk in response_stream:
        delta = chunk.choices[0].delta.content
        if delta:
            accumulated_text += delta
            await websocket.send_json({"type": "token", "content": delta})

    await websocket.send_json({"type": "end"})
    return accumulated_text

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