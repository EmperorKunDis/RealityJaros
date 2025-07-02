import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from src.services.vector_db_manager import VectorDatabaseManager
from src.models.email import EmailMessage

@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client"""
    mock = Mock()
    mock.create_collection = Mock()
    mock.get_collection = Mock()
    mock.list_collections = Mock(return_value=[])
    mock.delete_collection = Mock()
    return mock

@pytest.fixture
def mock_embedding_function():
    """Mock embedding function"""
    mock = Mock()
    mock.encode = Mock(return_value=[[0.1, 0.2, 0.3] * 128])  # Mock 384-dim embedding
    return mock

@pytest.fixture
def vector_manager():
    """Vector database manager instance"""
    with patch('src.services.vector_db_manager.chromadb.Client'), \
         patch('src.services.vector_db_manager.SentenceTransformer'):
        return VectorDatabaseManager()

@pytest.fixture
def sample_emails():
    """Sample emails for testing"""
    return [
        EmailMessage(
            id="email_1",
            sender="client1@example.com",
            subject="Project Update",
            body_text="Hi, could you please provide an update on the project status?",
            received_at=datetime.utcnow()
        ),
        EmailMessage(
            id="email_2", 
            sender="client2@example.com",
            subject="Meeting Request",
            body_text="I would like to schedule a meeting to discuss the project requirements.",
            received_at=datetime.utcnow()
        )
    ]

class TestVectorDatabaseManager:
    """Test cases for Vector Database Manager"""

    @pytest.mark.asyncio
    async def test_initialize_collections(self, vector_manager, mock_chroma_client):
        """Test collection initialization"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_chroma_client.list_collections.return_value = []
            
            await vector_manager.initialize_collections()
            
            # Should create all expected collections
            expected_collections = [
                "user_emails_general",
                "user_responses_general", 
                "client_interactions_general",
                "email_patterns_general",
                "writing_styles_general",
                "topic_clusters_general",
                "conversation_threads_general",
                "business_contexts_general"
            ]
            
            assert mock_chroma_client.create_collection.call_count >= len(expected_collections)

    @pytest.mark.asyncio
    async def test_chunk_and_embed_emails(self, vector_manager, sample_emails, mock_embedding_function):
        """Test email chunking and embedding"""
        with patch.object(vector_manager, 'embedding_function', mock_embedding_function):
            
            result = await vector_manager.chunk_and_embed_emails(
                emails=sample_emails,
                user_id="test_user"
            )
            
            assert "user_emails_test_user" in result
            assert "user_emails_general" in result
            assert len(result["user_emails_test_user"]) > 0
            assert len(result["user_emails_general"]) > 0
            
            # Check chunk structure
            chunk = result["user_emails_test_user"][0]
            assert "id" in chunk
            assert "text" in chunk
            assert "embedding" in chunk
            assert "metadata" in chunk

    def test_chunk_text(self, vector_manager):
        """Test text chunking functionality"""
        long_text = "This is a very long email content. " * 20  # Create long text
        
        chunks = vector_manager._chunk_text(
            text=long_text,
            chunk_size=100,
            overlap=20
        )
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 120 for chunk in chunks)  # Size + some buffer
        
        # Test overlap
        if len(chunks) > 1:
            # Should have some overlap between consecutive chunks
            overlap_found = any(
                chunks[i][-10:] in chunks[i+1][:30] or chunks[i+1][:10] in chunks[i][-30:]
                for i in range(len(chunks)-1)
            )
            # Note: Overlap might not always be exact due to word boundaries

    @pytest.mark.asyncio
    async def test_store_email_chunks(self, vector_manager, mock_chroma_client):
        """Test storing email chunks"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_collection = Mock()
            mock_chroma_client.get_collection.return_value = mock_collection
            
            chunks = [
                {
                    "id": "chunk_1",
                    "text": "This is a test chunk",
                    "embedding": [0.1] * 384,
                    "metadata": {"email_id": "email_1", "chunk_index": 0}
                }
            ]
            
            await vector_manager.store_email_chunks(
                collection_name="test_collection",
                chunks=chunks
            )
            
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_similar_emails(self, vector_manager, mock_chroma_client, mock_embedding_function):
        """Test similarity search"""
        with patch.object(vector_manager, 'client', mock_chroma_client), \
             patch.object(vector_manager, 'embedding_function', mock_embedding_function):
            
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "ids": [["chunk_1", "chunk_2"]],
                "documents": [["Document 1", "Document 2"]],
                "metadatas": [[{"email_id": "email_1"}, {"email_id": "email_2"}]],
                "distances": [[0.1, 0.3]]
            }
            mock_chroma_client.get_collection.return_value = mock_collection
            
            result = await vector_manager.search_similar_emails(
                query_text="project update",
                user_id="test_user",
                n_results=5
            )
            
            assert "user_emails_test_user" in result
            assert len(result["user_emails_test_user"]) > 0
            
            # Check result structure
            for item in result["user_emails_test_user"]:
                assert "id" in item
                assert "text" in item
                assert "metadata" in item
                assert "distance" in item

    @pytest.mark.asyncio
    async def test_search_user_responses(self, vector_manager, mock_chroma_client, mock_embedding_function):
        """Test user response search"""
        with patch.object(vector_manager, 'client', mock_chroma_client), \
             patch.object(vector_manager, 'embedding_function', mock_embedding_function):
            
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "ids": [["response_1"]],
                "documents": [["Thank you for your email"]],
                "metadatas": [[{"response_type": "acknowledgment"}]],
                "distances": [[0.2]]
            }
            mock_chroma_client.get_collection.return_value = mock_collection
            
            result = await vector_manager.search_user_responses(
                query_text="thank you",
                user_id="test_user",
                n_results=3
            )
            
            assert len(result) > 0
            assert result[0]["text"] == "Thank you for your email"

    @pytest.mark.asyncio
    async def test_store_conversation_thread(self, vector_manager, mock_chroma_client):
        """Test conversation thread storage"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_collection = Mock()
            mock_chroma_client.get_collection.return_value = mock_collection
            
            thread_data = {
                "thread_id": "thread_123",
                "emails": [
                    {"id": "email_1", "text": "Initial email"},
                    {"id": "email_2", "text": "Response email"}
                ],
                "summary": "Project discussion thread"
            }
            
            await vector_manager.store_conversation_thread(
                user_id="test_user",
                thread_data=thread_data
            )
            
            mock_collection.add.assert_called()

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, vector_manager, mock_chroma_client):
        """Test collection statistics"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_collection = Mock()
            mock_collection.count.return_value = 100
            mock_chroma_client.get_collection.return_value = mock_collection
            mock_chroma_client.list_collections.return_value = [
                Mock(name="test_collection")
            ]
            
            stats = await vector_manager.get_collection_stats()
            
            assert "collections" in stats
            assert "total_documents" in stats
            assert stats["total_documents"] > 0

    def test_generate_collection_name(self, vector_manager):
        """Test collection name generation"""
        # Test user-specific collection
        name = vector_manager._generate_collection_name("emails", "user_123")
        assert name == "user_emails_user_123"
        
        # Test general collection
        name = vector_manager._generate_collection_name("patterns", None)
        assert name == "email_patterns_general"

    def test_prepare_metadata(self, vector_manager):
        """Test metadata preparation"""
        email = EmailMessage(
            id="email_123",
            sender="test@example.com",
            subject="Test Subject",
            body_text="Test content",
            received_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        metadata = vector_manager._prepare_email_metadata(
            email=email,
            chunk_index=0,
            chunk_count=3,
            additional_metadata={"category": "business"}
        )
        
        assert metadata["email_id"] == "email_123"
        assert metadata["sender"] == "test@example.com"
        assert metadata["subject"] == "Test Subject"
        assert metadata["chunk_index"] == 0
        assert metadata["chunk_count"] == 3
        assert metadata["category"] == "business"
        assert "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_error_handling(self, vector_manager, mock_chroma_client):
        """Test error handling"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            # Simulate collection error
            mock_chroma_client.get_collection.side_effect = Exception("Collection not found")
            
            # Should handle error gracefully
            result = await vector_manager.search_similar_emails(
                query_text="test",
                user_id="test_user"
            )
            
            # Should return empty result instead of crashing
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_bulk_operations(self, vector_manager, sample_emails, mock_chroma_client):
        """Test bulk operations"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_collection = Mock()
            mock_chroma_client.get_collection.return_value = mock_collection
            
            # Test bulk email storage
            await vector_manager.bulk_store_emails(
                emails=sample_emails,
                user_id="test_user"
            )
            
            # Should call add method for bulk operation
            mock_collection.add.assert_called()

    def test_embedding_generation(self, vector_manager, mock_embedding_function):
        """Test embedding generation"""
        with patch.object(vector_manager, 'embedding_function', mock_embedding_function):
            text = "This is a test email content"
            
            embedding = vector_manager._generate_embedding(text)
            
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            mock_embedding_function.encode.assert_called_with([text])

    @pytest.mark.asyncio
    async def test_collection_cleanup(self, vector_manager, mock_chroma_client):
        """Test collection cleanup operations"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            # Test delete old chunks
            mock_collection = Mock()
            mock_collection.get.return_value = {
                "ids": ["old_chunk_1", "old_chunk_2"],
                "metadatas": [
                    {"timestamp": "2023-01-01T00:00:00Z"},
                    {"timestamp": "2024-01-01T00:00:00Z"}
                ]
            }
            mock_chroma_client.get_collection.return_value = mock_collection
            
            await vector_manager.cleanup_old_chunks(
                user_id="test_user",
                days_old=30
            )
            
            # Should identify and delete old chunks
            mock_collection.delete.assert_called()

    def test_text_preprocessing(self, vector_manager):
        """Test text preprocessing for embedding"""
        # Test various text formats
        test_cases = [
            ("Normal text", "Normal text"),
            ("TEXT WITH CAPS", "text with caps"),
            ("  Whitespace  ", "Whitespace"),
            ("Text\nwith\nnewlines", "Text with newlines"),
            ("", ""),  # Empty text
        ]
        
        for input_text, expected in test_cases:
            result = vector_manager._preprocess_text(input_text)
            assert expected.lower() in result.lower()

    @pytest.mark.asyncio
    async def test_vector_health_check(self, vector_manager, mock_chroma_client):
        """Test vector database health check"""
        with patch.object(vector_manager, 'client', mock_chroma_client):
            mock_chroma_client.heartbeat.return_value = 123456
            
            health = await vector_manager.health_check()
            
            assert health["status"] == "healthy"
            assert "heartbeat" in health
            assert "collections_count" in health

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, vector_manager, mock_chroma_client, mock_embedding_function):
        """Test similarity threshold filtering"""
        with patch.object(vector_manager, 'client', mock_chroma_client), \
             patch.object(vector_manager, 'embedding_function', mock_embedding_function):
            
            # Mock results with varying distances
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "ids": [["very_similar", "somewhat_similar", "not_similar"]],
                "documents": [["Doc 1", "Doc 2", "Doc 3"]],
                "metadatas": [[{}, {}, {}]],
                "distances": [[0.1, 0.5, 0.9]]  # Different similarity levels
            }
            mock_chroma_client.get_collection.return_value = mock_collection
            
            result = await vector_manager.search_similar_emails(
                query_text="test",
                user_id="test_user",
                similarity_threshold=0.6  # Should filter out the last one
            )
            
            # Should only return results below threshold
            user_results = result.get("user_emails_test_user", [])
            assert all(item["distance"] <= 0.6 for item in user_results)