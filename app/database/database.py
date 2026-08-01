# -- Imports -- #
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# Support for different databases via environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./your_database.db"
)

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite: disable check_same_thread for development only
    # For production, use PostgreSQL or MySQL
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL, MySQL, etc. with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Session: # type: ignore
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()