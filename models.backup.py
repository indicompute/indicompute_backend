from sqlalchemy import Column, Integer, String
from database import Base

class GPUNode(Base):
    __tablename__ = "gpu_nodes"

    id = Column(Integer, primary_key=True, index=True)
    Owner_name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    gpu_model = Column(String, nullable=False)
    gpu_count = Column(Integer, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
