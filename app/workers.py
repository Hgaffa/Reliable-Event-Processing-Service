import time, datetime, random, logging
from sqlalchemy.orm import Session
from sqlalchemy import asc
from app.db import SessionLocal
from app.models import Job
from app.schemas import JobStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def execute_job(job: Job, db: Session):
    """Route job to appropriate handler based on type"""
    
    handlers = {
        "send_email": handle_send_email,
        "process_data": handle_process_data,
        "test_failure": handle_always_fail
    }
    
    handler = handlers.get(job.type)
    if not handler:
        raise ValueError(f"Unknown job type: {job.type}")
    
    result = handler(job.payload)
    return result

def handle_send_email(payload: dict):
    """Simulate sending an email"""
    time.sleep(2)
    if random.random() < 0.2:
        raise Exception("Email service temporarily unavailable")
    
    return {"sent_to": payload.get("to"), "status": "sent"}

def handle_process_data(payload: dict):
    """Simulate processing data"""
    time.sleep(2)
    if random.random() < 0.2:
        raise Exception("Process data service temporarily unavailable")
    
    return {"data": payload.get("data"), "status": "processed"}

def handle_always_fail(payload: dict):
    """Always fails - for testing retry logic"""
    time.sleep(1)
    raise Exception("This job is designed to fail")    

def process_next_job(db: Session):
    """Fetch and process a pending job from db"""
    job: Job = db.query(Job).filter(Job.status == JobStatus.PENDING).order_by(asc(Job.created_at)).first()
    
    if (job):
        logger.info(f"Processing job {job.id} (type: {job.type})")
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.datetime.now()
        db.commit()
    else:
        logger.info("No new jobs found...")
        return

    try:
        result = execute_job(job, db)
        logger.info(f"Job {job.id} completed successfully")

        # Success
        job.status = JobStatus.COMPLETED
        job.result = result
        job.finished_at = datetime.datetime.now()
    
    except Exception as e:
        logger.error(f"Job {job.id} failed: {str(e)}")
        job.attempts += 1
        
        if job.attempts >= job.max_attempts:
            # No more retries
            logger.error(f"Job {job.id} has failed and has exceeded the max attempts: {job.max_attempts}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.finished_at = datetime.datetime.now()
        else:
            # Retry
            logger.info(f"Job {job.id} will retry (attempt {job.attempts}/{job.max_attempts})")
            job.status = JobStatus.PENDING
            job.error_message = f"Attempt {job.attempts} failed: {str(e)}"
    
    finally:
        job.updated_at = datetime.datetime.now()
        db.commit()
    
        

def recover_stuck_jobs(db: Session):
    """On startup, reset PROCESSING jobs to PENDING (crash recovery)"""
    stuck_jobs = db.query(Job).filter(Job.status == JobStatus.PROCESSING).all()
    count = len(stuck_jobs)
    
    if count > 0:
        logger.warning(f"Recovered {count} stuck jobs from previous crash")
        db.query(Job).filter(Job.status == JobStatus.PROCESSING).update({
            "status": JobStatus.PENDING
        })
        db.commit()
    else:
        logger.info("No stuck jobs found - clean startup")
    
def worker_loop():
    """Main worker loop that polls the db for jobs"""
    db = SessionLocal()
    
    try:
        # Crash recovery
        recover_stuck_jobs(db)
        
        # Process loop
        while True:
            process_next_job(db)
            time.sleep(1) # Poll every second
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Worker starting...")
    worker_loop()