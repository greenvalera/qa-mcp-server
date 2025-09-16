#!/usr/bin/env python3
"""
MCP Remote Server - stdio прослойка для віддаленого HTTP API сервера
Аналогічно до mcp_local.py, але підключається до віддаленого сервера
"""

import json
import sys
import urllib.request
import urllib.parse
from typing import Dict, Any, List

# Адреса віддаленого сервера
REMOTE_SERVER_URL = "http://10.11.0.128:3000"

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
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
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
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "qa_get_full_structure",
        "description": "Get full QA structure with hierarchy of sections, checklists and test cases",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Мапінг назв інструментів з підкресленнями на назви з крапками для віддаленого сервера
TOOL_NAME_MAPPING = {
    "qa_search_documents": "qa.search_documents",
    "qa_search_testcases": "qa.search_testcases",
    "qa_search_testcases_text": "qa.search_testcases_text",
    "qa_list_features": "qa.list_features",
    "qa_docs_by_feature": "qa.docs_by_feature",
    "qa_health": "qa.health",
    "qa_get_sections": "qa.get_sections",
    "qa_get_checklists": "qa.get_checklists",
    "qa_get_testcases": "qa.get_testcases",
    "qa_get_configs": "qa.get_configs",
    "qa_get_statistics": "qa.get_statistics",
    "qa_get_full_structure": "qa.get_full_structure"
}


def call_remote_server(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Викликає віддалений HTTP API сервер"""
    try:
        # Мапимо назву інструмента
        remote_method = TOOL_NAME_MAPPING.get(method, method)
        
        # Формуємо JSON-RPC запит
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": remote_method,
                "arguments": params
            },
            "id": 1
        }
        
        # Відправляємо запит
        data = json.dumps(jsonrpc_request).encode('utf-8')
        req = urllib.request.Request(
            f"{REMOTE_SERVER_URL}/jsonrpc",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'error' in result and result['error']:
                return {"error": result['error']['message'], "success": False}
            
            # Розпаковуємо відповідь MCP
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content']
                if content and len(content) > 0 and 'text' in content[0]:
                    return json.loads(content[0]['text'])
            
            return {"error": "Invalid response format", "success": False}

        
    except Exception as e:
        return {"error": f"Failed to call remote server: {str(e)}", "success": False}


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
                    "name": "qa-search-remote",
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
        
        # Викликаємо віддалений HTTP сервер
        result = call_remote_server(tool_name, tool_args)
        
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
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = handle_request(request)
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    },
                    "id": None
                }
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": None
                }
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
