# RAG-Engine-Service

Welcome to the core backend AI orchestrator for managing Retrieval-Augmented Generation (RAG). 

For a deep dive into the architecture, edge cases, and tech stack, please read the [SERVICE_DOCUMENTATION.md](./SERVICE_DOCUMENTATION.md).

---

## Prerequisites
- **Python 3.13** (via Conda recommended)
- **Docker & Docker Compose** (for Redis and PostgreSQL)
- **UV** package manager
- **API Keys**: Google Gemini API Key & GCP Service Account credentials (for Cloud Storage)

---

## Setup & Installation (Manual Development Mode)

### 1. Set up Environment Configuration
Create a `.env` file in the root directory (use a provided template if available) and configure your database, Redis, GCP, and Gemini credentials.

### 2. Create and Activate Conda Environment
```bash
conda create -n rag-env python=3.13 uv -c conda-forge
conda activate rag-env
```

### 3. Install Dependencies
```bash
cd src
uv pip install -r requirements.txt
```

### 4. Rename .env.example to .env and put all variables in it
```bash
cp .env.example .env
```

### 5. Start Infrastructure (Database & Redis)
Note: create your own `docker-compose.yml` for backing services (redis, postgresql) in the `docker/` folder:
```bash
docker-compose up -d postgres redis
```

### 6. Start the FastAPI App
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 7. Start the Celery Worker
In a separate terminal (with the conda env activated):
```bash
cd src
celery -A celery_tasks.tasks worker --loglevel=info --pool=solo
```

---

## Database Migrations (Alembic)

Before running the app for the first time, you must initialize the database schema and enable `pgvector`.

### Go to the DB folder
```bash
cd src/models
```

### Init Alembic (if not already initialized)
```bash
alembic init -t async migrations
```

### Generate a new migration revision
```bash
alembic revision --autogenerate -m "Initial schema"
```

### ⚠️ CRITICAL: Enable pgvector manually
Open the newly generated migration file in `src/models/migrations/versions/` and add these lines at the top of the `upgrade()` and `downgrade()` functions respectively:

```python
# In upgrade():
op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

# In downgrade():
op.execute('DROP EXTENSION IF EXISTS vector;')
```

### Apply changes to DB
```bash
alembic upgrade head
```

---

## Docker Containerization (Run Entire Stack Locally)

If you want to run the entire service (API, Celery, Redis, Postgres) locally via Docker without manual setup:

### Build and Run All Containers
```bash
docker-compose up --build -d
```
This will read your `Dockerfile` and `docker-compose.yml` to spin up the local environment automatically.

---

## API Usage Example

### Upload files using curl
```bash
curl.exe -X POST "http://localhost:5000/api/v1/documents_upload/company_id/container_id" `
-H "accept: application/json" `
-F "files=@file1.txt;type=text/plain" `
-F "files=@file2.pdf;type=application/pdf" `
-F "files=@file3.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```
