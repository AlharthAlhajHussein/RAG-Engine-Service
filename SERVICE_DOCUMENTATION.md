# RAG-Engine-Service: Architecture & Developer Guide

## 1. Overview & Purpose
The **RAG-Engine-Service** is the core backend AI orchestrator for managing Retrieval-Augmented Generation (RAG). Its primary responsibility is to ingest documents, break them into searchable vector chunks, store them efficiently, and perform lightning-fast semantic searches against user queries.

This service operates entirely headlessly (via API) and utilizes a combination of asynchronous API endpoints and background task workers to ensure heavy AI processing doesn't block the user experience.

---

## 2. Core Technologies & Stack
* **Web Framework:** **FastAPI** (Python 3.13) - Chosen for its high performance and native asynchronous support.
* **Database:** **PostgreSQL** with the **`pgvector`** extension - Used for storing 768-dimensional embeddings and performing HNSW (Hierarchical Navigable Small World) similarity searches.
* **ORM & Migrations:** **SQLAlchemy** (using Async and Sync sessions) and **Alembic** for automated database schema migrations.
* **AI & Embeddings:** **Google GenAI SDK (Gemini)** - Used for generating embeddings for both raw document chunks and user search queries.
* **Background Processing:** **Celery** backed by a **Redis** message broker - Offloads the heavy lifting of document downloading, extracting, chunking, and embedding.
* **Cloud Storage:** **Google Cloud Storage (GCP Bucket)** - Safely houses the raw uploaded files in a scalable directory structure.
* **Deployment & CI/CD:** **Docker & Docker Compose**, built and pushed via **GitHub Actions** to **Google Artifact Registry (GAR)**. The API runs on **Google Cloud Run**, and the Celery worker runs on a **Compute Engine VM**.

---

## 3. Core Workflows (How it Works)

### A. Container Management (`/containers`)
* **Concept:** Data is segregated logically into "Knowledge Containers" tied to a specific `company_id`.
* **Flow:** A user creates a container. The system generates a unique UUID, and returns it. This UUID acts as the namespace for future document uploads.

### B. Document Ingestion Pipeline (`/documents_upload` -> Celery)
* **Step 1: Fast API Acceptance:** The user uploads multiple files. The API immediately streams these files directly to a GCP Bucket (preventing RAM bloat on the server).
* **Step 2: Database Registry:** A `DocumentAsset` record is created with a `pending` status. If a document with the same name already exists in the container, the old document and its vector chunks are safely deleted first.
* **Step 3: Background Offload:** A Celery task (`process_and_embed_document`) is triggered, and the API instantly returns a `202 Accepted` response.
* **Step 4: The Worker Pipeline (Celery):**
  1. **Download:** The worker pulls the file from GCP to a temporary local path.
  2. **Extraction & Chunking:** Text is extracted from the file (PDF, DOCX, TXT) and split into manageable chunks.
  3. **Embedding:** Chunks are sent to the Gemini API in batches of 50 to generate 768-dimensional vector arrays. 
  4. **Database Insertion:** The embeddings and chunk metadata are bulk-saved into the `VectorChunk` table.
  5. **Cleanup:** Temporary files are deleted, and the document status is updated to `completed`.

### C. Semantic Search Retrieval (`/search`)
* **Step 1: Security Check:** Validates that the requested container actually belongs to the provided `company_id`.
* **Step 2: Query Embedding:** The user's text query is embedded using Gemini (specifically tagged with `task_type="RETRIEVAL_QUERY"` to optimize Google's embedding space for questions).
* **Step 3: Vector Search:** Executes a heavily optimized Cosine Distance (`<=>`) query against the `VectorChunk` table to find the closest matches.
* **Step 4: Quality Filtering:** Any chunk with a similarity score below a threshold (e.g., `< 0.2`) is discarded to prevent AI hallucinations.

---

## 4. Database Architecture
The system relies on three primary SQLAlchemy models:
1. **`KnowledgeContainer`**: The parent grouping mechanism (has a `company_id`, `name`, and unique constraints).
2. **`DocumentAsset`**: Tracks the metadata, GCP path, and processing status (`pending`, `processing`, `completed`, `failed`) of uploaded files. Belongs to a Container.
3. **`VectorChunk`**: The actual brain of the system. Contains the raw `chunk_text`, sequence ordering, and the `embedding` vector column. Belongs to a Document and a Container.

---

## 5. Edge Cases & Resilience (Already Handled)
* **Zero RAM Bloat on Uploads:** Files aren't loaded into API memory; they are streamed directly to GCP.
* **Rate Limiting Protection:** The Celery worker sleeps for 1 second between batch calls to Gemini to avoid `429 Too Many Requests`.
* **Duplicate File Prevention:** Uploading a file with the same name automatically cleans up the old DB records and orphaned vectors before processing the new one.
* **Search Hallucination Mitigation:** Hard-coded confidence thresholds (similarity score > 0.2) ensure the Orchestrator doesn't receive completely irrelevant context.
* **Thread-Safe AI Calls:** Synchronous Gemini API search calls are wrapped in `asyncio.to_thread` to prevent blocking the FastAPI event loop during concurrent user queries.
* **Automatic Worker Retries:** If Gemini goes down or GCP fails, the Celery task automatically retries up to 3 times with a 60-second countdown.

---

## 6. Future Development & Roadmap
For future developers taking over or improving this service, here are the highest-impact areas for development:

### A. Advanced RAG Techniques
* **Hybrid Search:** Combine the current dense vector search (pgvector) with keyword-based sparse search (BM25) to improve accuracy on exact-match queries (e.g., serial numbers or specific names).
* **Query Expansion:** Use an LLM to rewrite or expand the user's query into multiple angles before generating embeddings.

### B. Ingestion Pipeline Upgrades
* **Dynamic Chunking Strategies:** Move away from basic text splitting to semantic chunking (splitting by headers, paragraphs, or logical boundaries) to retain better context.
modal Support:** Enhance the extraction process to handle images within PDFs (via OCR or Vision models) and embed them.

### C. Infrastructure & Scalability
* **Webhooks/Websockets:** Implement a way to notify the frontend when a Celery document processing task shifts from `pending` to `completed`.
* **Database Indexing:** Ensure HNSW indexes are continuously optimized in pgvector as the dataset scales into the millions of rows.