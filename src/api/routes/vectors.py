from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from src.services.vector_db_manager import VectorDatabaseManager
from src.services.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

class VectorizeRequest(BaseModel):
    """Request to vectorize user emails"""
    user_id: str
    force_reindex: bool = False

class VectorizeResponse(BaseModel):
    """Response from vectorization process"""
    message: str
    status: str
    collections_updated: Optional[Dict[str, int]] = None
    processing_time: Optional[float] = None
    errors: Optional[List[str]] = None

class SearchRequest(BaseModel):
    """Semantic search request"""
    query: str
    collections: Optional[List[str]] = None
    max_results: int = 5
    min_similarity: float = 0.3

class SearchResponse(BaseModel):
    """Semantic search response"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    collections_searched: List[str]

class CollectionStatsResponse(BaseModel):
    """Collection statistics response"""
    collections: Dict[str, Dict[str, Any]]
    total_documents: int
    total_collections: int

@router.post("/vectorize", response_model=VectorizeResponse)
async def vectorize_emails(
    request: VectorizeRequest,
    background_tasks: BackgroundTasks
):
    """
    Vectorize user's emails and store in vector database
    
    Args:
        request: Vectorization request
        background_tasks: FastAPI background tasks
        
    Returns:
        Vectorization status and results
    """
    try:
        logger.info(f"Starting vectorization for user {request.user_id}")
        
        # Initialize vector database manager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        
        # Get user's emails from database
        from src.config.database import AsyncSessionLocal
        from src.models.email import EmailMessage
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            # Get user's emails
            stmt = select(EmailMessage).where(
                EmailMessage.user_id == request.user_id,
                EmailMessage.body_text.isnot(None),
                EmailMessage.body_text != ''
            )
            
            if not request.force_reindex:
                # Only process emails that haven't been chunked yet
                stmt = stmt.where(EmailMessage.is_chunked == False)
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            if not emails:
                return VectorizeResponse(
                    message="No emails found for vectorization",
                    status="no_data"
                )
            
            logger.info(f"Found {len(emails)} emails to vectorize")
            
            # Process emails into chunks and embeddings
            chunk_data = await vector_manager.chunk_and_embed_emails(
                list(emails), request.user_id
            )
            
            # Store embeddings in vector database
            storage_results = await vector_manager.store_embeddings(chunk_data)
            
            # Mark emails as chunked
            for email in emails:
                email.is_chunked = True
                email.is_embedded = True
            
            await session.commit()
        
        return VectorizeResponse(
            message="Email vectorization completed successfully",
            status="completed",
            collections_updated=storage_results,
            processing_time=0.0,  # TODO: Add timing
            errors=[]
        )
        
    except Exception as e:
        logger.error(f"Error during vectorization: {e}")
        raise HTTPException(status_code=500, detail=f"Vectorization failed: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic search across vector collections
    
    Args:
        request: Search request
        
    Returns:
        Search results
    """
    try:
        logger.info(f"Performing semantic search for query: '{request.query}'")
        
        # Initialize vector database manager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        
        # Perform search
        search_results = await vector_manager.similarity_search(
            query=request.query,
            collection_names=request.collections,
            k=request.max_results
        )
        
        # Filter by minimum similarity
        filtered_results = [
            result for result in search_results 
            if result["similarity"] >= request.min_similarity
        ]
        
        # Format results
        formatted_results = []
        for result in filtered_results:
            formatted_result = {
                "id": result["id"],
                "content": result["document"],
                "similarity": result["similarity"],
                "collection": result["collection"],
                "metadata": result["metadata"]
            }
            formatted_results.append(formatted_result)
        
        collections_searched = request.collections or list(vector_manager.collections.keys())
        
        return SearchResponse(
            query=request.query,
            results=formatted_results,
            total_results=len(formatted_results),
            collections_searched=collections_searched
        )
        
    except Exception as e:
        logger.error(f"Error during semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/collections/stats", response_model=CollectionStatsResponse)
async def get_collection_stats():
    """
    Get statistics for all vector collections
    
    Returns:
        Collection statistics
    """
    try:
        # Initialize vector database manager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        
        # Get collection statistics
        stats = await vector_manager.get_collection_stats()
        
        total_documents = sum(
            collection_stats.get("document_count", 0) 
            for collection_stats in stats.values()
        )
        
        return CollectionStatsResponse(
            collections=stats,
            total_documents=total_documents,
            total_collections=len(stats)
        )
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection stats: {str(e)}")

@router.delete("/user/{user_id}")
async def delete_user_vectors(user_id: str):
    """
    Delete all vector data for a specific user
    
    Args:
        user_id: User identifier
        
    Returns:
        Deletion status
    """
    try:
        logger.info(f"Deleting vector data for user {user_id}")
        
        # Initialize vector database manager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        
        # Delete user data
        await vector_manager.delete_user_data(user_id)
        
        # Update database to mark emails as not chunked
        from src.config.database import AsyncSessionLocal
        from src.models.email import EmailMessage
        from sqlalchemy import select, update
        
        async with AsyncSessionLocal() as session:
            stmt = update(EmailMessage).where(
                EmailMessage.user_id == user_id
            ).values(
                is_chunked=False,
                is_embedded=False
            )
            
            await session.execute(stmt)
            await session.commit()
        
        return {
            "message": f"Successfully deleted vector data for user {user_id}",
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error deleting user vectors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user vectors: {str(e)}")

@router.post("/initialize")
async def initialize_vector_database():
    """
    Initialize vector database collections
    
    Returns:
        Initialization status
    """
    try:
        logger.info("Initializing vector database")
        
        # Initialize vector database manager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        
        # Get collection stats
        stats = await vector_manager.get_collection_stats()
        
        return {
            "message": "Vector database initialized successfully",
            "status": "completed",
            "collections_created": len(stats),
            "collections": list(stats.keys())
        }
        
    except Exception as e:
        logger.error(f"Error initializing vector database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize vector database: {str(e)}")

@router.get("/health")
async def vector_health_check():
    """
    Health check for vector database services
    
    Returns:
        Health status
    """
    try:
        # Initialize and test vector database manager
        vector_manager = VectorDatabaseManager()
        
        # Test basic functionality
        test_embedding = await vector_manager._generate_embedding("test text")
        
        return {
            "status": "healthy",
            "vector_db_connected": True,
            "embedding_model_loaded": True,
            "embedding_dimension": len(test_embedding),
            "chroma_host": vector_manager.client._host if hasattr(vector_manager.client, '_host') else "in-memory",
            "collections_available": len(vector_manager.collections)
        }
        
    except Exception as e:
        logger.error(f"Vector health check failed: {e}")
        return {
            "status": "unhealthy",
            "vector_db_connected": False,
            "embedding_model_loaded": False,
            "error": str(e)
        }