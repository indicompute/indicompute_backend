# --- schemas.py (Final, Clean & Pydantic v2 Compatible) ---

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# =====================================================
# ===============  AUTH  ===============================
# =====================================================
class UserCreate(BaseModel):
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str]
    full_name: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class LoginSchema(BaseModel):
    email: str
    password: str


# =====================================================
# ===============  GPU NODE ============================
# =====================================================
class GPUNodeCreate(BaseModel):
    location: str
    gpu_model: str
    gpu_count: int


class GPUNodeUpdate(BaseModel):
    location: Optional[str]
    gpu_model: Optional[str]
    gpu_count: Optional[int]


class GPUNodeResponse(BaseModel):
    id: int
    location: str
    gpu_model: str
    gpu_count: int
    owner_id: int
    is_online: bool
    last_heartbeat: Optional[datetime]
    node_key: Optional[str]
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# =============== NODE REGISTER =======================
# =====================================================
class NodeRegisterRequest(BaseModel):
    location: str
    gpu_model: str
    gpu_count: int


class NodeRegisterResponse(BaseModel):
    id: int
    owner_id: int
    location: str
    gpu_model: str
    gpu_count: int
    node_key: str
    is_online: bool
    last_heartbeat: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class NodeHeartbeatRequest(BaseModel):
    node_id: int
    node_key: str

    # ---> paste this exactly after NodeHeartbeatRequest (or near other small response models)

class Token(BaseModel):
    access_token: str
    token_type: str


# =====================================================
# =============== NODE STATUS =========================
# =====================================================
class NodeStatusResponse(BaseModel):
    id: int
    is_online: bool
    last_heartbeat: Optional[datetime]
    seconds_since_last_heartbeat: Optional[int]
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# =============== JOB SYSTEM ==========================
# =====================================================
class JobCreate(BaseModel):
    node_id: int = Field(..., example=1)
    node_key: str = Field(..., example="a1b2c3d4f5g6h7i8")
    command: str = Field(..., example="echo hello GPU")


class JobResponse(BaseModel):
    id: int
    user_id: int
    node_id: int
    command: str
    status: str
    result: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# =============== BLOCK G =============================
# =====================================================

# ---------- NODE PRICING ----------
class NodePricingBase(BaseModel):
    price_per_hour: float
    currency: str = "INR"


class NodePricingCreate(NodePricingBase):
    pass


class NodePricingOut(NodePricingBase):
    id: int
    node_id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- NODE EARNINGS ----------
class NodeEarningOut(BaseModel):
    id: int
    node_id: int
    job_id: Optional[int]
    amount: float
    duration_hours: float
    currency: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- WALLET ----------
class WalletTransactionBase(BaseModel):
    type: str
    amount: float
    description: Optional[str]


class WalletTransactionCreate(WalletTransactionBase):
    pass


class WalletTransactionOut(WalletTransactionBase):
    id: int
    user_id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class WalletBalanceOut(BaseModel):
    user_id: int
    wallet_balance: float


# ---------- JOB BILLING ----------
class JobCompleteRequest(BaseModel):
    job_id: int
    force_complete: Optional[bool] = False


class JobBillingOut(BaseModel):
    job_id: int
    duration_hours: float
    price_per_hour: float
    amount_charged: float
    currency: str
    new_wallet_balance: float
    model_config = ConfigDict(from_attributes=True)


# ---------- GPU EXECUTION LOGS ----------
class GPUExecutionLogCreate(BaseModel):
    job_id: int
    log_type: str
    details: Optional[str]


class GPUExecutionLogOut(BaseModel):
    id: int
    job_id: int
    log_type: str
    details: Optional[str]
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- OWNER DASHBOARD ----------
class NodeEarningsDashboard(BaseModel):
    node_id: int
    total_earnings: float
    currency: str
    total_jobs: int
    last_payout: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)
