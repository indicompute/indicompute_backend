# ---------- Pydantic Schemas ----------
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# ===== GPU Node Schemas =====
class GPUNodeBase(BaseModel):
    Owner_name: str
    location: str
    gpu_model: str
    gpu_count: int

class GPUNodeCreate(GPUNodeBase):
    pass

class GPUNodeResponse(GPUNodeBase):
    id: int
    class Config:
        orm_mode = True  # FastAPI ko SQLAlchemy object ko serialize karne deta hai


# ===== User Schemas (Signup) =====
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str  # abhi simple; password policy baad me add karenge

class UserResponse(UserBase):
    id: int
    class Config:
        orm_mode = True


# ===== User Login Schema =====
class LoginSchema(BaseModel):
    email: EmailStr
    password: str
