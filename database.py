from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Neon ke liye driver add kar (safe way)
if SQLALCHEMY_DATABASE_URL:
    if "neon.tech" in SQLALCHEMY_DATABASE_URL:
        if not SQLALCHEMY_DATABASE_URL.startswith("postgresql+psycopg2://"):
            SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "sslmode": "require",
        "channel_binding": "require"  # Neon ke liye zaroori
    } if "neon.tech" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()