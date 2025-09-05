"""Basic tests for QA MCP Server."""

import pytest
from unittest.mock import Mock, patch
import os
import sys

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import Settings
from app.ai.embedder import OpenAIEmbedder
from app.mcp_tools.base import MCPToolBase, MCPToolError
from scripts.confluence_mock import MockConfluenceAPI


class TestConfiguration:
    """Test configuration management."""
    
    def test_settings_creation(self):
        """Test settings can be created."""
        settings = Settings(
            openai_api_key="test_key",
            mysql_dsn="mysql+pymysql://test:test@localhost/test",
            vectordb_url="http://localhost:6333"
        )
        
        assert settings.openai_api_key == "test_key"
        assert settings.mysql_dsn == "mysql+pymysql://test:test@localhost/test"
        assert settings.vectordb_url == "http://localhost:6333"
        assert settings.app_port == 3000  # default
    
    def test_environment_detection(self):
        """Test environment detection."""
        settings = Settings(
            openai_api_key="test",
            environment="development"
        )
        assert settings.is_development is True
        assert settings.is_production is False
        
        settings = Settings(
            openai_api_key="test",
            environment="production"
        )
        assert settings.is_development is False
        assert settings.is_production is True


class TestMockConfluenceAPI:
    """Test mock Confluence API."""
    
    def test_mock_api_creation(self):
        """Test mock API can be created."""
        api = MockConfluenceAPI()
        assert len(api.mock_pages) > 0
        assert len(api.mock_spaces) > 0
    
    def test_get_pages_no_filter(self):
        """Test getting pages without filters."""
        api = MockConfluenceAPI()
        pages = api.get_pages()
        assert len(pages) > 0
        
        # Check page structure
        page = pages[0]
        required_fields = ["id", "title", "space", "url", "labels", "version", "updated", "content"]
        for field in required_fields:
            assert field in page
    
    def test_get_pages_with_space_filter(self):
        """Test getting pages with space filter."""
        api = MockConfluenceAPI()
        qa_pages = api.get_pages(space_keys=["QA"])
        
        assert len(qa_pages) > 0
        for page in qa_pages:
            assert page["space"] == "QA"
    
    def test_get_pages_with_label_filter(self):
        """Test getting pages with label filter."""
        api = MockConfluenceAPI()
        checklist_pages = api.get_pages(labels=["checklist"])
        
        assert len(checklist_pages) > 0
        for page in checklist_pages:
            assert "checklist" in page["labels"]
    
    def test_get_page_content(self):
        """Test getting individual page content."""
        api = MockConfluenceAPI()
        pages = api.get_pages(limit=1)
        
        if pages:
            page_id = pages[0]["id"]
            content = api.get_page_content(page_id)
            assert content is not None
            assert content["id"] == page_id
    
    def test_normalize_content(self):
        """Test content normalization."""
        api = MockConfluenceAPI()
        content = "Test content with {macro} and\n\n\n\n\nextra whitespace"
        normalized = api.normalize_content(content)
        
        assert "{macro}" not in normalized
        assert "\n\n\n\n\n" not in normalized


class TestEmbedder:
    """Test OpenAI embedder (mocked)."""
    
    @patch('openai.OpenAI')
    def test_embedder_creation(self, mock_openai):
        """Test embedder can be created."""
        embedder = OpenAIEmbedder(api_key="test_key")
        assert embedder.api_key == "test_key"
        assert embedder.model == "text-embedding-3-small"  # default
    
    def test_get_dimension(self):
        """Test getting model dimension."""
        with patch('openai.OpenAI'):
            embedder = OpenAIEmbedder(api_key="test")
            dimension = embedder.get_dimension()
            assert dimension == 1536  # text-embedding-3-small dimension
    
    @patch('openai.OpenAI')
    def test_embed_text_mock(self, mock_openai):
        """Test text embedding with mocked response."""
        # Mock the OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        embedder = OpenAIEmbedder(api_key="test")
        result = embedder.embed_text("test text")
        
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()


class TestMCPToolBase:
    """Test MCP tool base functionality."""
    
    def test_tool_error_creation(self):
        """Test MCP tool error can be created."""
        error = MCPToolError("Test error")
        assert str(error) == "Test error"
    
    def test_create_response_success(self):
        """Test creating successful response."""
        # Create a concrete implementation for testing
        class TestTool(MCPToolBase):
            @property
            def name(self):
                return "test.tool"
            
            @property
            def description(self):
                return "Test tool"
            
            @property
            def input_schema(self):
                return {"type": "object"}
            
            async def execute(self, params):
                return {"test": "data"}
        
        with patch.multiple(
            'app.data.MySQLRepository',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.data.VectorDBRepository',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.ai.OpenAIEmbedder',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.ai.FeatureTagger',
            '__init__': Mock(return_value=None),
        ):
            tool = TestTool()
            response = tool.create_response({"test": "data"}, took_ms=100)
            
            assert response["test"] == "data"
            assert response["success"] is True
            assert response["took_ms"] == 100
    
    def test_create_response_error(self):
        """Test creating error response."""
        class TestTool(MCPToolBase):
            @property
            def name(self):
                return "test.tool"
            
            @property
            def description(self):
                return "Test tool"
            
            @property
            def input_schema(self):
                return {"type": "object"}
            
            async def execute(self, params):
                return {"test": "data"}
        
        with patch.multiple(
            'app.data.MySQLRepository',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.data.VectorDBRepository',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.ai.OpenAIEmbedder',
            '__init__': Mock(return_value=None),
        ), patch.multiple(
            'app.ai.FeatureTagger',
            '__init__': Mock(return_value=None),
        ):
            tool = TestTool()
            response = tool.create_response(None, error="Test error")
            
            assert response["error"] == "Test error"
            assert response["success"] is False


@pytest.mark.asyncio
async def test_import():
    """Test that main modules can be imported."""
    try:
        from app.server import app
        from app.config import settings
        from app.models import Feature, Document
        from app.data import MySQLRepository, VectorDBRepository
        from app.ai import OpenAIEmbedder, FeatureTagger
        from app.mcp_tools import SearchTool, ListFeaturesTool, DocsByFeatureTool, HealthTool
        
        # If we get here, imports succeeded
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
