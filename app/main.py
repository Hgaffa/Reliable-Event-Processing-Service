from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas import JobCreateRequest, JobResponse, JobStatus, JobListResponse
from app.db import Base, engine, get_db
from app.models import Job
from app.utils import build_job_response
from typing import Optional
import datetime

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/health")
def health():
    """Health check endpoint to verify service is running"""
    return { "status": "ok" }

@app.post("/jobs", response_model=JobResponse)
def create_job(
    job_request: JobCreateRequest, 
    db: Session = Depends(get_db)):
    """
    Create a new job with idempotency support.
    
    If a job with the same idempotency_key already exists, returns that job instead of creating a new one.
    This ensures that retrying the same request doesn't create duplicate jobs.
    """
    
    # Check if job with this idempotency key exists
    existing_job = db.query(Job).filter(
        Job.idempotency_key == job_request.idempotency_key
    ).first()
    
    if existing_job:
        # Return existing job
        return build_job_response(existing_job)

    # Otherwise, create a new job
    current_time = datetime.datetime.now()
    
    new_job = Job(
        idempotency_key=job_request.idempotency_key,
        type=job_request.type,
        payload=job_request.payload,
        status=JobStatus.PENDING,
        attempts=0,
        max_attempts=3,
        created_at=current_time,
        updated_at=current_time
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job) # Gets a new auto-generated ID
    
    return build_job_response(new_job)

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get the status and details of a specific job by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return build_job_response(job)

@app.get("/jobs", response_model=JobListResponse)
# Status is an optional query parameter as opposed to a URL parameter to allow users to query all jobs without status filtering
def get_jobs(
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db)):
    """
    List all jobs, optionally filtered by status.
    
    Query parameters:
    - status: Filter jobs by status (PENDING, PROCESSING, COMPLETED, FAILED)
    """
    query = db.query(Job)
    
    if status is not None:
        query = query.filter(Job.status == status)
    
    jobs = query.all()
    
    # Conver to response format
    job_list = [build_job_response(job) for job in jobs]
    
    return JobListResponse(jobs=job_list)