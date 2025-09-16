#!/usr/bin/env python3
"""
HTTP API Server - FastAPI сервер з HTTP endpoints та JSON-RPC для MCP
Використовує функції з mcp_tools.py для бізнес-логіки
"""

import json
import sys
import asyncio
from typing import Dict, Any, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .mcp_tools import (
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

# FastAPI app
app = FastAPI(
    title="QA HTTP API Server",
    description="HTTP API Server with QA tools and MCP JSON-RPC support",
    version="1.0.0"
)

# JSON-RPC models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[int] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

# Request models for HTTP endpoints
class SearchDocumentsRequest(BaseModel):
    query: str
    top_k: int = 10
    feature_names: Optional[List[str]] = None
    space_keys: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    return_chunks: bool = True

class SearchTestcasesRequest(BaseModel):
    query: str
    limit: int = 10
    min_similarity: float = 0.5
    section_id: Optional[int] = None
    checklist_id: Optional[int] = None
    test_group: Optional[str] = None
    functionality: Optional[str] = None
    priority: Optional[str] = None

# MCP Tools registry - всі інструменти з зрозумілими назвами
TOOLS = {
    "qa.search_documents": qa_search_documents,  # Пошук в документації/знаннях
    "qa.search_testcases": qa_search_testcases,  # Пошук в тесткейсах (AI)
    "qa.list_features": qa_list_features,
    "qa.docs_by_feature": qa_docs_by_feature,
    "qa.health": qa_health,
    "qa.get_sections": qa_get_sections,
    "qa.get_checklists": qa_get_checklists,
    "qa.get_testcases": qa_get_testcases,
    "qa.search_testcases_text": qa_search_testcases_text,  # Текстовий пошук тесткейсів
    "qa.get_configs": qa_get_configs,
    "qa.get_statistics": qa_get_statistics,
    "qa.get_full_structure": qa_get_full_structure
}

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    try:
        health_result = await qa_health()
        return health_result
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/jsonrpc")
async def jsonrpc_handler(request: JSONRPCRequest):
    """JSON-RPC endpoint for MCP tools"""
    try:
        method = request.method
        params = request.params
        
        # Handle standard MCP methods
        if method == "initialize":
            return JSONRPCResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "qa-search",
                        "version": "1.0.0"
                    }
                }
            )
        
        elif method == "tools/list":
            # Генеруємо список інструментів з TOOLS registry
            tools_list = []
            for tool_name in TOOLS.keys():
                # Базові схеми для кожного інструменту
                if tool_name == "qa.search_documents":
                    tool_schema = {
                        "name": tool_name,
                        "description": "🔍 Search in DOCUMENTATION and knowledge base - finds relevant docs, guides, and information chunks",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for documentation"},
                                "top_k": {"type": "integer", "default": 10, "description": "Number of documents to return"},
                                "feature_names": {"type": "array", "items": {"type": "string"}, "description": "Filter by feature names"},
                                "space_keys": {"type": "array", "items": {"type": "string"}, "description": "Filter by Confluence space keys"},
                                "return_chunks": {"type": "boolean", "default": True, "description": "Whether to return chunk information"}
                            },
                            "required": ["query"]
                        }
                    }
                elif tool_name == "qa.search_testcases":
                    tool_schema = {
                        "name": tool_name,
                        "description": "🧪 Search in TEST CASES using AI - finds specific tests by semantic similarity (step, expected_result)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for test cases"},
                                "limit": {"type": "integer", "default": 10, "description": "Maximum number of test cases"},
                                "min_similarity": {"type": "number", "default": 0.5, "description": "Minimum similarity (0.0-1.0)"},
                                "section_id": {"type": "integer", "description": "Filter by section ID"},
                                "checklist_id": {"type": "integer", "description": "Filter by checklist ID"},
                                "test_group": {"type": "string", "description": "Filter by test group (GENERAL or CUSTOM)"},
                                "priority": {"type": "string", "description": "Filter by priority"}
                            },
                            "required": ["query"]
                        }
                    }
                elif tool_name == "qa.search_testcases_text":
                    tool_schema = {
                        "name": tool_name,
                        "description": "📝 Search test cases by TEXT - simple text search in step and expected_result fields",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Text search query"},
                                "section_id": {"type": "integer", "description": "Section ID to filter by"},
                                "checklist_id": {"type": "integer", "description": "Checklist ID to filter by"},
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of results"}
                            },
                            "required": ["query"]
                        }
                    }
                elif tool_name == "qa.list_features":
                    tool_schema = {
                        "name": tool_name,
                        "description": "List all features with descriptions",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of features"},
                                "offset": {"type": "integer", "default": 0, "description": "Number of features to skip"}
                            }
                        }
                    }
                elif tool_name == "qa.docs_by_feature":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get documents for a specific feature",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "feature_name": {"type": "string", "description": "Feature name"},
                                "limit": {"type": "integer", "default": 50, "description": "Maximum number of documents"}
                            }
                        }
                    }
                elif tool_name == "qa.health":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Check system health",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                elif tool_name == "qa.get_sections":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get list of QA sections (Checklist WEB, Checklist MOB, etc.)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of sections"},
                                "offset": {"type": "integer", "default": 0, "description": "Number of sections to skip"}
                            }
                        }
                    }
                elif tool_name == "qa.get_checklists":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get list of checklists, optionally filtered by section",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "section_id": {"type": "integer", "description": "Section ID to filter by"},
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of checklists"},
                                "offset": {"type": "integer", "default": 0, "description": "Number of checklists to skip"}
                            }
                        }
                    }
                elif tool_name == "qa.get_testcases":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get list of test cases with filters",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "checklist_id": {"type": "integer", "description": "Checklist ID to filter by"},
                                "test_group": {"type": "string", "description": "Test group (GENERAL or CUSTOM)"},
                                "functionality": {"type": "string", "description": "Functionality to filter by"},
                                "priority": {"type": "string", "description": "Priority (LOW, MEDIUM, HIGH, CRITICAL)"},
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of test cases"},
                                "offset": {"type": "integer", "default": 0, "description": "Number of test cases to skip"}
                            }
                        }
                    }
                elif tool_name == "qa.get_configs":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get list of configurations",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "default": 100, "description": "Maximum number of configs"},
                                "offset": {"type": "integer", "default": 0, "description": "Number of configs to skip"}
                            }
                        }
                    }
                elif tool_name == "qa.get_statistics":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get QA structure statistics",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                elif tool_name == "qa.get_full_structure":
                    tool_schema = {
                        "name": tool_name,
                        "description": "Get full QA structure with hierarchy of sections, checklists and test cases",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                else:
                    # Fallback для невідомих інструментів
                    tool_schema = {
                        "name": tool_name,
                        "description": f"QA tool: {tool_name}",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                
                tools_list.append(tool_schema)
            
            return JSONRPCResponse(
                id=request.id,
                result={
                    "tools": tools_list
                }
            )
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name in TOOLS:
                result = await TOOLS[tool_name](**tool_args)
                return JSONRPCResponse(
                    id=request.id,
                    result={
                        "content": [
                            {
                                "type": "text", 
                                "text": json.dumps(result, ensure_ascii=False)
                            }
                        ]
                    }
                )
            else:
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                )
        
        elif method == "ping":
            return JSONRPCResponse(
                id=request.id,
                result={}
            )
        
        elif method == "notifications/initialized":
            # Notification methods should not have an id in the response
            return JSONRPCResponse(
                result={}
            )
        
        elif method in TOOLS:
            # Direct tool call
            result = await TOOLS[method](**params)
            return JSONRPCResponse(
                id=request.id,
                result=result
            )
        
        else:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            )
            
    except Exception as e:
        return JSONRPCResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )

