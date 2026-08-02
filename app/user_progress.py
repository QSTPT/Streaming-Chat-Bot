from sqlalchemy.orm import Session
from database.models import User
from fastapi import HTTPException
from security.hash_password import get_password_hash, verify_password

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