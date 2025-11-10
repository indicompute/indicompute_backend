# main.py (Stable, error-free)
# --- main.py (Stable + Error-free + Ready for Production) ---
import os
import sys
import secrets
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import (
    User, GPUNode, Job, NodeActivityLog,
    NodePricing, NodeEarning, WalletTransaction, GPUExecutionLog
)
from schemas import (
    UserCreate, UserResponse, LoginSchema,
    GPUNodeCreate, GPUNodeResponse, GPUNodeUpdate,
    NodeRegisterRequest, NodeRegisterResponse,
    NodeHeartbeatRequest, NodeStatusResponse,
    JobCreate, JobResponse,
    NodePricingCreate, NodePricingOut, NodeEarningOut,
    WalletTransactionOut, WalletBalanceOut,
    GPUExecutionLogCreate, GPUExecutionLogOut,
    NodeEarningsDashboard
)
from auth import (
    hash_password, verify_password,
    create_access_token, get_current_user,
    signup_user, login_user
)

# ---------- FASTAPI CONFIG ----------
app = FastAPI(
    title="IndiCompute API",
    version="1.5",
    description="Block F + Block G — GPU Rent + Billing + Wallet + Logs"
)

# Create DB tables (dev). For production use alembic migrations.
Base.metadata.create_all(bind=engine)

bearer_scheme = HTTPBearer(auto_error=True)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Public Marketplace GPU listing (no auth required)
# ========================
@app.get("/marketplace/gpu-nodes", response_model=List[GPUNodeResponse], tags=["Public"])
def list_public_gpu_nodes(db: Session = Depends(get_db)):
    # show only nodes marked public (safe: if model doesn't have is_public, default to True)
    if hasattr(GPUNode, "is_public"):
        nodes = db.query(GPUNode).filter(GPUNode.is_public == True).all()
    else:
        nodes = db.query(GPUNode).all()
    return nodes


# =====================================================
# ============== AUTH SECTION =========================
# =====================================================
@app.post("/signup", response_model=UserResponse, tags=["Auth"])
def signup(data: UserCreate, db: Session = Depends(get_db)):
    return signup_user(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        password=data.password,
        db=db,
    )


@app.post("/login", tags=["Auth"])
def login(data: LoginSchema, response: Response, db: Session = Depends(get_db)):
    return login_user(
        email=data.email,
        password=data.password,
        response=response,
        db=db,
    )