# Direct HTTP endpoints for each tool
@app.post("/api/search_documents")
async def api_search_documents(request: SearchDocumentsRequest):
    """Direct HTTP endpoint for document search"""
    try:
        result = await qa_search_documents(
            query=request.query,
            top_k=request.top_k,
            feature_names=request.feature_names,
            space_keys=request.space_keys,
            filters=request.filters,
            return_chunks=request.return_chunks
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search_testcases")
async def api_search_testcases(request: SearchTestcasesRequest):
    """Direct HTTP endpoint for testcase search"""
    try:
        result = await qa_search_testcases(
            query=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity,
            section_id=request.section_id,
            checklist_id=request.checklist_id,
            test_group=request.test_group,
            functionality=request.functionality,
            priority=request.priority
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/features")
async def api_list_features(
    limit: int = 100,
    offset: int = 0,
    with_documents: bool = True
):
    """Direct HTTP endpoint for listing features"""
    try:
        result = await qa_list_features(
            limit=limit,
            offset=offset,
            with_documents=with_documents
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/features/{feature_name}/docs")
async def api_docs_by_feature(
    feature_name: str,
    limit: int = 50,
    offset: int = 0
):
    """Direct HTTP endpoint for getting docs by feature"""
    try:
        result = await qa_docs_by_feature(
            feature_name=feature_name,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def api_health():
    """Direct HTTP endpoint for health check"""
    try:
        result = await qa_health()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Stdio JSON-RPC handler for MCP clients
async def stdio_jsonrpc_handler():
    """Handle JSON-RPC over stdio for MCP clients"""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request_data = json.loads(line)
                request = JSONRPCRequest(**request_data)
                response = await jsonrpc_handler(request)
                print(json.dumps(response.dict(), ensure_ascii=False))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = JSONRPCResponse(
                    error={
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                )
                print(json.dumps(error_response.dict()))
                sys.stdout.flush()
                
            except Exception as e:
                error_response = JSONRPCResponse(
                    error={
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                )
                print(json.dumps(error_response.dict()))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in stdio handler: {e}", file=sys.stderr)

def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP clients
        print("Starting HTTP API server in stdio mode...", file=sys.stderr)
        asyncio.run(stdio_jsonrpc_handler())
    else:
        # Run HTTP server
        print(f"Starting HTTP API server on port {settings.app_port}")
        uvicorn.run(
            "app.http_api:app",
            host="0.0.0.0",
            port=settings.app_port,
            reload=settings.is_development
        )

if __name__ == "__main__":
    main()