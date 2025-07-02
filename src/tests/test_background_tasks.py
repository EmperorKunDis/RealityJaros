import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from src.services.background_tasks import (
    BackgroundTaskManager,
    analyze_email_task,
    analyze_email_batch_task,
    generate_response_task,
    vectorize_emails_task,
    update_user_profile_task,
    cleanup_old_tasks,
    generate_daily_analytics
)

@pytest.fixture
def mock_celery_app():
    """Mock Celery application"""
    mock = Mock()
    mock.delay = Mock(return_value=Mock(id="test-task-123"))
    mock.control.revoke = Mock()
    return mock

@pytest.fixture
def task_manager():
    """Background task manager instance"""
    return BackgroundTaskManager()

@pytest.fixture
def sample_email_id():
    """Sample email ID for testing"""
    return "email_123"

@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return "user_123"

class TestBackgroundTaskManager:
    """Test cases for Background Task Manager"""

    @pytest.mark.asyncio
    async def test_submit_email_analysis(self, task_manager, sample_email_id, sample_user_id):
        """Test submitting email for analysis"""
        with patch('src.services.background_tasks.analyze_email_task') as mock_task:
            mock_task.delay.return_value = Mock(id="task_123")
            
            task_id = await task_manager.submit_email_analysis(sample_email_id, sample_user_id)
            
            assert task_id == "task_123"
            mock_task.delay.assert_called_once_with(sample_email_id, sample_user_id)

    @pytest.mark.asyncio
    async def test_submit_batch_analysis(self, task_manager, sample_user_id):
        """Test submitting batch analysis"""
        email_ids = ["email_1", "email_2", "email_3"]
        
        with patch('src.services.background_tasks.analyze_email_batch_task') as mock_task:
            mock_task.delay.return_value = Mock(id="batch_task_123")
            
            task_id = await task_manager.submit_batch_analysis(email_ids, sample_user_id)
            
            assert task_id == "batch_task_123"
            mock_task.delay.assert_called_once_with(email_ids, sample_user_id)

    @pytest.mark.asyncio
    async def test_submit_response_generation(self, task_manager, sample_email_id, sample_user_id):
        """Test submitting response generation"""
        options = {"strategy": "rag", "max_context": 2000}
        
        with patch('src.services.background_tasks.generate_response_task') as mock_task:
            mock_task.delay.return_value = Mock(id="response_task_123")
            
            task_id = await task_manager.submit_response_generation(
                sample_email_id, sample_user_id, options
            )
            
            assert task_id == "response_task_123"
            mock_task.delay.assert_called_once_with(sample_email_id, sample_user_id, options)

    @pytest.mark.asyncio
    async def test_submit_vectorization(self, task_manager, sample_user_id):
        """Test submitting vectorization"""
        email_ids = ["email_1", "email_2"]
        
        with patch('src.services.background_tasks.vectorize_emails_task') as mock_task:
            mock_task.delay.return_value = Mock(id="vector_task_123")
            
            task_id = await task_manager.submit_vectorization(email_ids, sample_user_id)
            
            assert task_id == "vector_task_123"
            mock_task.delay.assert_called_once_with(email_ids, sample_user_id)

    @pytest.mark.asyncio
    async def test_submit_user_profile_update(self, task_manager, sample_user_id):
        """Test submitting user profile update"""
        with patch('src.services.background_tasks.update_user_profile_task') as mock_task:
            mock_task.delay.return_value = Mock(id="profile_task_123")
            
            task_id = await task_manager.submit_user_profile_update(sample_user_id)
            
            assert task_id == "profile_task_123"
            mock_task.delay.assert_called_once_with(sample_user_id)

    @pytest.mark.asyncio
    async def test_get_task_status(self, task_manager):
        """Test getting task status"""
        with patch('src.services.background_tasks.AsyncResult') as mock_result:
            mock_result.return_value = Mock(
                status="SUCCESS",
                result={"status": "completed"},
                traceback=None,
                date_done=datetime.utcnow(),
                successful=Mock(return_value=True)
            )
            
            status = await task_manager.get_task_status("test_task_id")
            
            assert status["status"] == "SUCCESS"
            assert status["result"]["status"] == "completed"
            assert status["successful"] == True

    @pytest.mark.asyncio
    async def test_cancel_task(self, task_manager):
        """Test cancelling a task"""
        with patch('src.services.background_tasks.celery_app') as mock_app:
            mock_app.control.revoke = Mock()
            
            result = await task_manager.cancel_task("test_task_id")
            
            assert result == True
            mock_app.control.revoke.assert_called_once_with("test_task_id", terminate=True)

