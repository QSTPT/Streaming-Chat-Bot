import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Response, Request
from app.model_stream import stream_llm_response, listen_for_interrupt_or_complete
from app.database.schemas import CreateUserSchema, UserResponseModel
from sqlalchemy.orm import Session
from app.database.engine import get_db
from app import user_progress
from fastapi.security import OAuth2PasswordRequestForm
from app.database.models import User, Chat, UserMessage, AssistantMessage
from datetime import datetime, timezone
from app.security.session_manager import COOKIE_NAME, get_current_user_websocket
import os
from app.display_conversation import get_chat_history_db, count_tokens
from app.websocket_manager import manager

# Automatically load environment variables from .env


app = FastAPI(title="LLM Streaming WebSocket API")


@app.post("/sign_up", response_model=UserResponseModel)
def sign_up(user_input: CreateUserSchema, db: Session = Depends(get_db)) -> User:
    return user_progress.sign_up(user_input, db)

@app.post("/login")
def login(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:Session = Depends(get_db)) -> dict:
    
    auth_data = user_progress.login(form_data.username, form_data.password, db)

    response.set_cookie(
        key=COOKIE_NAME,
        value=auth_data["session_token"],
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "true").lower() == "true",
        samesite="lax",
        max_age= 7 * 24 * 60 * 60
    )
    
    return {"message": f"This is a simple test bot made for you! we are happy to have you here, {auth_data['user_name']}!"}
  
  
@app.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)) -> dict:
    return user_progress.logout(response, request, db)  

@app.get("/chats")
def display_chats(db:Session = Depends(get_db)):
    current_user = get_current_user_websocket()
    chat = db.query(Chat).filter(Chat.user_id == current_user.id).all()
    get_chat_history_db(db, chat.id)

@app.websocket("/ws/current_chat")
async def websocket_chat_endpoint(websocket: WebSocket, db:Session = Depends(get_db)): 
    
    current_user = get_current_user_websocket(websocket, db)

    manager.connect(websocket, current_user.id)

    new_chat_data = {
        "user_id":current_user.id,
        "created_at":datetime.now(timezone.utc),
        "chat_name": "Untitle", #Later we will let the model generate the name.
    }
    new_chat = Chat(**new_chat_data)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    chat = db.query(Chat).filter(Chat.user_id == current_user.id).first()
    
    history = get_chat_history_db(db, chat.id)
    
    manager.send_message({"type": "history", "data": history}, websocket)
    
    try:
        while True:
            user_input = manager.receive_json_message()
            
            if user_input.get("action") == "message":
                user_message = user_input.get("content", "").strip()
                if not user_message:
                    continue
       
                new_user_message_data = {
                    "user_id":current_user.id,
                    "chat_id":chat.id,
                    "content":user_message,
                    "created_at":datetime.now(timezone.utc)
                }
                
                new_user_message = UserMessage(**new_user_message_data)
                db.add(new_user_message)
                db.commit()
                db.refresh(new_user_message)

            
                stream_task = asyncio.create_task(stream_llm_response(websocket, chat.id, db))
                result = await listen_for_interrupt_or_complete(websocket, stream_task)

                if result:
                    full_response = result["full_response"]
                    prompt_tokens = result["prompt_tokens"]
                    completion_tokens = result["completion_tokens"]
    
                    new_assistant_message_data = {
                        "model_name":"llama-3.3-70b-versatile", #In the future we will add it automatically.
                        "chat_id":chat.id,
                        "content":full_response,
                        "created_at":datetime.now(timezone.utc)
                    }
                    
                    new_assistant_message = AssistantMessage(**new_assistant_message_data)
                    db.add(new_assistant_message)
                    db.commit()
                    db.refresh(new_assistant_message)
                    
                    manager.send_message({
                        "type": "token_update",
                        "prompt_tokens": prompt_tokens,
                        "assistant_tokens": completion_tokens,
                        "total_session_tokens": prompt_tokens + completion_tokens,
                        "max_context": 131072
                    })
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, current_user.id)
        print("Client disconnected.")