import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
import logging
import uuid
from datetime import datetime
import asyncio
import json

from src.config.settings import settings
from src.models.email import EmailMessage, EmailChunk
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class VectorDatabaseManager:
    """
    Multi-database vector storage with intelligent partitioning
    Manages embedding generation, storage, and retrieval
    """
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collections = {}
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            # Configure ChromaDB client
            chroma_settings = Settings(
                chroma_server_host=settings.chroma_host,
                chroma_server_http_port=settings.chroma_port,
                allow_reset=True
            )
            
            self.client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=chroma_settings
            )
            
            logger.info("ChromaDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            # Fallback to in-memory client for development
            self.client = chromadb.Client()
            logger.info("Using in-memory ChromaDB client as fallback")

    async def initialize_collections(self):
        """
        Create and initialize vector collections for different content types
        """
        try:
            collection_configs = {
                "user_emails_general": {
                    "metadata": {"description": "General email content for all users"},
                    "embedding_function": None  # Use default
                },
                "client_business": {
                    "metadata": {"description": "Business-related communications"},
                    "embedding_function": None
                },
                "client_technical": {
                    "metadata": {"description": "Technical support and discussions"},
                    "embedding_function": None
                },
                "client_personal": {
                    "metadata": {"description": "Personal/informal communications"},
                    "embedding_function": None
                },
                "client_legal": {
                    "metadata": {"description": "Legal and compliance matters"},
                    "embedding_function": None
                },
                "client_financial": {
                    "metadata": {"description": "Financial discussions and invoicing"},
                    "embedding_function": None
                },
                "writing_styles": {
                    "metadata": {"description": "Writing style examples and patterns"},
                    "embedding_function": None
                },
                "response_templates": {
                    "metadata": {"description": "Response templates and examples"},
                    "embedding_function": None
                }
            }
            
            for collection_name, config in collection_configs.items():
                try:
                    # Try to get existing collection
                    collection = self.client.get_collection(
                        name=collection_name,
                        embedding_function=config["embedding_function"]
                    )
                    logger.info(f"Collection '{collection_name}' already exists")
                    
                except Exception:
                    # Create new collection
                    collection = self.client.create_collection(
                        name=collection_name,
                        metadata=config["metadata"],
                        embedding_function=config["embedding_function"]
                    )
                    logger.info(f"Created new collection '{collection_name}'")
                
                self.collections[collection_name] = collection
            
            logger.info(f"Initialized {len(self.collections)} vector collections")
            
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
            raise

    async def create_user_collection(self, user_id: str) -> str:
        """
        Create a user-specific collection for personalized embeddings
        
        Args:
            user_id: User identifier
            
        Returns:
            Collection name
        """
        try:
            collection_name = f"user_{user_id}_emails"
            
            try:
                # Check if collection already exists
                collection = self.client.get_collection(name=collection_name)
                logger.info(f"User collection '{collection_name}' already exists")
                
            except Exception:
                # Create new user collection
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": f"Email embeddings for user {user_id}",
                        "user_id": user_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Created user collection '{collection_name}'")
            
            self.collections[collection_name] = collection
            return collection_name
            
        except Exception as e:
            logger.error(f"Error creating user collection: {e}")
            raise

    async def chunk_and_embed_emails(self, emails: List[EmailMessage], user_id: str) -> Dict[str, List[Dict]]:
        """
        Process emails into chunks and generate embeddings
        
        Args:
            emails: List of email messages
            user_id: User identifier
            
        Returns:
            Dictionary mapping collection names to chunk data
        """
        try:
            logger.info(f"Processing {len(emails)} emails for chunking and embedding")
            
            # Create user collection
            user_collection_name = await self.create_user_collection(user_id)
            
            chunk_data = {
                user_collection_name: [],
                "user_emails_general": []
            }
            
            async with AsyncSessionLocal() as session:
                for email in emails:
                    if not email.body_text:
                        continue
                    
                    try:
                        # Generate chunks for this email
                        email_chunks = await self._chunk_email_content(email)
                        
                        for chunk_idx, chunk in enumerate(email_chunks):
                            # Generate embedding
                            embedding = await self._generate_embedding(chunk["text"])
                            
                            # Prepare chunk metadata
                            chunk_metadata = {
                                "email_id": str(email.id),
                                "user_id": user_id,
                                "chunk_index": chunk_idx,
                                "chunk_type": chunk["type"],
                                "direction": email.direction,
                                "sender": email.sender,
                                "recipient": email.recipient,
                                "subject": email.subject or "",
                                "sent_date": email.sent_datetime.isoformat() if email.sent_datetime else "",
                                "character_count": len(chunk["text"]),
                                "token_count": len(chunk["text"].split())
                            }
                            
                            # Determine appropriate collection based on content analysis
                            target_collections = await self._determine_target_collections(
                                email, chunk, chunk_metadata
                            )
                            
                            # Add to appropriate collections
                            for collection_name in target_collections:
                                if collection_name not in chunk_data:
                                    chunk_data[collection_name] = []
                                
                                chunk_data[collection_name].append({
                                    "id": f"{email.id}_{chunk_idx}",
                                    "text": chunk["text"],
                                    "embedding": embedding.tolist(),
                                    "metadata": chunk_metadata.copy()
                                })
                            
                            # Store chunk in database
                            await self._store_chunk_record(
                                session, email.id, chunk_idx, chunk, target_collections
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing email {email.id}: {e}")
                        continue
                
                await session.commit()
            
            logger.info(f"Generated chunks for {len(chunk_data)} collections")
            return chunk_data
            
        except Exception as e:
            logger.error(f"Error in chunk_and_embed_emails: {e}")
            raise

    async def _chunk_email_content(self, email: EmailMessage) -> List[Dict[str, str]]:
        """
        Split email content into meaningful chunks
        
        Args:
            email: Email message
            
        Returns:
            List of chunk dictionaries
        """
        try:
            chunks = []
            
            # Chunk subject
            if email.subject and len(email.subject.strip()) > 10:
                chunks.append({
                    "text": email.subject.strip(),
                    "type": "subject"
                })
            
            # Chunk body text
            if email.body_text:
                body_chunks = await self._split_text_into_chunks(
                    email.body_text, 
                    max_chunk_size=500,
                    overlap=50
                )
                
                for i, chunk_text in enumerate(body_chunks):
                    chunks.append({
                        "text": chunk_text,
                        "type": f"body_{i}"
                    })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking email content: {e}")
            return []

    async def _split_text_into_chunks(self, text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text
            max_chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        try:
            if len(text) <= max_chunk_size:
                return [text]
            
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + max_chunk_size
                
                # Try to break at sentence boundary
                if end < len(text):
                    # Look for sentence endings
                    sentence_break = text.rfind('.', start, end)
                    if sentence_break > start + max_chunk_size // 2:
                        end = sentence_break + 1
                    else:
                        # Look for paragraph break
                        para_break = text.rfind('\n', start, end)
                        if para_break > start + max_chunk_size // 2:
                            end = para_break
                        else:
                            # Look for word boundary
                            word_break = text.rfind(' ', start, end)
                            if word_break > start + max_chunk_size // 2:
                                end = word_break
                
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # Move start position with overlap
                start = max(end - overlap, start + 1)
                
                if start >= len(text):
                    break
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting text into chunks: {e}")
            return [text]

    async def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text using sentence transformer
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        try:
            # Clean text
            cleaned_text = text.strip()
            if not cleaned_text:
                # Return zero vector for empty text
                return np.zeros(self.embedding_model.get_sentence_embedding_dimension())
            
            # Generate embedding
            embedding = self.embedding_model.encode(cleaned_text, normalize_embeddings=True)
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector on error
            return np.zeros(self.embedding_model.get_sentence_embedding_dimension())

    async def _determine_target_collections(self, email: EmailMessage, chunk: Dict, metadata: Dict) -> List[str]:
        """
        Determine which collections should store this chunk
        
        Args:
            email: Email message
            chunk: Chunk data
            metadata: Chunk metadata
            
        Returns:
            List of target collection names
        """
        try:
            collections = [f"user_{metadata['user_id']}_emails"]
            
            # Analyze content to determine specialized collections
            text_lower = chunk["text"].lower()
            
            # Business-related keywords
            if any(keyword in text_lower for keyword in 
                   ['project', 'business', 'proposal', 'contract', 'meeting', 'deadline']):
                collections.append("client_business")
            
            # Technical keywords
            if any(keyword in text_lower for keyword in 
                   ['technical', 'api', 'software', 'code', 'system', 'bug', 'feature']):
                collections.append("client_technical")
            
            # Financial keywords
            if any(keyword in text_lower for keyword in 
                   ['invoice', 'payment', 'cost', 'budget', 'financial', 'price']):
                collections.append("client_financial")
            
            # Legal keywords
            if any(keyword in text_lower for keyword in 
                   ['legal', 'contract', 'agreement', 'terms', 'compliance']):
                collections.append("client_legal")
            
            # Personal/informal indicators
            if any(keyword in text_lower for keyword in 
                   ['thanks', 'thank you', 'best regards', 'cheers', 'hope you']):
                collections.append("client_personal")
            
            # Always add to general collection for broad search
            collections.append("user_emails_general")
            
            return list(set(collections))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error determining target collections: {e}")
            return [f"user_{metadata['user_id']}_emails"]

    async def _store_chunk_record(self, session, email_id: str, chunk_index: int, 
                                chunk: Dict, collections: List[str]):
        """
        Store chunk record in database
        
        Args:
            session: Database session
            email_id: Email identifier
            chunk_index: Chunk index
            chunk: Chunk data
            collections: Target collections
        """
        try:
            chunk_record = EmailChunk(
                email_message_id=email_id,
                chunk_text=chunk["text"],
                chunk_index=chunk_index,
                chunk_type=chunk["type"],
                vector_collection=",".join(collections),
                vector_id=f"{email_id}_{chunk_index}",
                token_count=len(chunk["text"].split()),
                character_count=len(chunk["text"])
            )
            
            session.add(chunk_record)
            
        except Exception as e:
            logger.error(f"Error storing chunk record: {e}")

    async def store_embeddings(self, chunk_data: Dict[str, List[Dict]]) -> Dict[str, int]:
        """
        Store embeddings in ChromaDB collections
        
        Args:
            chunk_data: Dictionary mapping collection names to chunk data
            
        Returns:
            Dictionary mapping collection names to number of stored chunks
        """
        try:
            stored_counts = {}
            
            for collection_name, chunks in chunk_data.items():
                if not chunks:
                    continue
                
                try:
                    # Ensure collection exists
                    if collection_name not in self.collections:
                        await self._ensure_collection_exists(collection_name)
                    
                    collection = self.collections[collection_name]
                    
                    # Prepare data for batch insertion
                    ids = [chunk["id"] for chunk in chunks]
                    documents = [chunk["text"] for chunk in chunks]
                    embeddings = [chunk["embedding"] for chunk in chunks]
                    metadatas = [chunk["metadata"] for chunk in chunks]
                    
                    # Store in ChromaDB
                    collection.add(
                        ids=ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas
                    )
                    
                    stored_counts[collection_name] = len(chunks)
                    logger.info(f"Stored {len(chunks)} chunks in collection '{collection_name}'")
                    
                except Exception as e:
                    logger.error(f"Error storing chunks in collection '{collection_name}': {e}")
                    stored_counts[collection_name] = 0
            
            return stored_counts
            
        except Exception as e:
            logger.error(f"Error in store_embeddings: {e}")
            return {}

    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure a collection exists, create if not"""
        try:
            if collection_name not in self.collections:
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": f"Auto-created collection: {collection_name}"}
                )
                self.collections[collection_name] = collection
                
        except Exception as e:
            # Collection might already exist
            try:
                collection = self.client.get_collection(name=collection_name)
                self.collections[collection_name] = collection
            except Exception as e2:
                logger.error(f"Error ensuring collection exists: {e2}")
                raise

    async def similarity_search(self, query: str, collection_names: List[str] = None, 
                              k: int = 5, user_id: str = None) -> List[Dict]:
        """
        Perform semantic similarity search across collections
        
        Args:
            query: Search query text
            collection_names: List of collection names to search (None for all)
            k: Number of results to return
            user_id: User identifier for user-specific collections
            
        Returns:
            List of search results with metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Determine collections to search
            if collection_names is None:
                if user_id:
                    collection_names = [f"user_{user_id}_emails", "user_emails_general"]
                else:
                    collection_names = list(self.collections.keys())
            
            all_results = []
            
            for collection_name in collection_names:
                if collection_name not in self.collections:
                    continue
                
                try:
                    collection = self.collections[collection_name]
                    
                    # Perform similarity search
                    results = collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=min(k, 100),  # Limit per collection
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    # Process results
                    for i in range(len(results['ids'][0])):
                        result = {
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "distance": results['distances'][0][i],
                            "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                            "collection": collection_name
                        }
                        all_results.append(result)
                        
                except Exception as e:
                    logger.error(f"Error searching collection '{collection_name}': {e}")
                    continue
            
            # Sort by similarity and return top k
            all_results.sort(key=lambda x: x['similarity'], reverse=True)
            return all_results[:k]
            
        except Exception as e:
            logger.error(f"Error in similarity_search: {e}")
            return []

    async def get_collection_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for all collections
        
        Returns:
            Dictionary mapping collection names to stats
        """
        try:
            stats = {}
            
            for collection_name, collection in self.collections.items():
                try:
                    count = collection.count()
                    stats[collection_name] = {
                        "document_count": count,
                        "name": collection_name
                    }
                except Exception as e:
                    logger.error(f"Error getting stats for collection '{collection_name}': {e}")
                    stats[collection_name] = {
                        "document_count": 0,
                        "name": collection_name,
                        "error": str(e)
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}

    async def delete_user_data(self, user_id: str):
        """
        Delete all vector data for a user
        
        Args:
            user_id: User identifier
        """
        try:
            # Delete user-specific collection
            user_collection_name = f"user_{user_id}_emails"
            
            if user_collection_name in self.collections:
                self.client.delete_collection(name=user_collection_name)
                del self.collections[user_collection_name]
                logger.info(f"Deleted user collection '{user_collection_name}'")
            
            # Remove user data from general collections
            for collection_name, collection in self.collections.items():
                try:
                    # Get all documents for this user
                    results = collection.get(
                        where={"user_id": user_id},
                        include=['ids']
                    )
                    
                    if results['ids']:
                        collection.delete(ids=results['ids'])
                        logger.info(f"Deleted {len(results['ids'])} documents from '{collection_name}'")
                        
                except Exception as e:
                    logger.error(f"Error deleting user data from collection '{collection_name}': {e}")
            
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            raise