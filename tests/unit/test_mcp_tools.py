#!/usr/bin/env python3
"""
Unit tests for MCP tools (mcp_tools.py) with mocks.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from app.mcp_tools import (
    qa_search_documents,
    qa_search_testcases,
    qa_search_testcases_text,
    qa_list_features,
    qa_docs_by_feature,
    qa_health,
    qa_get_sections,
    qa_get_checklists,
    qa_get_testcases,
    qa_get_configs,
    qa_get_statistics,
    qa_get_full_structure
)


class TestQASearchDocuments:
    """Test qa_search_documents function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_search(self, mock_openai_embedder, mock_vector_repo):
        """Test successful document search."""
        with patch('app.ai.embedder.OpenAIEmbedder', return_value=mock_openai_embedder), \
             patch('app.data.vectordb_repo.VectorDBRepository', return_value=mock_vector_repo):
            
            result = await qa_search_documents("test query", top_k=5)
            
            assert result["success"] is True
            assert result["query"] == "test query"
            assert result["count"] == 1
            assert result["search_type"] == "vector_documents"
            assert len(result["results"]) == 1
            assert result["results"][0]["score"] == 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_embedding_failure(self, mock_vector_repo):
        """Test search when embedding generation fails."""
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = None
        
        with patch('app.ai.embedder.OpenAIEmbedder', return_value=mock_embedder), \
             patch('app.data.vectordb_repo.VectorDBRepository', return_value=mock_vector_repo):
            
            result = await qa_search_documents("test query")
            
            assert result["success"] is False
            assert "Failed to generate query embedding" in result["error"]
            assert result["results"] == []
            assert result["count"] == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_exception_handling(self):
        """Test exception handling in document search."""
        with patch('app.ai.embedder.OpenAIEmbedder', side_effect=Exception("Test error")):
            result = await qa_search_documents("test query")
            
            assert result["success"] is False
            assert "Test error" in result["error"]
            assert result["results"] == []
            assert result["count"] == 0


class TestQASearchTestcases:
    """Test qa_search_testcases function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_semantic_search(self, mock_qa_repo, sample_search_results):
        """Test successful semantic search."""
        mock_qa_repo.semantic_search_testcases.return_value = [
            {
                'testcase': Mock(
                    id=1,
                    step="Test step",
                    expected_result="Expected result",
                    priority=Mock(value="HIGH"),
                    test_group=Mock(value="GENERAL"),
                    functionality="Search",
                    subcategory=None,
                    checklist_id=1,
                    screenshot=None,
                    qa_auto_coverage=None
                ),
                'checklist_title': 'Test Checklist',
                'config_name': None,
                'similarity': 0.85
            }
        ]
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_search_testcases("test query", limit=10)
            
            assert result["success"] is True
            assert result["query"] == "test query"
            assert result["count"] == 1
            assert result["search_type"] == "semantic"
            assert len(result["results"]) == 1
            assert result["results"][0]["id"] == 1
            assert result["results"][0]["similarity"] == 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test short query
        result = await qa_search_testcases("ab")
        assert result["success"] is False
        assert "at least 3 characters long" in result["error"]
        
        # Test invalid limit
        result = await qa_search_testcases("test", limit=0)
        assert result["success"] is False
        assert "between 1 and 50" in result["error"]
        
        # Test invalid min_similarity
        result = await qa_search_testcases("test", min_similarity=1.5)
        assert result["success"] is False
        assert "between 0.0 and 1.0" in result["error"]
        
        # Test invalid test_group
        result = await qa_search_testcases("test", test_group="INVALID")
        assert result["success"] is False
        assert "GENERAL or CUSTOM" in result["error"]
        
        # Test invalid priority
        result = await qa_search_testcases("test", priority="INVALID")
        assert result["success"] is False
        assert "LOWEST, LOW, MEDIUM, HIGH, HIGHEST, CRITICAL" in result["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_exception_handling(self, mock_qa_repo):
        """Test exception handling in semantic search."""
        mock_qa_repo.semantic_search_testcases.side_effect = Exception("Test error")
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_search_testcases("test query")
            
            assert result["success"] is False
            assert "Test error" in result["error"]


class TestQASearchTestcasesText:
    """Test qa_search_testcases_text function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_text_search(self, mock_qa_repo, sample_qa_data):
        """Test successful text search."""
        mock_testcase = Mock()
        mock_testcase.id = 1
        mock_testcase.step = "Test step"
        mock_testcase.expected_result = "Expected result"
        mock_testcase.screenshot = None
        mock_testcase.priority = Mock(value="HIGH")
        mock_testcase.test_group = Mock(value="GENERAL")
        mock_testcase.functionality = "Search"
        mock_testcase.subcategory = None
        mock_testcase.checklist_id = 1
        mock_testcase.checklist = Mock()
        mock_testcase.checklist.title = "Test Checklist"
        mock_testcase.checklist.section = Mock()
        mock_testcase.checklist.section.title = "Test Section"
        
        mock_qa_repo.search_testcases.return_value = [mock_testcase]
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_search_testcases_text("test query", limit=10)
            
            assert result["success"] is True
            assert result["query"] == "test query"
            assert result["count"] == 1
            assert len(result["testcases"]) == 1
            assert result["testcases"][0]["id"] == 1
            assert result["testcases"][0]["checklist_title"] == "Test Checklist"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test short query
        result = await qa_search_testcases_text("a")
        assert result["success"] is False
        assert "at least 2 characters long" in result["error"]
        
        # Test invalid limit
        result = await qa_search_testcases_text("test", limit=0)
        assert result["success"] is False
        assert "between 1 and 200" in result["error"]
        
        # Test invalid test_group
        result = await qa_search_testcases_text("test", test_group="INVALID")
        assert result["success"] is False
        assert "GENERAL or CUSTOM" in result["error"]
        
        # Test invalid priority
        result = await qa_search_testcases_text("test", priority="INVALID")
        assert result["success"] is False
        assert "LOW, MEDIUM, HIGH, or CRITICAL" in result["error"]


