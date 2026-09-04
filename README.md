# 10x Task Management & AI Triage API

A comprehensive, scalable backend system built with Python and FastAPI. The project features full CRUD task management with flexible persistence options (local SQLite and cloud Supabase PostgreSQL), robust JWT authentication, and an asynchronous AI task-triage pipeline powered by OpenRouter and background worker queues.

---

## Architecture & Database Options

The project supports two persistence layers:
1. **Local SQLite (`tasks.db`)**: Lightweight, zero config, serverless persistence ideal for rapid local development, offline runs, and isolated unit testing.
2. **Cloud PostgreSQL (Supabase)**: Production grade cloud persistence with built in relational integrity, remote access, and integrated user identity management.

---

## 5 Concepts Implemented

| # | Concept | Implementation Location | Description |
|---|---|---|---|
| 1 | **API Endpoints** | `FlyRack Backend/main.py` | FastAPI REST endpoints (`/tasks`, `/auth/*`, `/tasks/triage/*`) with Pydantic schema validation. |
| 2 | **Database** | Supabase PostgreSQL / Local SQLite | Persistent task storage that survives server restarts. |
| 3 | **Authentication** | `FlyRack Backend/main.py` | JWT token validation and protected routes via `get_current_user` dependency. |
| 4 | **LLM Integration** | `FlyRack Backend/main.py` | OpenRouter client executing structured prompt classification with JSON parsing. |
| 5 | **Background Jobs** | `FlyRack Backend/main.py` | FastAPI `BackgroundTasks` returning an immediate `202 Accepted` with polling status endpoints (`/tasks/triage/jobs/{job_id}`). |

---

## How to Run

### 1. Clone the Repository
```bash
git clone [https://github.com/amnar6/todo-crud-api.git](https://github.com/amnar6/todo-crud-api.git)
cd todo-crud-api