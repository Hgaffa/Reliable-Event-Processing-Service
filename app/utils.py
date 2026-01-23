'''
Utility class containing helper functions for procesing and formatting job data
'''
from app.schemas import JobResponse

def build_job_response(job_id: int, job: dict) -> JobResponse:
    return JobResponse(
        job_id=job_id,
        type=job["type"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        started_at=job["started_at"],
        finished_at=job["finished_at"],
        error_message=job["error_message"] or "No errors",
        attempts=job["attempts"],
        result=job["result"],
    )
