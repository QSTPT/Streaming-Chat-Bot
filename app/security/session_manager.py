import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
from app.database.models import UserSession
import secrets

SESSION_EXPIRE_DAYS = 7 
COOKIE_NAME = "historia_session"
MAX_SESSIONS_PER_USER = 5

def create_session(db: Session, user_id: int) -> str:
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id)
        .order_by(UserSession.expires_at.asc())
        .all()
    )
    if len(sessions) >= MAX_SESSIONS_PER_USER:
        for old in sessions[: len(sessions) - MAX_SESSIONS_PER_USER + 1]:
            db.delete(old)
    
    
    raw_token = secrets.token_urlsafe(32)
    hashed_token = hash_session(raw_token)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    
    new_session = UserSession(
        token=hashed_token,
        user_id=user_id,
        expires_at=expires
    )
    db.add(new_session)
    db.commit()
    return raw_token

def hash_session(token:str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def verify_session(db:Session, token:str) -> UserSession | None:
    return (
        db.query(UserSession)
        .options(joinedload(UserSession.user))
        .filter(
            UserSession.token == hash_session(token),
            UserSession.expires_at > datetime.now(timezone.utc),
        ).first()
    )
    
# Use it inside logout    
def delete_session(db:Session, raw_token:str) -> None:
    db.query(UserSession).filter(
        UserSession.token_hash == hash_session(raw_token)
    ).delete()
    db.commit()