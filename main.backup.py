from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import Base, engine, get_db
from models import GPUNode, User
from schemas import GPUNodeCreate, GPUNodeResponse, UserCreate, UserResponse, LoginSchema
from auth_utils import hash_password
from auth_jwt import get_current_user, create_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_pwd, hashed_pwd):
    return pwd_context.verify(plain_pwd, hashed_pwd)

@app.get("/")
def root():
    return {"message": "API is running 🚀"}

# ---------------------- GPU NODE ROUTES ----------------------
@app.post("/gpu-nodes", response_model=GPUNodeResponse, tags=["GPU"])
def create_gpu_node(data: GPUNodeCreate, db: Session = Depends(get_db)):
    new_node = GPUNode(
        Owner_name=data.Owner_name,
        location=data.location,
        gpu_model=data.gpu_model,
        gpu_count=data.gpu_count
    )
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node

@app.get("/gpu-nodes", response_model=list[GPUNodeResponse], tags=["GPU"])
def get_gpu_nodes(db: Session = Depends(get_db)):
    return db.query(GPUNode).all()

# ---------------------- AUTH (SIGNUP) ROUTE ----------------------
@app.post("/signup", response_model=UserResponse, tags=["Auth"])
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# ---------------------- AUTH (LOGIN) ROUTE ----------------------
@app.post("/login", tags=["Auth"], response_model=None)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid Email or Password")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid Email or Password")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}
@app.get("/me", tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }
