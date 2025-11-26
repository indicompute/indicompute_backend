# --- auth.py (Final Stable: SHA256 + bcrypt + JWT + Signup/Login) ---

import jwt
import hashlib
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models import User
from main import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


# =====================================================
# PASSWORD + JWT CONFIG
# =====================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)


# =====================================================
# PASSWORD HASHING (🔥 FIXED VERSION)
# =====================================================

def hash_password(password: str) -> str:
    """
    Fix for bcrypt 72-byte limit:
    1) First hash plain password with SHA256 → fixed 64 chars
    2) Then bcrypt that safe fixed string
    """
    sha = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(sha)


def verify_password(password: str, hashed: str) -> bool:
    sha = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.verify(sha, hashed)


# =====================================================
# CREATE JWT TOKEN
# =====================================================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


# =====================================================
# SIGNUP
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
        hashed_password=hash_password(password),   # 🔥 fixed
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    print(f"[AUTH][SIGNUP] new_user id={new_user.id} email={new_user.email}")

    return new_user


# =====================================================
# LOGIN
# =====================================================

def login_user(email: str, password: str, response: Response, db: Session):

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id, "email": user.email})

    print(f"[AUTH][LOGIN] user_id={user.id} email={user.email} token_len={len(token)}")

    # Optional cookie (auto login)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
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
# CURRENT USER (DECODE JWT)
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id") or payload.get("sub")

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
