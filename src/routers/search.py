from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import asyncio
import logging
from models.connect_database import get_db
from models.chunk import VectorChunk
from models.db_operations import check_container_exists, semantic_search
from routers.schems.search import SearchRequest
from views.search import SearchResultItem, SearchResponse
from controllers.embd_file import get_query_embedding
from routers.dependencies import verify_internal_secret

logger = logging.getLogger("uvicorn.error")
router = APIRouter(
    prefix="/api/v1/search", 
    tags=["search"],
    dependencies=[Depends(verify_internal_secret)]
)


@router.post("/{company_id}/{container_id}", response_model=SearchResponse)
async def search_knowledge_base(
    company_id: str,
    container_id: uuid.UUID,
    request: SearchRequest,
    db_session: AsyncSession = Depends(get_db)
):
    """
    Takes a user query, embeds it, and performs a fast HNSW vector search to find the most relevant chunks.
    """
    # --- EDGE CASE 1: Verify the Container Belongs to the Company ---
    container = await check_container_exists(db_session, str(container_id), company_id)
    if not container:
        raise HTTPException(
            status_code=404,
            detail="Knowledge container not found or unauthorized access."
        )

    # --- 1. EMBED THE QUERY ---
    try:
        # Run the synchronous Gemini SDK call in a background thread so it doesn't block FastAPI
        query_vector = await asyncio.to_thread(get_query_embedding, request.query)
    except Exception as e:
        logger.error(f"Gemini API Error during search: {e}")
        raise HTTPException(status_code=502, detail="Failed to embed search query via AI provider.")

    # --- 2. VECTOR SEARCH USING PGVECTOR ---
    search_results = await semantic_search(db_session, container_id, query_vector, request.top_k)

    # --- 3. FORMAT THE RESPONSE ---
    formatted_results = []
    
    # search_results returns a tuple: (VectorChunk object, similarity_score float)
    for chunk_obj, score in search_results:
        # --- EDGE CASE 2: Filter out absolute garbage matches ---
        # If the similarity score is too low (e.g., < 0.2), it's a hallucination risk.
        if score < 0.2: 
            continue 
            
        formatted_results.append(
            SearchResultItem(
                chunk_text=chunk_obj.chunk_text,
                document_id=str(chunk_obj.document_id),
                similarity_score=round(score, 4), # Round to 4 decimals for clean JSON
                chunk_order=chunk_obj.chunk_order
            )
        )

    # --- EDGE CASE 3: No relevant data found ---
    # We still return a 200 OK, but with an empty list so the Orchestrator knows to say "I don't know"
    return SearchResponse(
        results=formatted_results,
        container_id=str(container_id)
    )
    