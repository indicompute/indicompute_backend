# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1) yahi se DB URL aayega (Render ke env se)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # local testing ke liye (agar env set nahi hai)
    # yaha tum apna local Postgres ya SQLite rakh sakte ho
    # फिलहाल कम से कम crash na ho isliye simple message:
    print("⚠ WARNING: DATABASE_URL not set, using local SQLite")
    DATABASE_URL = "sqlite:///./local.db"

# 2) PostgreSQL / normal URLs ke liye simple engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# 3) Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4) Base class for all models
Base = declarative_base()


# 5) Dependency (FastAPI routes me use hota hai)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()