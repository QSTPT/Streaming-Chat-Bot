import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from groq import AsyncGroq
from model_stream import stream_llm_response, listen_for_interrupt_or_complete
from database.schemas import CreateUserSchema
from sqlalchemy.orm import Session
from database.database import get_db
import user_progress

# Automatically load environment variables from .env
load_dotenv()

app = FastAPI(title="LLM Streaming WebSocket API")
groq_client = AsyncGroq()

@app.post("/sign_up")
def sign_up(user_input: CreateUserSchema, db: Session = Depends(get_db)):
    return user_progress.sign_up(user_input, db)


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