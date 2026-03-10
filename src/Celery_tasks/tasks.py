import os
import uuid
import logging
import time
from celery import Celery
from google.cloud import storage

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from google.genai import types
from models.db_operations import update_document_status, save_vector_chunks
from models.connect_database import SyncSessionLocal
from helpers.config import settings

logger = logging.getLogger(__name__)

# 1. Initialize Celery
redis_broker_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0" 
celery_app = Celery("librarian_worker", broker=redis_broker_url)

# 2. Initialize Gemini
gemini_client = genai.Client(api_key=settings.gemini_api_key)

@celery_app.task(bind=True, max_retries=3)
def process_and_embed_document(self, document_id: str, company_id: str, container_id: str, gcp_path: str, file_extension: str):
    """
    Downloads, extracts, chunks, embeds, and saves to the pgvector database.
    """
    logger.info(f"Processing Document {document_id} for Container {container_id}")
    temp_filename = f"/tmp/{uuid.uuid4()}.{file_extension}"
    
    with SyncSessionLocal() as db_session:
        try:
            # Mark as processing in DB
            update_document_status(db_session, document_id, "processing")
            
            # --- 1. DOWNLOAD FROM GCP ---
            storage_client = storage.Client()
            bucket = storage_client.bucket(settings.gcp_storage_bucket)
            blob = bucket.blob(gcp_path)
            blob.download_to_filename(temp_filename)
            
            # --- 2. EXTRACT TEXT ---
            if file_extension == "pdf":
                loader = PyMuPDFLoader(temp_filename)
            elif file_extension == "txt":
                loader = TextLoader(temp_filename, encoding='utf-8')
            elif file_extension == "docx":
                loader = Docx2txtLoader(temp_filename)
            else:
                raise ValueError(f"Unsupported extension: {file_extension}")
                
            file_content = loader.load()
            
            # --- 3. CHUNK TEXT ---
            text_splitter = RecursiveCharacterTextSplitter(
                separators=["\n\n", "\n", ".", "؟", "!", " "],
                chunk_size=500,
                chunk_overlap=50,
                length_function=len
            )
            
            # Extract plain text strings from Langchain documents
            raw_texts = [doc.page_content for doc in file_content]
            chunks = text_splitter.create_documents(raw_texts)
            
            # --- 4. EMBED AND SAVE (BATCH PROCESSING) ---
            batch_size = 50 
            total_inserted = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_texts = [chunk.page_content for chunk in batch]
                
                if not batch_texts:
                    continue # Skip empty batches
                
                # A. Call Gemini API using STRICT typing (This fixes the 404!)
                embed_config = types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
                
                # A. Call Gemini API
                response = gemini_client.models.embed_content(
                    model=settings.embedding_model,
                    contents=batch_texts,
                    config=embed_config
                )
                
                embeddings_list = [item.values for item in response.embeddings]
                
                # B. Map data to our new SQLAlchemy Model structure
                chunks_to_insert = []
                for idx, (chunk_text, vector) in enumerate(zip(batch_texts, embeddings_list)):
                    chunks_to_insert.append({
                        "container_id": container_id,
                        "document_id": document_id,       # The file_id requirement
                        "chunk_text": chunk_text,         # The text requirement
                        "chunk_order": total_inserted + idx + 1,
                        "metadata_": {"company_id": company_id}, 
                        "embedding": vector
                    })
                
                # C. Use our modular DB operation to save
                save_vector_chunks(db_session, chunks_to_insert)
                total_inserted += len(batch)
                
                time.sleep(1) # Rate limit protection
                
            # Mark as completed in DB!
            update_document_status(db_session, document_id, "completed")
            return {"status": "success", "chunks_processed": total_inserted}

        except Exception as exc:
            logger.error(f"Error processing {gcp_path}: {exc}")
            update_document_status(db_session, document_id, "failed")
            raise self.retry(exc=exc, countdown=60)
            
        finally:
            # --- 5. CLEANUP ---
            if os.path.exists(temp_filename):
                os.remove(temp_filename)