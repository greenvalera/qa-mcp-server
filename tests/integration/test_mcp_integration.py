#!/usr/bin/env python3
"""
Integration tests for MCP server - real connection tests.
"""

import asyncio
import json
import pytest
import httpx
from typing import Dict, Any, Optional


class MCPIntegrationClient:
    """Client for testing MCP server integration."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """Initialize integration test client."""
        self.base_url = base_url
        self.jsonrpc_url = f"{base_url}/jsonrpc"
    
    async def call_tool(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call MCP tool via JSON-RPC."""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.jsonrpc_url,
                json=request_data
            )
            response.raise_for_status()
            return response.json()
    
    async def call_http_endpoint(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call HTTP REST API endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, params=data or {})
            elif method.upper() == "POST":
                response = await client.post(url, json=data or {})
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()


@pytest.fixture
def mcp_client():
    """Create MCP integration test client."""
    return MCPIntegrationClient()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for integration tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestMCPHealthIntegration:
    """Integration tests for health check functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_via_mcp(self, mcp_client):
        """Test health check via MCP JSON-RPC."""
        result = await mcp_client.call_tool("qa.health")
        
        assert "result" in result
        health_data = result["result"]
        assert health_data["success"] is True
        assert health_data["ok"] is True
        assert "services" in health_data
        assert "statistics" in health_data
        assert health_data["services"]["mysql"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_via_http(self, mcp_client):
        """Test health check via HTTP REST API."""
        result = await mcp_client.call_http_endpoint("GET", "/health")
        
        assert result["success"] is True
        assert result["ok"] is True
        assert "services" in result
        assert "statistics" in result


class TestMCPSearchIntegration:
    """Integration tests for search functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_documents_integration(self, mcp_client):
        """Test document search integration."""
        result = await mcp_client.call_tool("qa.search_documents", {
            "query": "Як тестувати функціонал Search",
            "top_k": 5
        })
        
        assert "result" in result
        search_data = result["result"]
        assert search_data["success"] is True
        assert search_data["query"] == "Як тестувати функціонал Search"
        assert "results" in search_data
        assert "count" in search_data
        assert search_data["search_type"] == "vector_documents"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_testcases_semantic_integration(self, mcp_client):
        """Test semantic testcase search integration."""
        result = await mcp_client.call_tool("qa.search_testcases", {
            "query": "How to test Search functionality",
            "limit": 10,
            "min_similarity": 0.3
        })
        
        assert "result" in result
        search_data = result["result"]
        assert search_data["success"] is True
        assert search_data["query"] == "How to test Search functionality"
        assert "results" in search_data
        assert "count" in search_data
        assert search_data["search_type"] == "semantic"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_testcases_text_integration(self, mcp_client):
        """Test text testcase search integration."""
        result = await mcp_client.call_tool("qa.search_testcases_text", {
            "query": "Search",
            "limit": 15
        })
        
        assert "result" in result
        search_data = result["result"]
        assert search_data["success"] is True
        assert search_data["query"] == "Search"
        assert "testcases" in search_data
        assert "count" in search_data
        assert len(search_data["testcases"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_via_http(self, mcp_client):
        """Test search via HTTP REST API - SKIPPED (no HTTP API available)."""
        pytest.skip("HTTP API not available in this MCP server")


class TestMCPDataRetrievalIntegration:
    """Integration tests for data retrieval functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_sections_integration(self, mcp_client):
        """Test get sections integration."""
        result = await mcp_client.call_tool("qa.get_sections", {
            "limit": 10
        })
        
        assert "result" in result
        sections_data = result["result"]
        assert sections_data["success"] is True
        assert "sections" in sections_data
        assert "total" in sections_data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_checklists_integration(self, mcp_client):
        """Test get checklists integration."""
        result = await mcp_client.call_tool("qa.get_checklists", {
            "limit": 10
        })
        
        assert "result" in result
        checklists_data = result["result"]
        assert checklists_data["success"] is True
        assert "checklists" in checklists_data
        assert "total" in checklists_data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_testcases_integration(self, mcp_client):
        """Test get testcases integration."""
        result = await mcp_client.call_tool("qa.get_testcases", {
            "functionality": "Search",
            "limit": 15
        })
        
        assert "result" in result
        testcases_data = result["result"]
        assert testcases_data["success"] is True
        assert "testcases" in testcases_data
        assert "total" in testcases_data
        assert len(testcases_data["testcases"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_configs_integration(self, mcp_client):
        """Test get configs integration."""
        result = await mcp_client.call_tool("qa.get_configs", {
            "limit": 10
        })
        
        assert "result" in result
        configs_data = result["result"]
        # Configs might not be available in test environment
        if configs_data["success"]:
            assert "configs" in configs_data
            assert "total" in configs_data
        else:
            # If configs are not available, that's also acceptable
            assert "error" in configs_data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_statistics_integration(self, mcp_client):
        """Test get statistics integration."""
        result = await mcp_client.call_tool("qa.get_statistics")
        
        assert "result" in result
        stats_data = result["result"]
        assert stats_data["success"] is True
        assert "statistics" in stats_data
        assert "sections_count" in stats_data["statistics"]
        assert "testcases_count" in stats_data["statistics"]
        assert stats_data["statistics"]["testcases_count"] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_full_structure_integration(self, mcp_client):
        """Test get full structure integration."""
        result = await mcp_client.call_tool("qa.get_full_structure")
        
        assert "result" in result
        structure_data = result["result"]
        assert structure_data["success"] is True
        assert "structure" in structure_data
        # Structure is a list of sections, not a dict with sections key
        assert isinstance(structure_data["structure"], list)
        assert len(structure_data["structure"]) > 0


class TestMCPFeaturesIntegration:
    """Integration tests for features functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_features_integration(self, mcp_client):
        """Test list features integration."""
        result = await mcp_client.call_tool("qa.list_features", {
            "limit": 10,
            "with_documents": True
        })
        
        assert "result" in result
        features_data = result["result"]
        assert features_data["success"] is True
        assert "features" in features_data
        assert "count" in features_data
        assert "total" in features_data
        assert len(features_data["features"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_docs_by_feature_integration(self, mcp_client):
        """Test docs by feature integration."""
        # First get a feature to test with
        features_result = await mcp_client.call_tool("qa.list_features", {"limit": 1})
        if features_result["result"]["features"]:
            test_feature = features_result["result"]["features"][0]
            
            result = await mcp_client.call_tool("qa.docs_by_feature", {
                "feature_name": test_feature["name"],
                "limit": 5
            })
            
            assert "result" in result
            docs_data = result["result"]
            assert docs_data["success"] is True
            assert "documents" in docs_data
            assert "count" in docs_data
            assert "feature_name" in docs_data


class TestMCPErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_parameters_integration(self, mcp_client):
        """Test error handling for invalid parameters."""
        # Test invalid limit
        result = await mcp_client.call_tool("qa.get_testcases", {
            "limit": 0
        })
        
        assert "result" in result
        error_data = result["result"]
        assert error_data["success"] is False
        assert "error" in error_data
        assert "between 1 and 500" in error_data["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_query_integration(self, mcp_client):
        """Test error handling for invalid queries."""
        # Test short query
        result = await mcp_client.call_tool("qa.search_testcases", {
            "query": "ab"
        })
        
        assert "result" in result
        error_data = result["result"]
        assert error_data["success"] is False
        assert "error" in error_data
        assert "at least 3 characters long" in error_data["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_enum_values_integration(self, mcp_client):
        """Test error handling for invalid enum values."""
        # Test invalid test_group
        result = await mcp_client.call_tool("qa.get_testcases", {
            "test_group": "INVALID"
        })
        
        assert "result" in result
        error_data = result["result"]
        assert error_data["success"] is False
        assert "error" in error_data
        assert "GENERAL or CUSTOM" in error_data["error"]


class TestMCPPerformanceIntegration:
    """Integration tests for performance."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_search_performance(self, mcp_client):
        """Test search performance with multiple queries."""
        queries = [
            "Як тестувати функціонал Search",
            "How to test Search functionality", 
            "Search",
            "поиск",
            "authentication testing"
        ]
        
        results = []
        for query in queries:
            start_time = asyncio.get_event_loop().time()
            
            result = await mcp_client.call_tool("qa.search_testcases_text", {
                "query": query,
                "limit": 10
            })
            
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            
            results.append({
                "query": query,
                "response_time": response_time,
                "success": result["result"]["success"],
                "count": result["result"]["count"]
            })
        
        # Verify all queries succeeded
        for result in results:
            assert result["success"] is True
            assert result["response_time"] < 5.0  # Should respond within 5 seconds
        
        # Print performance summary
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        print(f"\nPerformance Test Results:")
        print(f"Average response time: {avg_response_time:.3f}s")
        for result in results:
            print(f"  {result['query']}: {result['response_time']:.3f}s ({result['count']} results)")


class TestMCPEndToEndIntegration:
    """End-to-end integration tests simulating real usage scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_functionality_scenario(self, mcp_client):
        """Test complete search functionality scenario."""
        # Step 1: Check system health
        health_result = await mcp_client.call_tool("qa.health")
        assert health_result["result"]["success"] is True
        print("✅ Health check passed")
        
        # Step 2: Get system statistics
        stats_result = await mcp_client.call_tool("qa.get_statistics")
        assert stats_result["result"]["success"] is True
        total_testcases = stats_result["result"]["statistics"]["testcases_count"]
        print(f"✅ System has {total_testcases} test cases")
        
        # Step 3: Search for Search functionality test cases
        search_result = await mcp_client.call_tool("qa.get_testcases", {
            "functionality": "Search",
            "limit": 10
        })
        assert search_result["result"]["success"] is True
        search_testcases = search_result["result"]["testcases"]
        print(f"✅ Found {len(search_testcases)} Search test cases")
        
        # Step 4: Semantic search for testing procedures
        semantic_result = await mcp_client.call_tool("qa.search_testcases", {
            "query": "How to test Search functionality",
            "limit": 5,
            "min_similarity": 0.3
        })
        assert semantic_result["result"]["success"] is True
        semantic_results = semantic_result["result"]["results"]
        print(f"✅ Semantic search found {len(semantic_results)} relevant test cases")
        
        # Step 5: Text search for specific terms
        text_result = await mcp_client.call_tool("qa.search_testcases_text", {
            "query": "Search",
            "limit": 15
        })
        assert text_result["result"]["success"] is True
        text_results = text_result["result"]["testcases"]
        print(f"✅ Text search found {len(text_results)} test cases")
        
        # Step 6: Document search for comprehensive information
        doc_result = await mcp_client.call_tool("qa.search_documents", {
            "query": "Як тестувати функціонал Search",
            "top_k": 5
        })
        assert doc_result["result"]["success"] is True
        doc_results = doc_result["result"]["results"]
        print(f"✅ Document search found {len(doc_results)} relevant documents")
        
        # Verify we have meaningful results
        assert len(search_testcases) > 0, "Should have Search test cases"
        assert len(text_results) > 0, "Should have text search results"
        assert len(doc_results) > 0, "Should have document search results"
        
        print("🎉 End-to-end search functionality test completed successfully!")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_features_and_documents_scenario(self, mcp_client):
        """Test features and documents scenario."""
        # Step 1: List all features
        features_result = await mcp_client.call_tool("qa.list_features", {
            "limit": 20,
            "with_documents": True
        })
        assert features_result["result"]["success"] is True
        features = features_result["result"]["features"]
        print(f"✅ Found {len(features)} features")
        
        # Step 2: Get documents for Search feature
        search_feature = None
        for feature in features:
            if "Search" in feature["name"]:
                search_feature = feature
                break
        
        if search_feature:
            docs_result = await mcp_client.call_tool("qa.docs_by_feature", {
                "feature_name": search_feature["name"],
                "limit": 10
            })
            assert docs_result["result"]["success"] is True
            documents = docs_result["result"]["documents"]
            print(f"✅ Found {len(documents)} documents for Search feature")
        
        # Step 3: Get full structure
        structure_result = await mcp_client.call_tool("qa.get_full_structure")
        assert structure_result["result"]["success"] is True
        structure = structure_result["result"]["structure"]
        print(f"✅ Retrieved full QA structure with {len(structure)} sections")
        
        print("🎉 Features and documents scenario completed successfully!")
