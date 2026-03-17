import os
import uuid
import logging
from celery import Celery
from google.cloud import storage
from models.db_operations import update_document_status
from models.connect_database import SyncSessionLocal
from helpers.config import settings
from controllers.process_file import chunking_text, extract_text
from controllers.embd_file import embbeding_and_saving

logger = logging.getLogger(__name__)

# 1. Initialize Celery
redis_broker_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0" 
celery_app = Celery("librarian_worker", broker=redis_broker_url)

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
            
            # --- 2. EXTRACT TEXT AND CHUNKING ---
            file_content = extract_text(file_extension, temp_filename)
            chunks = chunking_text(file_content)
            
            # --- 3. EMBED AND SAVE (BATCH PROCESSING) ---
            total_inserted = embbeding_and_saving(db_session, chunks, container_id, document_id, company_id, batch_size=50)
                
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
                