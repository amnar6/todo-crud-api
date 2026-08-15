from enum import Enum
from pydantic import BaseModel, Field


class TaskCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    HEALTH = "health"
    URGENT = "urgent"
    OTHER = "other"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


# Input validation model (Rejects invalid payloads before LLM call)
class TaskTriageRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The task or issue description to classify."
    )


# Output contract model (Enforces typed JSON)
class TaskTriageResponse(BaseModel):
    category: TaskCategory
    priority: TaskPriority
    estimated_minutes: int = Field(..., ge=1, le=480)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=200)