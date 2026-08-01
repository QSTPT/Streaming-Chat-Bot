import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from groq import AsyncGroq

# Automatically load environment variables from .env
load_dotenv()

app = FastAPI(title="LLM Streaming WebSocket API")
groq_client = AsyncGroq()

async def stream_llm_response(websocket: WebSocket, history: list) -> str:
    accumulated_text = ""
    response_stream = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=history,
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

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    history = []

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            if data.get("action") == "message":
                user_message = data.get("content", "").strip()
                if not user_message:
                    continue
                
                history.append({"role": "user", "content": user_message})
                stream_task = asyncio.create_task(stream_llm_response(websocket, history))
                full_response = await listen_for_interrupt_or_complete(websocket, stream_task)

                if full_response:
                    history.append({"role": "assistant", "content": full_response})

    except WebSocketDisconnect:
        print("Client disconnected.")