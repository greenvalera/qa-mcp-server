#!/usr/bin/env python3
"""Test client for MCP QA Search Server."""

import json
import asyncio
import httpx
import click
from typing import Dict, Any, Optional


class MCPTestClient:
    """Test client for MCP tools."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """Initialize test client."""
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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.jsonrpc_url,
                json=request_data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def test_health(self) -> bool:
        """Test health check."""
        click.echo("🔍 Testing qa.health...")
        try:
            result = await self.call_tool("qa.health")
            
            if "error" in result and result["error"] is not None:
                click.echo(f"  ❌ Error: {result['error']}")
                return False
            
            health_data = result["result"]
            click.echo(f"  ✅ Vector DB: {health_data['vector_db']['status']}")
            click.echo(f"  ✅ MySQL: {health_data['mysql']['status']}")
            click.echo(f"  ✅ OpenAI: {health_data['openai']['status']}")
            click.echo(f"  📊 Documents: {health_data['summary']['total_documents']}")
            click.echo(f"  📊 Features: {health_data['summary']['total_features']}")
            click.echo(f"  📊 Chunks: {health_data['summary']['total_chunks']}")
            
            return health_data["ok"]
            
        except Exception as e:
            click.echo(f"  ❌ Health check failed: {e}")
            return False
    
    async def test_list_features(self) -> bool:
        """Test list features."""
        click.echo("\n🔍 Testing qa.list_features...")
        try:
            result = await self.call_tool("qa.list_features", {
                "with_documents": True,
                "limit": 10
            })
            
            if "error" in result:
                click.echo(f"  ❌ Error: {result['error']}")
                return False
            
            features_data = result["result"]
            features = features_data["features"]
            
            click.echo(f"  ✅ Found {len(features)} features (total: {features_data['total']})")
            
            for feature in features[:3]:  # Show first 3
                click.echo(f"    • {feature['name']}: {feature['description'][:50]}...")
                if feature.get('documents'):
                    click.echo(f"      Documents: {len(feature['documents'])}")
            
            return True
            
        except Exception as e:
            click.echo(f"  ❌ List features failed: {e}")
            return False
    
    async def test_docs_by_feature(self) -> bool:
        """Test docs by feature."""
        click.echo("\n🔍 Testing qa.docs_by_feature...")
        try:
            # First get a feature to test with
            features_result = await self.call_tool("qa.list_features", {"limit": 1})
            if "error" in features_result or not features_result["result"]["features"]:
                click.echo("  ⚠️  No features available to test with")
                return True
            
            test_feature = features_result["result"]["features"][0]
            
            result = await self.call_tool("qa.docs_by_feature", {
                "feature_name": test_feature["name"],
                "limit": 5
            })
            
            if "error" in result:
                click.echo(f"  ❌ Error: {result['error']}")
                return False
            
            docs_data = result["result"]
            documents = docs_data["documents"]
            
            click.echo(f"  ✅ Feature '{docs_data['feature']['name']}' has {len(documents)} documents")
            
            for doc in documents[:2]:  # Show first 2
                click.echo(f"    • {doc['title']}")
                click.echo(f"      Space: {doc['space']}")
                click.echo(f"      Labels: {', '.join(doc['labels'])}")
            
            return True
            
        except Exception as e:
            click.echo(f"  ❌ Docs by feature failed: {e}")
            return False
    
    async def test_search(self) -> bool:
        """Test search functionality."""
        click.echo("\n🔍 Testing qa.search...")
        try:
            # Test search queries
            test_queries = [
                "authentication testing",
                "API documentation",
                "deployment procedures"
            ]
            
            for query in test_queries:
                click.echo(f"\n  🔎 Searching for: '{query}'")
                
                result = await self.call_tool("qa.search", {
                    "query": query,
                    "top_k": 3,
                    "return_chunks": True
                })
                
                if "error" in result:
                    click.echo(f"    ❌ Error: {result['error']}")
                    continue
                
                search_data = result["result"]
                results = search_data["results"]
                
                click.echo(f"    ✅ Found {len(results)} results")
                
                for i, hit in enumerate(results[:2]):  # Show top 2
                    click.echo(f"      {i+1}. {hit['document']['title']} (score: {hit['score']:.3f})")
                    click.echo(f"         Feature: {hit['feature']['name']}")
                    if hit.get('chunk'):
                        chunk_text = hit['chunk']['text'][:100] + "..." if len(hit['chunk']['text']) > 100 else hit['chunk']['text']
                        click.echo(f"         Chunk: {chunk_text}")
            
            return True
            
        except Exception as e:
            click.echo(f"  ❌ Search failed: {e}")
            return False
    
    async def test_http_api(self) -> bool:
        """Test HTTP REST API endpoints."""
        click.echo("\n🔍 Testing HTTP REST API...")
        try:
            async with httpx.AsyncClient() as client:
                # Test health endpoint
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                click.echo("  ✅ GET /health")
                
                # Test features endpoint
                response = await client.get(f"{self.base_url}/features?limit=5")
                response.raise_for_status()
                click.echo("  ✅ GET /features")
                
                # Test search endpoint
                search_payload = {
                    "query": "testing procedures",
                    "top_k": 3
                }
                response = await client.post(f"{self.base_url}/search", json=search_payload)
                response.raise_for_status()
                click.echo("  ✅ POST /search")
                
                # Test tools info endpoint
                response = await client.get(f"{self.base_url}/tools")
                response.raise_for_status()
                tools_data = response.json()
                click.echo(f"  ✅ GET /tools ({len(tools_data['tools'])} tools listed)")
            
            return True
            
        except Exception as e:
            click.echo(f"  ❌ HTTP API test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests."""
        click.echo("🚀 Starting MCP QA Search Server tests...\n")
        
        tests = [
            ("Health Check", self.test_health),
            ("List Features", self.test_list_features),
            ("Docs by Feature", self.test_docs_by_feature),
            ("Search", self.test_search),
            ("HTTP API", self.test_http_api)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                if success:
                    passed += 1
                else:
                    click.echo(f"  ❌ {test_name} test failed")
            except Exception as e:
                click.echo(f"  ❌ {test_name} test crashed: {e}")
        
        click.echo(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            click.echo("🎉 All tests passed!")
            return True
        else:
            click.echo("💥 Some tests failed")
            return False


@click.command()
@click.option('--url', default='http://localhost:3000', help='Base URL of MCP server')
@click.option('--test', type=click.Choice(['all', 'health', 'features', 'docs', 'search', 'http']), 
              default='all', help='Which test to run')
def main(url, test):
    """Test MCP QA Search Server functionality."""
    
    client = MCPTestClient(url)
    
    async def run_test():
        if test == 'all':
            return await client.run_all_tests()
        elif test == 'health':
            return await client.test_health()
        elif test == 'features':
            return await client.test_list_features()
        elif test == 'docs':
            return await client.test_docs_by_feature()
        elif test == 'search':
            return await client.test_search()
        elif test == 'http':
            return await client.test_http_api()
    
    try:
        success = asyncio.run(run_test())
        exit_code = 0 if success else 1
        click.echo(f"\nTest completed with exit code: {exit_code}")
        exit(exit_code)
        
    except KeyboardInterrupt:
        click.echo("\n\nTests interrupted by user")
        exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
