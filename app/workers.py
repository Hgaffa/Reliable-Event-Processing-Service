"""Worker functions for background job processing."""
import time
import datetime
import random
import logging
import os
from dotenv import load_dotenv

from prometheus_client import start_http_server

from sqlalchemy.orm import Session
from sqlalchemy import asc, or_

from app.db import SESSIONLOCAL
from app.models import Job
from app.schemas import JobStatus
from app.metrics import (
    jobs_completed_counter,
    jobs_failed_counter,
    jobs_retried_counter,
    job_duration_histogram,
    job_queue_wait_histogram,
    jobs_pending_gauge,
    jobs_processing_gauge,
    worker_up_gauge
)

load_dotenv()
WORKER_METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "8001"))

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

    current_time = datetime.datetime.now(datetime.timezone.utc)

    job: Job = db.query(Job).filter(
        Job.status == JobStatus.PENDING,
        or_(
            Job.scheduled_at.is_(None),           # Not scheduled - process now
            Job.scheduled_at <= current_time      # Scheduled time arrived
        )
    ).order_by(
        asc(Job.priority),
        asc(Job.created_at)
    ).first()

    if job:
        # Calculate wait time for metrics
        queue_wait_seconds = (current_time - job.created_at).total_seconds()
        job_queue_wait_histogram.labels(
            job_type=job.type).observe(queue_wait_seconds)

        logger.info(
            f"Processing job {job.id} (type: {job.type}, priority: {job.priority}, waited: {queue_wait_seconds:.2f}s)")
        if job.scheduled_at:
            logger.info(
                f"Job was scheduled for {job.scheduled_at.isoformat()}")

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.datetime.now()
        db.commit()

        # Start timing the job
        start_time = time.time()
    else:
        logger.info("No jobs ready to process...")
        return

    try:
        result = execute_job(job, db)
        duration = time.time() - start_time

        logger.info(f"Job {job.id} completed successfully in {duration:.2f}s")

        # Success - record metrics
        job.status = JobStatus.COMPLETED
        job.result = result
        job.finished_at = datetime.datetime.now()

        jobs_completed_counter.labels(job_type=job.type).inc()
        job_duration_histogram.labels(job_type=job.type).observe(duration)

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Job {job.id} failed after {duration:.2f}s: {str(e)}")

        job.attempts += 1

        if job.attempts >= job.max_attempts:
            # No more retries
            logger.error(
                f"Job {job.id} has failed and has exceeded the max attempts: {job.max_attempts}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.finished_at = datetime.datetime.now()

            jobs_failed_counter.labels(job_type=job.type).inc()
            job_duration_histogram.labels(job_type=job.type).observe(duration)
        else:
            # Retry
            logger.info(
                f"Job {job.id} will retry (attempt {job.attempts}/{job.max_attempts})")
            job.status = JobStatus.PENDING
            job.error_message = f"Attempt {job.attempts} failed: {str(e)}"

            jobs_retried_counter.labels(job_type=job.type).inc()

    finally:
        job.updated_at = datetime.datetime.now()
        db.commit()


def update_state_gauges(db: Session):
    """Update gauge metrics with current job counts"""
    pending_count = db.query(Job).filter(
        Job.status == JobStatus.PENDING).count()
    processing_count = db.query(Job).filter(
        Job.status == JobStatus.PROCESSING).count()

    jobs_pending_gauge.set(pending_count)
    jobs_processing_gauge.set(processing_count)


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
    db = SESSIONLOCAL()

    try:
        # Start metrics server in background thread
        logger.info(
            f"Starting metrics server on port {WORKER_METRICS_PORT}...")
        start_http_server(WORKER_METRICS_PORT)

        # Wait for database to be ready with retries
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Crash recovery
                recover_stuck_jobs(db)
                logger.info("Database connection established")
                break
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Database not ready (attempt {retry_count}/{max_retries}): {e}")
                if retry_count >= max_retries:
                    logger.error(
                        "Failed to connect to database after max retries")
                    raise
                time.sleep(2)  # Wait 2 seconds before retry

        # Mark worker as up
        worker_up_gauge.set(1)

        # Process loop
        while True:
            process_next_job(db)
            update_state_gauges(db)
            time.sleep(1)  # Poll every second

    except KeyboardInterrupt:
        logger.info("Worker shutting down gracefully...")
        worker_up_gauge.set(0)

    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Worker starting...")
    worker_loop()
