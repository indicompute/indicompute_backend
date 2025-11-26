# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 1) ENV load
load_dotenv()

# 2) ENV se URL read karo
DATABASE_URL = os.getenv("DATABASE_URL")

# 3) Agar DATABASE_URL nahi hai → Local SQLite fallback
if not DATABASE_URL:
    print("⚠ WARNING: DATABASE_URL not set → using local SQLite (local.db)")
    DATABASE_URL = "sqlite:///./local.db"

# 4) SQLite ke liye special arg; PostgreSQL ke liye nahi
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 5) Engine create → PostgreSQL / SQLite automatic
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# 6) Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 7) Base Model
Base = declarative_base()

# 8) Dependency (FastAPI routes ke liye)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
