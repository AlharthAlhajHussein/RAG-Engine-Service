from fastapi import Header, HTTPException, status
from helpers.config import settings

async def verify_internal_secret(x_internal_secret: str = Header(..., description="Secret key passed by the Core Platform")):
    """Validates the internal authorization header to protect RAG APIs."""
    if x_internal_secret != settings.core_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal service secret. Access Denied."
        )