class TestQAListFeatures:
    """Test qa_list_features function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_list_features(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful features listing."""
        mock_qa_repo.get_session.return_value = test_session
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_list_features(limit=10, with_documents=True)
            
            assert result["success"] is True
            assert result["count"] >= 0
            assert "features" in result
            assert result["limit"] == 10
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test invalid limit
        result = await qa_list_features(limit=0)
        assert result["success"] is False
        assert "between 1 and 500" in result["error"]
        
        # Test invalid offset
        result = await qa_list_features(offset=-1)
        assert result["success"] is False
        assert "non-negative" in result["error"]


class TestQADocsByFeature:
    """Test qa_docs_by_feature function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_docs_by_feature(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful docs by feature."""
        mock_qa_repo.get_session.return_value = test_session
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_docs_by_feature(feature_name="Search", limit=10)
            
            assert result["success"] is True
            assert "documents" in result
            assert result["limit"] == 10
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test missing feature name and ID
        result = await qa_docs_by_feature()
        assert result["success"] is False
        assert "Either feature_name or feature_id is required" in result["error"]
        
        # Test invalid limit
        result = await qa_docs_by_feature(feature_name="test", limit=0)
        assert result["success"] is False
        assert "between 1 and 200" in result["error"]
        
        # Test invalid offset
        result = await qa_docs_by_feature(feature_name="test", offset=-1)
        assert result["success"] is False
        assert "non-negative" in result["error"]


class TestQAHealth:
    """Test qa_health function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_health_check(self, mock_qa_repo, sample_health_response):
        """Test successful health check."""
        mock_qa_repo.get_session.return_value = Mock()
        mock_qa_repo.get_qa_statistics.return_value = sample_health_response["statistics"]
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo), \
             patch('sqlalchemy.text') as mock_text:
            
            result = await qa_health()
            
            assert result["success"] is True
            assert result["ok"] is True
            assert "services" in result
            assert "statistics" in result
            assert result["services"]["mysql"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mysql_connection_failure(self, mock_qa_repo):
        """Test health check with MySQL connection failure."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Connection failed")
        mock_qa_repo.get_session.return_value = mock_session
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo), \
             patch('sqlalchemy.text'):
            
            result = await qa_health()
            
            assert result["success"] is False
            assert result["services"]["mysql"]["status"] == "unhealthy"
            assert "Connection failed" in result["services"]["mysql"]["message"]


class TestQAGetSections:
    """Test qa_get_sections function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_sections(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful sections retrieval."""
        mock_qa_repo.get_qa_sections.return_value = ([sample_qa_data["section"]], 1)
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_sections(limit=10)
            
            assert result["success"] is True
            assert result["total"] == 1
            assert len(result["sections"]) == 1
            assert result["sections"][0]["id"] == 1
            assert result["sections"][0]["title"] == "Test Section"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test invalid limit
        result = await qa_get_sections(limit=0)
        assert result["success"] is False
        assert "between 1 and 500" in result["error"]
        
        # Test invalid offset
        result = await qa_get_sections(offset=-1)
        assert result["success"] is False
        assert ">= 0" in result["error"]


class TestQAGetChecklists:
    """Test qa_get_checklists function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_checklists(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful checklists retrieval."""
        mock_qa_repo.get_checklists.return_value = ([sample_qa_data["checklist"]], 1)
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_checklists(limit=10)
            
            assert result["success"] is True
            assert result["total"] == 1
            assert len(result["checklists"]) == 1
            assert result["checklists"][0]["id"] == 1
            assert result["checklists"][0]["title"] == "Test Checklist"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test invalid limit
        result = await qa_get_checklists(limit=0)
        assert result["success"] is False
        assert "between 1 and 200" in result["error"]
        
        # Test invalid offset
        result = await qa_get_checklists(offset=-1)
        assert result["success"] is False
        assert ">= 0" in result["error"]


class TestQAGetTestcases:
    """Test qa_get_testcases function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_testcases(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful testcases retrieval."""
        mock_qa_repo.get_testcases.return_value = (sample_qa_data["testcases"], 2)
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_testcases(limit=10)
            
            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["testcases"]) == 2
            assert result["testcases"][0]["id"] == 1
            assert result["testcases"][0]["functionality"] == "Search"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test invalid limit
        result = await qa_get_testcases(limit=0)
        assert result["success"] is False
        assert "between 1 and 500" in result["error"]
        
        # Test invalid offset
        result = await qa_get_testcases(offset=-1)
        assert result["success"] is False
        assert ">= 0" in result["error"]
        
        # Test invalid test_group
        result = await qa_get_testcases(test_group="INVALID")
        assert result["success"] is False
        assert "GENERAL or CUSTOM" in result["error"]
        
        # Test invalid priority
        result = await qa_get_testcases(priority="INVALID")
        assert result["success"] is False
        assert "LOW, MEDIUM, HIGH, or CRITICAL" in result["error"]


class TestQAGetConfigs:
    """Test qa_get_configs function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_configs(self, mock_qa_repo, test_session, sample_qa_data):
        """Test successful configs retrieval."""
        mock_qa_repo.get_configs.return_value = ([sample_qa_data["config"]], 1)
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_configs(limit=10)
            
            assert result["success"] is True
            assert result["total"] == 1
            assert len(result["configs"]) == 1
            assert result["configs"][0]["id"] == 1
            assert result["configs"][0]["name"] == "Test Config"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validation_errors(self):
        """Test parameter validation."""
        # Test invalid limit
        result = await qa_get_configs(limit=0)
        assert result["success"] is False
        assert "between 1 and 200" in result["error"]
        
        # Test invalid offset
        result = await qa_get_configs(offset=-1)
        assert result["success"] is False
        assert ">= 0" in result["error"]


class TestQAGetStatistics:
    """Test qa_get_statistics function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_statistics(self, mock_qa_repo, sample_health_response):
        """Test successful statistics retrieval."""
        mock_qa_repo.get_qa_statistics.return_value = sample_health_response["statistics"]
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_statistics()
            
            assert result["success"] is True
            assert "statistics" in result
            assert result["statistics"]["sections_count"] == 4
            assert result["statistics"]["testcases_count"] == 2336


class TestQAGetFullStructure:
    """Test qa_get_full_structure function."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_get_full_structure(self, mock_qa_repo):
        """Test successful full structure retrieval."""
        mock_structure = {
            "sections": [
                {
                    "id": 1,
                    "title": "Test Section",
                    "checklists": [
                        {
                            "id": 1,
                            "title": "Test Checklist",
                            "testcases": [
                                {"id": 1, "step": "Test step"}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_qa_repo.get_full_qa_structure.return_value = mock_structure
        
        with patch('app.mcp_tools.qa_repo', mock_qa_repo):
            result = await qa_get_full_structure()
            
            assert result["success"] is True
            assert "structure" in result
            assert len(result["structure"]["sections"]) == 1
            assert result["structure"]["sections"][0]["title"] == "Test Section"
