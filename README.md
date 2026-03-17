# AI ORCHESTRATOR SERVICE

## SET UP ENV

### Create conda env
```bash
conda create -n rag-env python=3.13 uv -c conda-forge
```

### Activate conda env
```bash
conda activate rag-env
```

### Install dependancies
```bash
cd src
uv pip install -r requirements.txt
```

## START APP
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

## START CELERY
```bash
celery -A celery_tasks.tasks worker --loglevel=info --pool=solo
```

## Upload files using curl
```bash
curl.exe -X POST "http://127.0.0.1:8000/api/v1/documents_upload/company_id/container_id" `
>> -H "accept: application/json" `
>> -F "files=@techcorp_policies.txt;type=text/plain"
```

## SETUP ALEMBIC

### Go to db folder
```bash
cd .\models
```
### Init alembic
```bash
alembic init -t async migrations
```

### Revesion code with alembic
```bash
alembic revision --autogenerate -m "commit message here"
```

### Aplly changes to DB
```bash
alembic upgrade head
```

### Use this in megration files
```python
op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
op.execute('DROP EXTENSION IF EXISTS vector;')
```


--------------------------------------------------
--------------------------------------------------
--------------------------------------------------

# Deployment 

## Containerize Project

### Build Image

### Run app contaier locally and connect with Redis, PostgreSQL (they run on Docker-compose)


## Database Setup

### Step 1: Create Instance on Cloud SQL
This usually takes about 5 to 10 minutes

### Step 2: Create Your App's Database and Dedicated User for this database
Once the instance finishes spinning up, we need to create the specific database inside it.
- Make Database name match your .env file and create.
- Make User name match you .env file and also here put password for this user to use you DB

### Step 3: Install the Cloud SQL Auth Proxy (The Secure Bridge)
Cloud SQL Auth Proxy tool acts just like the SSH Tunnel we use for connecting with our remote DB.

1. Download the Auth Proxy for Windows directly from Google: Download [[cloud-sql-proxy-x64.exe](https://www.google.com/search?q=https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.0/cloud-sql-proxy-x64.exe)]

2. Rename the downloaded file to cloud-sql-proxy.exe and move it into the root folder of your project.

3. Find your Instance Connection Name: Go back to the GCP Console -> SQL -> Overview tab. Look for the "Connection name" (it will look like project-id:region:instance-name).

### Step 4: Run the Proxy Bridge
Open a new PowerShell terminal in your project root and run this command (replace with your exact connection name):
```bash
.\cloud-sql-proxy.exe your-project-id:your-region:your-instance-name --port 5432
```
Leave this terminal open! The encrypted bridge to Google Cloud is now active.

## Step 5: Update .env and Run Alembic
- Update Database configuration in your .env file
```bash
db_user=your-user-name
db_password=YourNewUserPasswordHere
db_name=DB-name
```
- Run your Alembic migrations
```bash
alembic upgrade head
```