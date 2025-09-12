#!/usr/bin/env python3
"""
Unit tests for MCP Server layer.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app import mcp_server


class TestMCPTools:
    """Test MCP tool decorators and context handling."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_health_import(self):
        """Test that qa_health is properly imported."""
        assert hasattr(mcp_server, 'qa_health')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_list_features_import(self):
        """Test that qa_list_features is properly imported."""
        assert hasattr(mcp_server, 'qa_list_features')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_docs_by_feature_import(self):
        """Test that qa_docs_by_feature is properly imported."""
        assert hasattr(mcp_server, 'qa_docs_by_feature')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_search_documents_import(self):
        """Test that qa_search_documents is properly imported."""
        assert hasattr(mcp_server, 'qa_search_documents')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_search_testcases_import(self):
        """Test that qa_search_testcases is properly imported."""
        assert hasattr(mcp_server, 'qa_search_testcases')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_search_testcases_text_import(self):
        """Test that qa_search_testcases_text is properly imported."""
        assert hasattr(mcp_server, 'qa_search_testcases_text')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_sections_mcp_import(self):
        """Test that qa_get_sections_mcp is properly imported."""
        assert hasattr(mcp_server, 'qa_get_sections_mcp')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_checklists_import(self):
        """Test that qa_get_checklists is properly imported."""
        assert hasattr(mcp_server, 'qa_get_checklists')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_testcases_import(self):
        """Test that qa_get_testcases is properly imported."""
        assert hasattr(mcp_server, 'qa_get_testcases')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_configs_import(self):
        """Test that qa_get_configs is properly imported."""
        assert hasattr(mcp_server, 'qa_get_configs')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_statistics_import(self):
        """Test that qa_get_statistics is properly imported."""
        assert hasattr(mcp_server, 'qa_get_statistics')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_qa_get_full_structure_import(self):
        """Test that qa_get_full_structure is properly imported."""
        assert hasattr(mcp_server, 'qa_get_full_structure')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mcp_server_imports(self):
        """Test that all required imports are present."""
        # Test that the module can be imported without errors
        import app.mcp_server
        assert app.mcp_server is not None
        
        # Test that FastMCP is imported
        assert hasattr(app.mcp_server, 'FastMCP')
        
        # Test that all tool functions are imported
        expected_tools = [
            'qa_health',
            'qa_list_features', 
            'qa_docs_by_feature',
            'qa_search_documents',
            'qa_search_testcases',
            'qa_search_testcases_text',
            'qa_get_sections_mcp',
            'qa_get_checklists',
            'qa_get_testcases',
            'qa_get_configs',
            'qa_get_statistics',
            'qa_get_full_structure'
        ]
        
        for tool in expected_tools:
            assert hasattr(app.mcp_server, tool), f"Missing tool: {tool}"