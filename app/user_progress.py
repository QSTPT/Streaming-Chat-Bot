from sqlalchemy.orm import Session
from database.models import User
from fastapi import HTTPException

def sign_up(user_input, db:Session):
    if db.query(User).filter(User.username == user_input.username).first():
        raise HTTPException(
            status_code=422,
            detail="User already exists"
        )
        
    user_data = {
        "name" : user_input.name,
        "username": user_input.username,
        "password" : user_input.password # !!! Hash the password later.
    }
    
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def login(username, password, db:Session):
    user = db.query(User).filter(
        User.username == username,
        User.password == password
    ).first()
    
    # Later When you add password hash you have to check the password via verify password!
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
            )