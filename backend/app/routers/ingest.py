"""Ingestion endpoints. Ingestion runs asynchronously in a background task so
the request returns immediately with a job id the client can poll."""
from __future__ import annotations

import uuid
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..ingestion.pipeline import ingest_documents
from ..models.schemas import (
    DocumentInput,
    IngestRequest,
    IngestResponse,
    JobStatus,
)

router = APIRouter(tags=["ingestion"])

# In-memory job registry. For production this would be Redis / a DB.
_JOBS: Dict[str, JobStatus] = {}


def _run_job(job_id: str, documents: List[DocumentInput]) -> None:
    status = _JOBS[job_id]
    status.status = "running"
    try:
        ingest_documents(documents, status)
    except Exception as exc:  # noqa: BLE001
        status.status = "failed"
        status.error = str(exc)


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = JobStatus(job_id=job_id, status="pending")
    background_tasks.add_task(_run_job, job_id, req.documents)
    return IngestResponse(
        job_id=job_id, status="pending", document_count=len(req.documents)
    )


@router.get("/ingest/{job_id}", response_model=JobStatus)
async def ingest_status(job_id: str) -> JobStatus:
    status = _JOBS.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
