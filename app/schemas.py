from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobCreateRequest(BaseModel):
    type: str
    idempotency_key: str
    payload: Dict[str, Any]
    priority: Optional[int] = 5
    scheduled_at: Optional[str] = None


class JobResponse(BaseModel):
    job_id: int
    type: str
    idempotency_key: str
    status: JobStatus
    priority: int
    payload: Dict[str, Any]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    scheduled_at: Optional[str]
    error_message: Optional[str]
    attempts: int
    result: Optional[Any] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
