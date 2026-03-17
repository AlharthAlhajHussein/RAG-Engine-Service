from pydantic import BaseModel



class SearchResultItem(BaseModel):
    chunk_text: str
    document_id: str
    similarity_score: float
    chunk_order: int

class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    container_id: str
    
    