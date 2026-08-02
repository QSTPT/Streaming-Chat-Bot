from sqlalchemy.orm import Session
from app.database.models import User
from fastapi import HTTPException, Response, Request, Depends
from app.security.password_manager import get_password_hash, verify_password
from app.security.session_manager import create_session
from app.database.engine import get_db
from app.security.session_manager import COOKIE_NAME, delete_session

def sign_up(user_input, db:Session):
    if db.query(User).filter(User.username == user_input.username).first():
        raise HTTPException(
            status_code=422,
            detail="User already exists"
        )
        
    user_data = {
        "name" : user_input.name,
        "username": user_input.username,
        "password" : get_password_hash(user_input.password)
    }
    
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def login(username, password, db:Session):
    user = db.query(User).filter(
        User.username == username,
    ).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
            )
        
    hashed_token = create_session(db,user.id)
    
    return {"session_token": hashed_token, "user_name": user.name}

def logout(response: Response, request: Request, db: Session = Depends(get_db)) -> dict:
    raw_session_token = request.cookies.get(COOKIE_NAME)
    
    if raw_session_token:
        delete_session(db, raw_session_token)
        
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Successfully logged out."}