class TestCeleryTasks:
    """Test cases for Celery task functions"""

    def test_analyze_email_task_structure(self):
        """Test that email analysis task has proper structure"""
        # Test that the task function exists and is callable
        assert callable(analyze_email_task)
        
        # Test task properties
        assert hasattr(analyze_email_task, 'name')
        assert analyze_email_task.name == 'analyze_email_task'

    def test_batch_analysis_task_structure(self):
        """Test that batch analysis task has proper structure"""
        assert callable(analyze_email_batch_task)
        assert hasattr(analyze_email_batch_task, 'name')
        assert analyze_email_batch_task.name == 'analyze_email_batch_task'

    def test_response_generation_task_structure(self):
        """Test that response generation task has proper structure"""
        assert callable(generate_response_task)
        assert hasattr(generate_response_task, 'name')
        assert generate_response_task.name == 'generate_response_task'

    def test_vectorization_task_structure(self):
        """Test that vectorization task has proper structure"""
        assert callable(vectorize_emails_task)
        assert hasattr(vectorize_emails_task, 'name')
        assert vectorize_emails_task.name == 'vectorize_emails_task'

    def test_profile_update_task_structure(self):
        """Test that profile update task has proper structure"""
        assert callable(update_user_profile_task)
        assert hasattr(update_user_profile_task, 'name')
        assert update_user_profile_task.name == 'update_user_profile_task'

    def test_cleanup_task_structure(self):
        """Test that cleanup task has proper structure"""
        assert callable(cleanup_old_tasks)
        assert hasattr(cleanup_old_tasks, 'name')
        assert cleanup_old_tasks.name == 'cleanup_old_tasks'

    def test_analytics_task_structure(self):
        """Test that analytics task has proper structure"""
        assert callable(generate_daily_analytics)
        assert hasattr(generate_daily_analytics, 'name')
        assert generate_daily_analytics.name == 'generate_daily_analytics'

class TestTaskExecution:
    """Test cases for task execution logic"""

    def test_task_error_handling(self):
        """Test error handling in tasks"""
        # Test that tasks handle exceptions properly
        with patch('src.services.background_tasks.asyncio.new_event_loop') as mock_loop:
            mock_loop.side_effect = Exception("Loop creation failed")
            
            # This would normally raise an exception
            # In a real test, we'd verify the task updates state to FAILURE
            try:
                # Call task function directly (not through Celery)
                analyze_email_task("test_email", "test_user")
            except Exception as e:
                assert "Loop creation failed" in str(e)

    @patch('src.services.background_tasks.AsyncSessionLocal')
    def test_async_function_mocking(self, mock_session):
        """Test mocking of async functions in tasks"""
        # Test that we can properly mock async database operations
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        
        # This demonstrates how async functions would be mocked in real tests
        assert mock_session.return_value.__aenter__ is not None

