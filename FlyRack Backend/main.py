import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from typing import Optional

# Force load_dotenv to reload updated environment variables from disk
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Auth Login & Protect API")
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
        # Verify the JWT token with Supabase Auth
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

# --- STAGE 1: SIGNUP & LOGIN ---

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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

# --- STAGE 2: PROTECTED PROFILE ---

@app.get("/protected/profile")
def get_profile(current_user=Depends(get_current_user)):
    return {
        "message": "Welcome to your protected profile!",
        "user_id": current_user.id,
        "email": current_user.email
    }

# --- STAGE 3: USER-SPECIFIC TASK CRUD ---

# 1. CREATE TASK
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

# 2. READ ALL TASKS FOR CURRENT USER
@app.get("/tasks")
def get_user_tasks(current_user=Depends(get_current_user)):
    try:
        response = supabase.table("tasks") \
            .select("*") \
            .eq("user_id", current_user.id) \
            .execute()
            
        return {"tasks": response.data}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# 3. UPDATE TASK
@app.patch("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, current_user=Depends(get_current_user)):
    try:
        update_data = {k: v for k, v in task.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided to update")

        response = supabase.table("tasks") \
            .update(update_data) \
            .eq("id", task_id) \
            .eq("user_id", current_user.id) \
            .execute()

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or unauthorized")

        return {"message": "Task updated successfully", "task": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# 4. DELETE TASK
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user=Depends(get_current_user)):
    try:
        response = supabase.table("tasks") \
            .delete() \
            .eq("id", task_id) \
            .eq("user_id", current_user.id) \
            .execute()

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or unauthorized")

        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))