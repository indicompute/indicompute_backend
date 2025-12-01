from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.hash import argon2
import jwt
import os

from database import get_db
from models import User


# Load env
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

print("AUTH_SECRET_KEY =", SECRET_KEY)

bearer_scheme = HTTPBearer(auto_error=True)


# =====================================================
# PASSWORD HASHING (Argon2 — recommended & stable)
# =====================================================

def hash_password(plain: str) -> str:
    """Hash password using Argon2 (no 72-byte limit issue)."""
    return argon2.hash(plain.strip())

def verify_password(plain: str, hashed: str) -> bool:
    """Verify Argon2 hashed password."""
    return argon2.verify(plain.strip(), hashed)


# =====================================================
# CREATE JWT TOKEN
# =====================================================
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =====================================================
# SIGNUP USER
# =====================================================
def signup_user(email: str, username: str, full_name: str, password: str, db: Session):

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    print(f"[AUTH][SIGNUP] id={new_user.id} email={new_user.email}")

    return new_user


# =====================================================
# LOGIN USER
# =====================================================
def login_user(email: str, password: str, response: Response, db: Session):

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id, "email": user.email})

    # Optional cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        domain=".indicompute.in",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
    }


# =====================================================
# CURRENT LOGGED IN USER
# =====================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
