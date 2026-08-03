# -- Imports -- #
from app.database.engine import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(512), nullable=False)
    
class UserSession(Base):
    __tablename__ = "UserSession"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    User = relationship("User")
    
    
## -- These models should be used inside Websocket; no need to use schema for them -- ##
class Chat(Base):
    __tablename__ = "Chat"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    chat_name= Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    User = relationship("User")
    
class UserMessage(Base):
    __tablename__ = "UserMessage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False) # This has no use. we use chat for finding messages of the user. maybe admin will use it oneday for getting total token usage.
    chat_id = Column(Integer, ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(600), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    User = relationship("User")
    Chat = relationship("Chat")
    
class AssistantMessage(Base):
    __tablename__ = "AssistantMessage"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(75), nullable=False)
    chat_id = Column(Integer, ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(4000), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    Chat = relationship("Chat")