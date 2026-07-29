import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

# Load variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# Pydantic models for request validation
class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

def get_db_connection():
    # dict_row returns database rows as Python dictionaries
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create tasks table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                );
            """)
            
            # Seed 3 default tasks ONLY if the table is empty
            cur.execute("SELECT COUNT(*) FROM tasks;")
            count = cur.fetchone()["count"]
            if count == 0:
                cur.execute("""
                    INSERT INTO tasks (title, done) VALUES 
                    (%s, %s),
                    (%s, %s),
                    (%s, %s);
                """, (
                    "Complete Backend Internship Task", True,
                    "Connect FastAPI CRUD API to Postgres", False,
                    "Explore database in Docker Container", False
                ))
            conn.commit()

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# --- ENDPOINTS ---

@app.get("/tasks")
def get_tasks():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
            return cur.fetchall()

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s;", (task_id,))
            task = cur.fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done;",
                (task.title, False)
            )
            new_task = cur.fetchone()
            conn.commit()
            return new_task

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_update: TaskUpdate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s;", (task_id,))
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Task not found")
            
            new_title = task_update.title if task_update.title is not None else existing["title"]
            new_done = task_update.done if task_update.done is not None else existing["done"]
            
            cur.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done;",
                (new_title, new_done, task_id)
            )
            updated_task = cur.fetchone()
            conn.commit()
            return updated_task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id;", (task_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="Task not found")
            conn.commit()
            return None