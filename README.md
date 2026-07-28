# Task Management CRUD API (SQLite Persistence)

A lightweight RESTful API built with Python and FastAPI that manages a to do list backed by a SQLite database (`tasks.db`). Features interactive OpenAPI (Swagger UI) documentation, input validation, and full data persistence across server restarts.


## Why SQLite?

SQLite was chosen as the database layer because:
* **Zero Configuration:** It runs serverless directly from a single local file (`tasks.db`).
* **Persistence:** Data survives server restarts without needing external database service setups.
* **Auto-Initialization:** The application automatically creates the database file, builds the table schema, and seeds default data on its first run[cite: 2].


## How to Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/amnar6/todo-crud-api.git](https://github.com/amnar6/todo-crud-api.git)
   cd todo-crud-api