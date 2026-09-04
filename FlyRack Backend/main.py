import os
import json
import re
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from enum import Enum
from supabase import create_client, Client
from typing import Optional, Dict, Any
from openai import OpenAI

# Load environment variables
load_dotenv(override=True)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

# --- SUPABASE INIT ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://placeholder.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "placeholder-key")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# --- OPENROUTER / LLM CLIENT INIT ---
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")

llm_client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)

TRIAGE_SYSTEM_PROMPT = """You are an automated task classification system.
Analyze the user's task description and return a strictly valid JSON object matching this schema:
{
  "category": "work" | "personal" | "finance" | "health" | "urgent" | "other",
  "priority": "low" | "normal" | "high",
  "estimated_minutes": integer between 1 and 480,
  "confidence": float between 0.0 and 1.0,
  "reason": "one concise sentence explaining the classification"
}

Strict Rules:
- You must output ONLY raw JSON. No markdown backticks (```json), no explanations, no conversational text before or after.
- The "category" MUST be one of: ["work", "personal", "finance", "health", "urgent", "other"].
- The "priority" MUST be one of: ["low", "normal", "high"].
- If ambiguous, unclear, or insufficient detail: set category to "other", confidence < 0.5, and priority to "normal".
"""

app = FastAPI(title="Auth Login & Task Triage API")
security = HTTPBearer()

# --- REQUEST SCHEMAS ---

class AuthCredentials(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

# --- AI TRIAGE SCHEMAS ---

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

class TaskTriageRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The task or issue description to classify."
    )

class TaskTriageResponse(BaseModel):
    category: TaskCategory
    priority: TaskPriority
    estimated_minutes: int = Field(..., ge=1, le=480)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=200)

# --- JOB QUEUE SCHEMAS ---

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[TaskTriageResponse] = None
    error: Optional[str] = None
    retries: int = 0

# In-memory store for tracking background jobs
jobs_db: Dict[str, Dict[str, Any]] = {}

# --- EVENTS & PUBLIC ENDPOINTS ---

@app.on_event("startup")
def startup_event():
    print("Server running and connected to Supabase")

@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

# --- AUTH DEPENDENCY ---

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        if supabase is None:
            raise Exception("Supabase client not initialized")
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return user_response.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# --- AUTH ROUTES ---

@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(credentials: AuthCredentials):
    if not credentials.email.strip() or not credentials.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    try:
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed. Please check credentials."
            )
        return {
            "message": "User created successfully",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/auth/login", status_code=status.HTTP_200_OK)
def login(credentials: AuthCredentials):
    if not credentials.email.strip() or not credentials.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials"
            )
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials"
        )

# --- PROTECTED PROFILE ---

@app.get("/protected/profile")
def get_profile(current_user=Depends(get_current_user)):
    return {
        "message": "Welcome to your protected profile!",
        "user_id": current_user.id,
        "email": current_user.email
    }

# --- TASK CRUD ---

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, current_user=Depends(get_current_user)):
    try:
        response = supabase.table("tasks").insert({
            "title": task.title,
            "description": task.description,
            "user_id": current_user.id
        }).execute()
        return {"message": "Task created successfully", "task": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/tasks")
def get_user_tasks(current_user=Depends(get_current_user)):
    try:
        response = supabase.table("tasks").select("*").eq("user_id", current_user.id).execute()
        return {"tasks": response.data}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, current_user=Depends(get_current_user)):
    try:
        update_data = {k: v for k, v in task.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided to update")

        response = supabase.table("tasks").update(update_data).eq("id", task_id).eq("user_id", current_user.id).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or unauthorized")

        return {"message": "Task updated successfully", "task": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user=Depends(get_current_user)):
    try:
        response = supabase.table("tasks").delete().eq("id", task_id).eq("user_id", current_user.id).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or unauthorized")

        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- BACKGROUND WORKER FUNCTION ---

def process_triage_job(job_id: str, description: str, max_retries: int = 3):
    """Background worker executing the LLM inference with retry/backoff."""
    job = jobs_db.get(job_id)
    if not job:
        return

    job["status"] = JobStatus.PROCESSING

    # Stub mode check
    if os.getenv("LLM_STUB", "0") == "1":
        job["status"] = JobStatus.COMPLETED
        job["result"] = TaskTriageResponse(
            category=TaskCategory.WORK,
            priority=TaskPriority.NORMAL,
            estimated_minutes=30,
            confidence=0.95,
            reason="Stub mode: Pre-computed response satisfying output schema."
        )
        job["completed_at"] = datetime.utcnow().isoformat()
        return

    for attempt in range(max_retries):
        try:
            job["retries"] = attempt
            completion = llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": description}
                ],
                temperature=0.1
            )
            raw_content = completion.choices[0].message.content.strip()

            # Robust JSON extraction: match the first '{' to the last '}'
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            data = json.loads(json_str)

            job["status"] = JobStatus.COMPLETED
            job["result"] = TaskTriageResponse(**data)
            job["completed_at"] = datetime.utcnow().isoformat()
            return

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                job["status"] = JobStatus.FAILED
                job["error"] = f"Failed after {max_retries} attempts: {str(e)}"
                job["completed_at"] = datetime.utcnow().isoformat()
                print(f"[ALERT] Background job {job_id} failed: {str(e)}")

# --- ASYNC AI TRIAGE ENDPOINTS (CONCEPT 5: BACKGROUND JOBS) ---

@app.post("/tasks/triage/async", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def triage_task_async(request: TaskTriageRequest, background_tasks: BackgroundTasks):
    """Producer: Enqueue a task triage job and return 202 Accepted immediately."""
    job_id = str(uuid.uuid4())
    job_record = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None,
        "retries": 0
    }
    jobs_db[job_id] = job_record

    background_tasks.add_task(process_triage_job, job_id, request.description)
    return job_record

@app.get("/tasks/triage/jobs/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_triage_job_status(job_id: str):
    """Consumer/Poller: Check the status and results of a background triage job."""
    job = jobs_db.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job