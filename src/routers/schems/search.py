from pydantic import BaseModel, Field

# --- SCHEMAS ---
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="The user's question")
    top_k: int = Field(default=5, ge=1, le=20, description="How many chunks to return")
    
    