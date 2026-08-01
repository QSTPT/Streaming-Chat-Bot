# -- Imports -- #
from ..database.database import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(512), nullable=False)
    active = Column(Boolean, default=False)
    
class Chat(Base):
    __tablename__ = "Chat"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    chat_name = name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    User = relationship("User")
    
class UserMessage(Base):
    __tablename__ = "UserMessage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    chat_id = Column(Integer, ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(600), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    User = relationship("User")
    Chat = relationship("Chat")
    
class AssistantMessage(Base):
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(75), nullable=False)
    chat_id = Column(Integer, ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False)
    user_message_id = Column(Integer, ForeignKey("UserMessage.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(4000), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    Chat = relationship("Chat")
    UserMessage = relationship("UserMessage")