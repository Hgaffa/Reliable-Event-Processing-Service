from fastapi import FastAPI, HTTPException, BackgroundTasks
from app.schemas import JobCreateRequest, JobResponse, JobStatus, JobListResponse
from app.utils import build_job_response
from typing import Dict, Optional

import random, time, datetime

# Defines valid job transitions - To be able to move to a status that is a key in the dictionary, the current status must be equal to validJobTransitions[key]
validJobTransitions = {
    JobStatus.PROCESSING: JobStatus.PENDING,
    JobStatus.COMPLETED: JobStatus.PROCESSING,
    JobStatus.FAILED: JobStatus.PROCESSING
}

# Temporary memory store
jobs: Dict[int, dict] = {}
job_counter = 1

app = FastAPI()


def process_job(job_id: int):
    """
    Simulates doing work on a job.
    This represents a background worker and will be moved to a separate service when we implement a real worker.
    """
    try:
        jobs[job_id]["status"] = JobStatus.PROCESSING
        
        # Simulate work
        time.sleep(random.randint(2,5))
        
        # Simulate success or failure
        if random.random() < 0.8:
            jobs[job_id]["status"] = JobStatus.COMPLETED
            jobs[job_id]["result"] = {
                "message": "Job completed successfully"
            }
        else:
            jobs[job_id]["status"] = JobStatus.FAILED
            jobs[job_id]["result"] = {
                "message": "Job failed during worker execution"
            }
    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["result"] = { "error": str(e) }
    
    jobs[job_id]["attempts"] += 1    

@app.get("/health")
def health():
    return { "status": "ok" }

@app.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreateRequest, background_tasks: BackgroundTasks):
    global job_counter
    
    job_id = job_counter
    job_counter += 1
    
    currentTime = datetime.datetime.now()
    
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "created_at": currentTime.isoformat(),
        "updated_at": currentTime.isoformat(),
        "started_at": None,
        "finished_at": None,
        "payload": job.payload,
        "error_message": None,
        "attempts": 0,
        "result": None,
        "type": job.type
    }
    
    background_tasks.add_task(process_job, job_id)
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=currentTime.isoformat(),
        updated_at=currentTime.isoformat(),
        started_at=None,
        finished_at=None,
        payload=job.payload,
        error_message=None,
        attempts=0,
        result=None,
        type=job.type
    )

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    job = jobs.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return build_job_response(job_id, job)

@app.get("/jobs", response_model=JobListResponse)
# Status is an optional query parameter as opposed to a URL parameter to allow users to query all jobs without status filtering
def get_jobs(status: Optional[JobStatus] = None):
    # By utilising a list comprehension and the pydantic model 'JobResponse' we can format the jobs we have saved quite easily (may need to be updated when data stores in DB and not in memory)
    jobList = [
        build_job_response(job_id, job)
        for job_id, job in jobs.items()
        if status is None or job["status"] == status
    ]
    
    return JobListResponse(jobs=jobList)