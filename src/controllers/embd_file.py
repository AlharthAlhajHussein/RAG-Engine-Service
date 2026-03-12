from google import genai
from google.genai import types
from helpers import settings
from models.db_operations import save_vector_chunks
from sqlalchemy.orm import Session
import time

# 2. Initialize Gemini
gemini_client = genai.Client(api_key=settings.gemini_api_key)

def embbeding_and_saving(db_session: Session, chunks: list, container_id: str, document_id: str, company_id: str, batch_size: int = 50):    
    total_inserted = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_texts = [chunk.page_content for chunk in batch]
        
        if not batch_texts:
            continue # Skip empty batches
        
        # A. Call Gemini API using STRICT typing (This fixes the 404!)
        embed_config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
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
        
    return total_inserted
        

# We wrap the Gemini call in a synchronous function so we can run it in a thread pool
def get_query_embedding(query_text: str) -> list[float]:
    embed_config = types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY", # CRITICAL: Tells Google this is a search question!
        output_dimensionality=768
    )
    response = gemini_client.models.embed_content(
        model=settings.embedding_model,
        contents=query_text,
        config=embed_config
    )
    return response.embeddings[0].values        
        