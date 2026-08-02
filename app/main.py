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
from fastapi.security import OAuth2PasswordRequestForm
from database.models import User, Chat, UserMessage, AssistantMessage
from datetime import datetime, timezone

# Automatically load environment variables from .env
load_dotenv()

app = FastAPI(title="LLM Streaming WebSocket API")
groq_client = AsyncGroq()

@app.post("/sign_up")
def sign_up(user_input: CreateUserSchema, db: Session = Depends(get_db)) -> User:
    return user_progress.sign_up(user_input, db)

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)) -> dict:
    user_progress.login(form_data.username, form_data.password, db)


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket, user_id, chat_id, db:Session = Depends(get_db)): # When we add session there will be no user_id. we will get it via user_session.
    await websocket.accept()

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            if data.get("action") == "message":
                user_message = data.get("content", "").strip()
                if not user_message:
                    continue
                
                new_chat_data = {
                    "user_id":user_id, #Later when i add session there will be no user_id like that.
                    "created_at":datetime.now(timezone.utc),
                    "chat_name": "Untitle", #Later we will let the model generate the name.
                }
                new_chat = Chat(**new_chat_data)
                db.add(new_chat)
                db.commit()
                db.refresh(new_chat)
                
                new_user_message_data = {
                    "user_id":user_id,
                    "chat_id":chat_id,
                    "content":user_message,
                    "created_at":datetime.now(timezone.utc)
                }
                
                new_user_message = UserMessage(**new_user_message_data)
                db.add(new_user_message)
                db.commit()
                db.refresh(new_user_message)

            
                stream_task = asyncio.create_task(stream_llm_response(websocket, chat_id, db))
                full_response = await listen_for_interrupt_or_complete(websocket, stream_task)

                if full_response:
                    new_assistant_message_data = {
                        "model_name":"llama-3.3-70b-versatile", #In the future we will add it automatically.
                        "chat_id":chat_id,
                        "content":full_response,
                        "created_at":datetime.now(timezone.utc)
                    }

    except WebSocketDisconnect:
        print("Client disconnected.")