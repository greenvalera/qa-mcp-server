#!/usr/bin/env python3
"""
MCP Local Server - stdio проксі для рефакторованого HTTP API сервера
Архітектура після рефакторингу:
- app/http_api.py: HTTP FastAPI сервер з JSON-RPC endpoints
- app/mcp_tools.py: Чисті QA функції з бізнес-логікою (без MCP декораторів)
- app/mcp_server.py: FastMCP сервер з декораторами (для прямого stdio)
- mcp_local.py: Проксі між Cursor і HTTP API (цей файл)
"""

import json
import sys
import urllib.request
import urllib.parse
from typing import Dict, Any, List


# Список інструментів з підкресленнями для Cursor (зрозумілі назви)
TOOLS = [
    {
        "name": "qa_search_documents",
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
    },
    {
        "name": "qa_search_testcases",
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
    },
    {
        "name": "qa_search_testcases_text",
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
    },
    {
        "name": "qa_list_features",
        "description": "List all features with descriptions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100, "description": "Maximum number of features"},
                "offset": {"type": "integer", "default": 0, "description": "Number of features to skip"}
            }
        }
    },
    {
        "name": "qa_docs_by_feature",
        "description": "Get documents for a specific feature",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string", "description": "Feature name"},
                "limit": {"type": "integer", "default": 50, "description": "Maximum number of documents"}
            }
        }
    },
    {
        "name": "qa_health",
        "description": "Check system health",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "qa_get_sections",
        "description": "Get list of QA sections (Checklist WEB, Checklist MOB, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100, "description": "Maximum number of sections"},
                "offset": {"type": "integer", "default": 0, "description": "Number of sections to skip"}
            }
        }
    },
    {
        "name": "qa_get_checklists",
        "description": "Get list of checklists, optionally filtered by section",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section_id": {"type": "integer", "description": "Section ID to filter by"},
                "limit": {"type": "integer", "default": 100, "description": "Maximum number of checklists"},
                "offset": {"type": "integer", "default": 0, "description": "Number of checklists to skip"}
            }
        }
    },
    {
        "name": "qa_get_testcases",
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
    },
    {
        "name": "qa_search_testcases",
        "description": "Search test cases by text in step or expected_result",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "section_id": {"type": "integer", "description": "Section ID to filter by"},
                "checklist_id": {"type": "integer", "description": "Checklist ID to filter by"},
                "limit": {"type": "integer", "default": 100, "description": "Maximum number of results"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "qa_get_configs",
        "description": "Get list of configurations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100, "description": "Maximum number of configs"},
                "offset": {"type": "integer", "default": 0, "description": "Number of configs to skip"}
            }
        }
    },
    {
        "name": "qa_get_statistics",
        "description": "Get QA structure statistics",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "qa_get_full_structure",
        "description": "Get full QA structure with hierarchy of sections, checklists and test cases",
        "inputSchema": {"type": "object", "properties": {}}
    },
]


def call_docker_server(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Викликає оновлений HTTP сервер через JSON-RPC"""
    # Конвертуємо qa_xxx в qa.xxx для HTTP сервера
    if method.startswith("qa_"):
        docker_method = method.replace("qa_", "qa.", 1)
    else:
        docker_method = method
    
    payload = {
        "jsonrpc": "2.0",
        "method": docker_method,
        "params": params,
        "id": 1
    }
    
    try:
        req = urllib.request.Request(
            "http://localhost:3000/jsonrpc",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        if "error" in result and result["error"] is not None:
            return {"error": f"Docker server error: {result['error']}", "success": False}
        
        # Повертаємо результат або пустий dict якщо результат None
        return result.get("result") or {}
        
    except Exception as e:
        return {"error": f"Failed to call Docker server: {str(e)}", "success": False}


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Обробляє MCP запити"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "qa-search",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        # Викликаємо оновлений HTTP сервер
        result = call_docker_server(tool_name, tool_args)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False)
                    }
                ]
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }

    elif method == "notifications/initialized":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """Основна функція для stdio MCP сервера"""
    print("MCP Local Server ready", file=sys.stderr)
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
