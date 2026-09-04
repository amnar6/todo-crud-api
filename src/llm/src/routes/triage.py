import os
from fastapi import APIRouter, HTTPException, status
from src.llm.schema import TaskTriageRequest, TaskTriageResponse, TaskCategory, TaskPriority

router = APIRouter(prefix="/tasks", tags=["AI Triage"])


@router.post(
    "/triage",
    response_model=TaskTriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify and triage task description"
)
async def triage_task(request: TaskTriageRequest):
    # STUB MODE: If LLM_STUB=1, return hard-coded valid response without calling model
    if os.getenv("LLM_STUB", "0") == "1":
        return TaskTriageResponse(
            category=TaskCategory.WORK,
            priority=TaskPriority.NORMAL,
            estimated_minutes=30,
            confidence=0.95,
            reason="Stub mode: Pre-computed response satisfying output schema."
        )

    # Real LLM integration placeholder (Stages 2 & 3)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Model call will be connected in Stage 2."
    )