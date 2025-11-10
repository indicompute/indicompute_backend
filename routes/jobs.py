from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import Job, GPUNode
from schemas import JobCreate, JobResponse
from auth import get_current_user
from models import User

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)

# 🧩 Create a new Job
@router.post("/", response_model=JobResponse)
def create_job(data: JobCreate,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == data.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="GPU Node not found")

    new_job = Job(
        user_id=current_user.id,
        node_id=node.id,
        command=data.command,
        status="running",
        result=f"Job '{data.command}' is running."
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


# 🧩 Get All Jobs (for logged-in user)
@router.get("/", response_model=List[JobResponse])
def get_jobs(current_user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
    return jobs


# 🧩 Get Single Job by ID
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# 🧩 Delete Job
@router.delete("/{job_id}")
def delete_job(job_id: int,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"detail": "Job deleted successfully"}


# 🧩 Submit Job (for Node)
@router.post("/submit-job", response_model=JobResponse)
def submit_job(job: JobCreate,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    node = db.query(GPUNode).filter(GPUNode.id == job.node_id, GPUNode.node_key == job.node_key).first()
    if not node:
        raise HTTPException(403, "Invalid node credentials")

    new_job = Job(
        user_id=current_user.id,
        node_id=node.id,
        command=job.command,
        status="running",
        result=f"Job '{job.command}' started on GPU Node {node.id}"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


# 🧩 Get Job Status
@router.get("/job-status/{job_id}", response_model=JobResponse)
def job_status(job_id: int,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# 🧩 Mark Job Complete ✅
@router.post("/job/complete", response_model=JobResponse)
def mark_job_complete(job_id: int,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    job.status = "completed"
    job.result = f"✅ Job '{job.command}' completed successfully at {datetime.utcnow()}."
    db.commit()
    db.refresh(job)
    return job