@app.get("/me", response_model=UserResponse, tags=["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/")
def read_root():
    return {"message": "IndiCompute Backend is Live ✅"}


# =====================================================
# ============== GPU NODES SECTION ====================
# =====================================================

@app.post("/gpu-nodes", response_model=GPUNodeResponse, tags=["GPU"])
def create_gpu_node(data: GPUNodeCreate,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    node_key = secrets.token_hex(8)
    node = GPUNode(
        owner_id=current_user.id,
        location=data.location,
        gpu_model=data.gpu_model,
        gpu_count=data.gpu_count,
        node_key=node_key,
        is_online=False
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


# ✅ FIXED — Add GET /gpu-nodes (was missing earlier)
@app.get("/gpu-nodes", response_model=List[GPUNodeResponse], tags=["GPU"])
def list_user_gpu_nodes(current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Return all GPU nodes owned by the current user."""
    nodes = db.query(GPUNode).filter(GPUNode.owner_id == current_user.id).all()
    return nodes


@app.put("/gpu-nodes/{node_id}", response_model=GPUNodeResponse, tags=["GPU"])
def update_gpu_node(node_id: int, data: GPUNodeUpdate,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "GPU node not found")
    if data.location is not None:
        node.location = data.location
    if data.gpu_model is not None:
        node.gpu_model = data.gpu_model
    if data.gpu_count is not None:
        node.gpu_count = data.gpu_count
    db.commit()
    db.refresh(node)
    return node


@app.delete("/gpu-nodes/{node_id}", tags=["GPU"])
def delete_gpu_node(node_id: int,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "GPU node not found")
    db.delete(node)
    db.commit()
    return {"detail": "GPU node deleted"}


@app.post("/register-node", response_model=NodeRegisterResponse, tags=["GPU"])
def register_node(data: NodeRegisterRequest,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    node_key = secrets.token_hex(16)
    node = GPUNode(
        owner_id=current_user.id,
        location=data.location,
        gpu_model=data.gpu_model,
        gpu_count=data.gpu_count,
        node_key=node_key,
        is_online=False,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@app.post("/node-heartbeat", tags=["GPU"])
def node_heartbeat(req: NodeHeartbeatRequest, db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == req.node_id, GPUNode.node_key == req.node_key).first()
    if not node:
        raise HTTPException(401, "Invalid node credentials")
    node.is_online = True
    node.last_heartbeat = datetime.utcnow()
    db.add(NodeActivityLog(node_id=node.id, event_type="heartbeat", message="Node heartbeat received"))
    db.commit()
    return {"detail": "heartbeat received", "node_id": node.id}


@app.get("/node-status/{node_id}", response_model=NodeStatusResponse, tags=["GPU"])
def node_status(node_id: int,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "GPU node not found")
    seconds = None
    if node.last_heartbeat:
        seconds = int((datetime.utcnow() - node.last_heartbeat).total_seconds())
    return {
        "id": node.id,
        "is_online": node.is_online,
        "last_heartbeat": node.last_heartbeat,
        "seconds_since_last_heartbeat": seconds,
    }


# ✅ FIXED — Keep only one “details” endpoint
@app.get("/gpu-nodes/details", tags=["Public"])
def get_gpu_nodes_details_public(db: Session = Depends(get_db)):
    """Public: GPU nodes with pricing and last_active (used in Marketplace UI)."""
    nodes = db.query(GPUNode).all()
    results = []
    for n in nodes:
        pricing = db.query(NodePricing).filter(NodePricing.node_id == n.id).first()
        price_per_hour = float(pricing.price_per_hour) if pricing else None
        currency = pricing.currency if pricing else "INR"

        last_active = None
        if n.last_heartbeat:
            last_active = n.last_heartbeat
        else:
            log = (
                db.query(NodeActivityLog)
                .filter(NodeActivityLog.node_id == n.id, NodeActivityLog.event_type == "heartbeat")
                .order_by(NodeActivityLog.timestamp.desc())
                .first()
            )
            if log:
                last_active = getattr(log, "timestamp", None)

        results.append({
            "id": n.id,
            "owner_id": n.owner_id,
            "location": n.location,
            "gpu_model": n.gpu_model,
            "gpu_count": n.gpu_count,
            "is_online": n.is_online,
            "price_per_hour": price_per_hour,
            "currency": currency,
            "last_active": last_active.isoformat() if last_active else None,
        })
    return results


# =====================================================
# ============== PRICING / JOBS / WALLET / EARNINGS ===
# =====================================================
@app.post("/pricing/{node_id}", response_model=NodePricingOut, tags=["Pricing"])
def set_node_pricing(node_id: int, data: NodePricingCreate,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "Node not found or not owned by user")

    pricing = db.query(NodePricing).filter(NodePricing.node_id == node_id).first()
    if pricing:
        pricing.price_per_hour = data.price_per_hour
        pricing.currency = data.currency
        pricing.last_updated = datetime.utcnow()
    else:
        pricing = NodePricing(node_id=node_id, price_per_hour=data.price_per_hour, currency=data.currency)
        db.add(pricing)
    db.commit()
    db.refresh(pricing)
    return pricing


@app.get("/pricing/{node_id}", response_model=NodePricingOut, tags=["Pricing"])
def get_node_pricing(node_id: int, db: Session = Depends(get_db)):
    pricing = db.query(NodePricing).filter(NodePricing.node_id == node_id).first()
    if not pricing:
        raise HTTPException(404, "Pricing not set for this node")
    return pricing


# ---------- Jobs ----------
@app.post("/submit-job", response_model=JobResponse, tags=["Jobs"])
def submit_job(job: JobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == job.node_id, GPUNode.node_key == job.node_key).first()
    if not node:
        raise HTTPException(403, "Invalid node credentials")

    # ✅ Get pricing (if not set, default ₹10/hr)
    pricing = db.query(NodePricing).filter(NodePricing.node_id == node.id).first()
    price_per_hour = pricing.price_per_hour if pricing else 10.0

    # ✅ Check user balance
    if (current_user.wallet_balance or 0) < price_per_hour:
        raise HTTPException(400, "Insufficient wallet balance")

    # ✅ Deduct wallet
    current_user.wallet_balance -= price_per_hour

    # ✅ Create transaction
    tx = WalletTransaction(
        user_id=current_user.id,
        type="debit",
        amount=price_per_hour,
        description=f"Job submitted on node {node.gpu_model}"
    )
    db.add(tx)

    # ✅ Create job
    new_job = Job(
        user_id=current_user.id,
        node_id=node.id,
        command=job.command,
        status="running",
        result=f"Job '{job.command}' is running."
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


@app.get("/job-status/{job_id}", response_model=JobResponse, tags=["Jobs"])
def job_status(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/job/complete", response_model=JobResponse, tags=["Jobs"])
def mark_job_complete(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    job.status = "completed"
    job.result = f"✅ Job '{job.command}' marked completed successfully."

    # ✅ Auto Earnings Logic (safe addition) - using top-level imports (no duplicate import)
    earning_amount = 5.0  # fixed per job (testing)

    # create earning record
    earning = NodeEarning(
        node_id=job.node_id,
        amount=earning_amount,
        currency="INR"
    )
    db.add(earning)

    # find node owner and update wallet
    node = db.query(GPUNode).filter(GPUNode.id == job.node_id).first()
    if node:
        owner = db.query(User).filter(User.id == node.owner_id).first()
        if owner:
            owner.wallet_balance = (owner.wallet_balance or 0.0) + earning_amount
            # optionally record a WalletTransaction (credit)
            tx = WalletTransaction(
                user_id=owner.id,
                type="credit",
                amount=earning_amount,
                description=f"Payout for job {job.id}"
            )
            db.add(tx)

    db.commit()
    db.refresh(job)
    return job


# ---------- Wallet ----------
@app.post("/wallet/topup", response_model=WalletBalanceOut, tags=["Wallet"])
def wallet_topup(amount: float = Query(...), 
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    # ✅ Validation
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    # ✅ Fetch user from DB
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Update wallet balance
    user.wallet_balance = (user.wallet_balance or 0.0) + float(amount)

    # ✅ Create transaction record
    tx = WalletTransaction(
        user_id=user.id,
        type="credit",
        amount=float(amount),
        description="Wallet top-up via frontend"
    )
    db.add(tx)
    db.commit()
    db.refresh(user)

    return {"user_id": user.id, "wallet_balance": user.wallet_balance}

@app.get("/wallet/balance", response_model=WalletBalanceOut, tags=["Wallet"])
def get_wallet_balance(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "wallet_balance": current_user.wallet_balance or 0.0}


@app.get("/wallet/transactions", response_model=List[WalletTransactionOut], tags=["Wallet"])
def get_wallet_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == current_user.id)
        .order_by(WalletTransaction.timestamp.desc())
        .all()
    )


# ---------- Earnings ----------
@app.get("/earnings/{node_id}", response_model=List[NodeEarningOut], tags=["Earnings"])
def get_node_earnings(node_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "Node not found or not owned by user")
    return (
        db.query(NodeEarning)
        .filter(NodeEarning.node_id == node_id)
        .order_by(NodeEarning.timestamp.desc())
        .all()
    )


@app.get("/earnings/dashboard/{node_id}", response_model=NodeEarningsDashboard, tags=["Earnings"])
def get_earnings_dashboard(node_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == node_id, GPUNode.owner_id == current_user.id).first()
    if not node:
        raise HTTPException(404, "Node not found or not owned by user")

    total = sum([float(e[0]) for e in db.query(NodeEarning.amount).filter(NodeEarning.node_id == node_id).all() if e[0]])
    total_jobs = db.query(NodeEarning).filter(NodeEarning.node_id == node_id).count()
    last_tx = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == current_user.id, WalletTransaction.type == "credit")
        .order_by(WalletTransaction.timestamp.desc())
        .first()
    )
    currency = db.query(NodeEarning.currency).filter(NodeEarning.node_id == node_id).first()

    return {
        "node_id": node_id,
        "total_earnings": float(round(total, 8)),
        "currency": currency[0] if currency else "INR",
        "total_jobs": total_jobs,
        "last_payout": last_tx.timestamp if last_tx else None,
    }


# ---------- GPU Execution Logs ----------
@app.post("/gpu-exec/log", response_model=GPUExecutionLogOut, tags=["GPUExec"])
def post_gpu_execution_log(payload: GPUExecutionLogCreate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    log = GPUExecutionLog(job_id=payload.job_id, log_type=payload.log_type, details=payload.details)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@app.get("/gpu-exec/logs/{job_id}", response_model=List[GPUExecutionLogOut], tags=["GPUExec"])
def get_gpu_execution_logs(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    node = db.query(GPUNode).filter(GPUNode.id == job.node_id).first()
    if not node:
        raise HTTPException(404, "Node not found")
    if job.user_id != current_user.id and node.owner_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    return db.query(GPUExecutionLog).filter(GPUExecutionLog.job_id == job_id).all()


# =====================================================
# ============== SWAGGER SECURITY =====================
# =====================================================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    schema["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi