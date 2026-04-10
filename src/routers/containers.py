from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.connect_database import get_db
from models.container import KnowledgeContainer
from models.db_operations import check_container_exists, delete_container_entirely
from routers.dependencies import verify_internal_secret

router = APIRouter(
    prefix="/api/v1/containers", 
    tags=["containers"],
    dependencies=[Depends(verify_internal_secret)]
)

# Request Schema
class ContainerCreate(BaseModel):
    company_id: str
    name: str
    description: str | None = None

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_container(request: ContainerCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new knowledge container for a company. Ensures the name is unique.
    """
    # 1. Check if the name already exists for THIS company
    # We want to ensure that we don't create duplicate containers with the same name for the same company
    stmt = select(KnowledgeContainer).where(
        KnowledgeContainer.company_id == request.company_id,
        # Check if a container with this name already exists for this company
        KnowledgeContainer.name == request.name
    )
    result = await db.execute(stmt)
    existing_container = result.scalar_one_or_none()
    
    if existing_container:
        # If a container with the same name already exists, raise an error
        raise HTTPException(
            status_code=400, 
            detail=f"A container named '{request.name}' already exists for your company."
        )
        
    # 2. Create the new container
    # Create a new KnowledgeContainer instance with the provided request data
    new_container = KnowledgeContainer(
        company_id=request.company_id,
        name=request.name,
        description=request.description
    )
    
    # 3. Add the new container to the database and commit the changes
    db.add(new_container)
    await db.commit()
    await db.refresh(new_container) # Retrieves the newly generated UUID
    
    # 4. Return the UUID so the frontend can use it for uploads!
    return {
        "message": "Container created successfully",
        "container_id": str(new_container.id),
        "name": new_container.name
    }

@router.delete("/{company_id}/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_container(
    company_id: str, 
    container_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a container, all its chunks, documents, and GCP files safely.
    """
    container = await check_container_exists(db, container_id, company_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found.")
        
    await delete_container_entirely(db_session=db, container=container)
    return None
