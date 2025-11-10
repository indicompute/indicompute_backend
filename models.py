# models.py (Final Synced Version)
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ---------- USERS ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    wallet_balance = Column(Float, default=0.0)

    nodes = relationship("GPUNode", back_populates="owner", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("WalletTransaction", back_populates="user", cascade="all, delete-orphan")


# ---------- GPU NODES ----------
class GPUNode(Base):
    __tablename__ = "gpu_nodes"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, nullable=False)
    gpu_model = Column(String, nullable=False)
    gpu_count = Column(Integer, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", back_populates="nodes")

    node_key = Column(String, nullable=True)
    is_online = Column(Boolean, nullable=False, default=False)
    last_heartbeat = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)
    price_per_hour = Column(Float, nullable=True)

    jobs = relationship("Job", back_populates="node", cascade="all, delete-orphan")
    activity_logs = relationship("NodeActivityLog", back_populates="node", cascade="all, delete-orphan")
    pricing = relationship("NodePricing", back_populates="node", uselist=False, cascade="all, delete-orphan")
    earnings = relationship("NodeEarning", back_populates="node", cascade="all, delete-orphan")


# ---------- JOBS ----------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id"), nullable=False, index=True)

    command = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    cost_incurred = Column(Float, default=0.0)
    currency = Column(String, default="INR")

    user = relationship("User", back_populates="jobs")
    node = relationship("GPUNode", back_populates="jobs")
    execution_logs = relationship("GPUExecutionLog", back_populates="job", cascade="all, delete-orphan")


# ---------- NODE ACTIVITY LOGS ----------
class NodeActivityLog(Base):
    __tablename__ = "node_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id"), nullable=False)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    node = relationship("GPUNode", back_populates="activity_logs")


# ---------- NODE PRICING ----------
class NodePricing(Base):
    __tablename__ = "node_pricing"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id", ondelete="CASCADE"))
    price_per_hour = Column(Float, nullable=False, default=0.0)
    currency = Column(String, default="INR")
    last_updated = Column(DateTime, default=datetime.utcnow)

    node = relationship("GPUNode", back_populates="pricing")


# ---------- NODE EARNINGS ----------
class NodeEarning(Base):
    __tablename__ = "node_earnings"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id", ondelete="CASCADE"))
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Float, default=0.0)
    duration_hours = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    currency = Column(String, default="INR")

    node = relationship("GPUNode", back_populates="earnings")


# ---------- WALLET TRANSACTIONS ----------
class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


# ---------- GPU EXECUTION LOG ----------
class GPUExecutionLog(Base):
    __tablename__ = "gpu_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    log_type = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="execution_logs")