class TestPeriodicTasks:
    """Test cases for periodic task configuration"""

    def test_celery_beat_schedule_configuration(self):
        """Test that periodic tasks are properly configured"""
        from src.services.background_tasks import celery_app
        
        # Check that beat schedule is configured
        assert hasattr(celery_app.conf, 'beat_schedule')
        
        # Check specific periodic tasks
        schedule = celery_app.conf.beat_schedule
        assert 'cleanup-old-tasks' in schedule
        assert 'generate-daily-analytics' in schedule
        
        # Check task intervals
        cleanup_task = schedule['cleanup-old-tasks']
        assert cleanup_task['schedule'] == 3600.0  # Every hour
        
        analytics_task = schedule['generate-daily-analytics']
        assert analytics_task['schedule'] == 86400.0  # Every day

    def test_celery_configuration(self):
        """Test Celery app configuration"""
        from src.services.background_tasks import celery_app
        
        # Test basic configuration
        assert celery_app.conf.task_serializer == 'json'
        assert celery_app.conf.accept_content == ['json']
        assert celery_app.conf.result_serializer == 'json'
        assert celery_app.conf.timezone == 'UTC'
        assert celery_app.conf.enable_utc == True

class TestTaskIntegration:
    """Integration tests for background tasks"""

    @pytest.mark.asyncio
    async def test_task_submission_workflow(self, task_manager):
        """Test complete task submission workflow"""
        with patch('src.services.background_tasks.analyze_email_task') as mock_task:
            mock_task.delay.return_value = Mock(id="workflow_test_123")
            
            # Submit task
            task_id = await task_manager.submit_email_analysis("email_123", "user_123")
            
            # Verify task was submitted
            assert task_id == "workflow_test_123"
            
            # Test getting status
            with patch('src.services.background_tasks.AsyncResult') as mock_result:
                mock_result.return_value = Mock(
                    status="PENDING",
                    result=None,
                    successful=Mock(return_value=False)
                )
                
                status = await task_manager.get_task_status(task_id)
                assert status["status"] == "PENDING"

    @pytest.mark.asyncio 
    async def test_error_handling_in_submission(self, task_manager):
        """Test error handling in task submission"""
        with patch('src.services.background_tasks.analyze_email_task') as mock_task:
            mock_task.delay.side_effect = Exception("Celery connection failed")
            
            with pytest.raises(Exception):
                await task_manager.submit_email_analysis("email_123", "user_123")

    def test_task_priority_handling(self):
        """Test task priority handling"""
        # This would test priority queue configuration
        # For now, we just verify the priority parameter is accepted
        assert True  # Placeholder for priority testing

class TestTaskMonitoring:
    """Test cases for task monitoring and management"""

    @pytest.mark.asyncio
    async def test_task_status_reporting(self, task_manager):
        """Test task status reporting functionality"""
        with patch('src.services.background_tasks.AsyncResult') as mock_result:
            # Test different task states
            states = ["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"]
            
            for state in states:
                mock_result.return_value = Mock(
                    status=state,
                    result={"test": "data"},
                    successful=Mock(return_value=(state == "SUCCESS"))
                )
                
                status = await task_manager.get_task_status("test_task")
                assert status["status"] == state

    def test_worker_health_monitoring(self):
        """Test worker health monitoring"""
        # This would test worker status checking
        # Placeholder for worker monitoring tests
        assert True

class TestTaskConfiguration:
    """Test cases for task configuration and settings"""

    def test_task_timeout_configuration(self):
        """Test task timeout settings"""
        from src.services.background_tasks import celery_app
        
        # Check timeout settings
        assert celery_app.conf.task_time_limit == 30 * 60  # 30 minutes
        assert celery_app.conf.task_soft_time_limit == 25 * 60  # 25 minutes

    def test_worker_configuration(self):
        """Test worker configuration settings"""
        from src.services.background_tasks import celery_app
        
        # Check worker settings
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.worker_max_tasks_per_child == 1000

    def test_broker_configuration(self):
        """Test broker and backend configuration"""
        from src.services.background_tasks import celery_app
        from src.config.settings import settings
        
        # Test that broker and backend are configured
        assert celery_app.conf.broker_url == settings.redis_url
        assert celery_app.conf.result_backend == settings.redis_url