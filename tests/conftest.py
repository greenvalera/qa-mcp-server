#!/usr/bin/env python3
"""
Pytest configuration and fixtures for QA MCP Server tests.
"""

import asyncio
import os
import pytest
import pytest_asyncio
import tempfile
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["MYSQL_HOST"] = "localhost"
os.environ["MYSQL_PORT"] = "3306"
os.environ["MYSQL_USER"] = "test_user"
os.environ["MYSQL_PASSWORD"] = "test_password"
os.environ["MYSQL_DATABASE"] = "test_qa_db"
os.environ["OPENAI_API_KEY"] = "test_openai_key"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["QDRANT_API_KEY"] = "test_qdrant_key"

from app.config import settings
from app.models.qa_models import Base, QASection, Checklist, TestCase, Config
from app.data.qa_repository import QARepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create test session factory."""
    return sessionmaker(bind=test_engine)


@pytest.fixture
def test_session(test_session_factory):
    """Create test database session."""
    session = test_session_factory()
    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def mock_qa_repo(test_session):
    """Create mocked QA repository."""
    repo = Mock(spec=QARepository)
    repo.get_session.return_value = test_session
    repo.close = Mock()
    return repo


@pytest.fixture
def mock_openai_embedder():
    """Create mocked OpenAI embedder."""
    embedder = Mock()
    embedder.embed_text.return_value = [0.1] * 1536  # Mock embedding vector
    return embedder


@pytest.fixture
def mock_vector_repo():
    """Create mocked vector repository."""
    repo = Mock()
    repo.search.return_value = [
        {
            "score": 0.85,
            "feature": {"name": "Test Feature", "id": 1},
            "document": {"id": 1, "title": "Test Document", "url": "http://test.com"},
            "space": "TEST",
            "url": "http://test.com",
            "chunk": {"id": "1", "text": "Test chunk content"}
        }
    ]
    return repo


@pytest.fixture
def sample_qa_data(test_session):
    """Create sample QA data for tests."""
    # Create test section
    section = QASection(
        id=1,
        title="Test Section",
        description="Test section description",
        url="http://test.com/section",
        confluence_page_id=12345,
        space_key="TEST"
    )
    test_session.add(section)
    
    # Create test checklist
    checklist = Checklist(
        id=1,
        title="Test Checklist",
        description="Test checklist description",
        url="http://test.com/checklist",
        confluence_page_id=54321,
        section_id=1,
        space_key="TEST",
        content_hash="test_hash_123"
    )
    test_session.add(checklist)
    
    # Create test testcases
    testcases = [
        TestCase(
            id=1,
            step="Test step 1",
            expected_result="Expected result 1",
            priority="HIGH",
            test_group="GENERAL",
            functionality="Search",
            checklist_id=1,
            order_index=1
        ),
        TestCase(
            id=2,
            step="Test step 2",
            expected_result="Expected result 2",
            priority="MEDIUM",
            test_group="CUSTOM",
            functionality="Authentication",
            checklist_id=1,
            order_index=2
        )
    ]
    for testcase in testcases:
        test_session.add(testcase)
    
    # Create test config
    config = Config(
        id=1,
        name="Test Config",
        url="http://test.com/config",
        description="Test config description"
    )
    test_session.add(config)
    
    test_session.commit()
    return {
        "section": section,
        "checklist": checklist,
        "testcases": testcases,
        "config": config
    }


@pytest.fixture
def mock_mcp_context():
    """Create mocked MCP context."""
    context = AsyncMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return {
        "success": True,
        "query": "test query",
        "results": [
            {
                "id": 1,
                "step": "Test step",
                "expected_result": "Expected result",
                "priority": "HIGH",
                "test_group": "GENERAL",
                "functionality": "Search",
                "similarity": 0.85
            }
        ],
        "count": 1
    }


@pytest.fixture
def sample_health_response():
    """Sample health check response."""
    return {
        "success": True,
        "ok": True,
        "timestamp": 1234567890.0,
        "services": {
            "mysql": {"status": "healthy", "message": "Connection OK"}
        },
        "statistics": {
            "sections_count": 4,
            "checklists_count": 285,
            "testcases_count": 2336,
            "configs_count": 291
        }
    }


@pytest.fixture
def sample_features_response():
    """Sample features list response."""
    return {
        "success": True,
        "features": [
            {
                "id": 1,
                "name": "Search",
                "description": "Functionality: Search",
                "documents": ["WEB: Search", "MOB: Search"]
            }
        ],
        "count": 1,
        "total": 1
    }


# Async test markers
pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def mcp_client():
    """Create MCP client for integration and scenario tests."""
    from tests.integration.test_mcp_integration import MCPIntegrationClient
    client = MCPIntegrationClient()
    yield client
    # MCPIntegrationClient doesn't have a close method, so we just clean up
    if hasattr(client, 'close'):
        await client.close()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "scenario: mark test as a scenario test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
