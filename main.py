# main.py (Stable, error-free)
# --- main.py (Stable + Error-free + Ready for Production) ---

import sys
import secrets
from datetime import datetime
from typing import List
import os

from dotenv import load_dotenv

# ✅ Correct logger import (safe local import)
import log_config
logger = log_config.setup_logger()


# ye line env file load karti hai
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))



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
    NodeEarningsDashboard, Token
)
from pydantic import BaseModel

class WalletTopupRequest(BaseModel):
    amount: float

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
@app.get("/healthz", tags=["System"])
def health_check():
    logger.info("Health check endpoint called successfully.")
    return {"status": "ok"}
@app.get("/db-test")
def db_test():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return {"database": "connected"}
    except Exception as e:
        return {"error": str(e)}



# Create DB tables (dev). For production use alembic migrations.
Base.metadata.create_all(bind=engine)

bearer_scheme = HTTPBearer(auto_error=True)

# ---------- CORS ----------

origins = [
    "https://app.indicompute.in",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
# ------------------ SIGNUP ------------------
# ---------- SIGNUP ----------
@app.post("/signup", response_model=Token, tags=["Auth"])
def signup_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    new_user = signup_user(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        password=user.password,
        db=db
    )

    token = create_access_token({"user_id": new_user.id, "email": new_user.email})
    return {"access_token": token, "token_type": "bearer"}


# ---------- LOGIN ----------
@app.post("/login", response_model=Token, tags=["Auth"])
def login_user_endpoint(data: LoginSchema, response: Response, db: Session = Depends(get_db)):
    result = login_user(email=data.email, password=data.password, response=response, db=db)
    return {"access_token": result["access_token"], "token_type": result["token_type"]}





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

@app.post("/gpu-nodes/register", tags=["GPU Nodes"])
def register_gpu_node(data: NodeRegisterRequest,
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
            "node_key": getattr(n, "node_key", None),
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

# Add this under your Jobs section in main.py (below other job endpoints)

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

@app.post("/simulate-job-complete/{job_id}", response_model=JobResponse, tags=["Jobs"])
def simulate_job_complete(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Testing endpoint (protected): mark job complete and credit node owner.
    Idempotent: if job already completed, just returns the job.
    Use this for testing earnings flow (simulate node reporting job finish).
    """
    # 1) load job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # optional: restrict who can call this (owner of node or the user who submitted the job or admin)
    node = db.query(GPUNode).filter(GPUNode.id == job.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Allow only: job submitter OR node owner OR any authenticated user with same id (for testing)
    if current_user.id not in (job.user_id, node.owner_id):
        # you can relax this if you want testers to call it — change as needed
        raise HTTPException(status_code=403, detail="Not allowed to complete this job")

    # If already completed, return it (idempotent)
    if job.status == "completed":
        return job

    # Determine payout amount: from pricing or fallback
    pricing = db.query(NodePricing).filter(NodePricing.node_id == node.id).first()
    price_per_hour = float(pricing.price_per_hour) if pricing and pricing.price_per_hour is not None else 10.0

    # Wrap modifications in transaction for safety
    try:
        # Start transaction block
        # Deduct at submission is already handled in submit_job. Here we only credit owner and record earning & tx.
        job.status = "completed"
        job.result = f"✅ Job '{job.command}' marked completed by simulate endpoint."

        # Create earning record
        earning = NodeEarning(node_id=node.id, amount=price_per_hour, currency=(pricing.currency if pricing else "INR"))
        db.add(earning)

        # Credit owner wallet
        owner = db.query(User).filter(User.id == node.owner_id).with_for_update().first()
        if owner:
            owner.wallet_balance = (owner.wallet_balance or 0.0) + price_per_hour
            tx_owner = WalletTransaction(
                user_id=owner.id,
                type="credit",
                amount=price_per_hour,
                description=f"Payout for job {job.id}"
            )
            db.add(tx_owner)
        else:
            # Should not happen normally
            raise HTTPException(status_code=500, detail="Owner not found during payout")

        # Optional: add NodeActivityLog
        db.add(NodeActivityLog(node_id=node.id, event_type="job_completed", message=f"Job {job.id} completed."))

        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during simulate complete")
    from typing import List

@app.get("/user-jobs", response_model=List[JobResponse], tags=["Jobs"])
def get_user_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Return all jobs submitted by the currently logged-in user.
    """
    jobs = db.query(Job).filter(Job.user_id == current_user.id).order_by(Job.id.desc()).all()
    return jobs


# ---------- Wallet ----------
@app.post("/wallet/topup", response_model=WalletBalanceOut, tags=["Wallet"])
def wallet_topup(data: WalletTopupRequest,  
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    amount = data.amount

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
    return {"user_id": current_user.id,"username": current_user.username, "wallet_balance": current_user.wallet_balance or 0.0}


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