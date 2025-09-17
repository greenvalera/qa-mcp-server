#!/usr/bin/env python3
"""
MCP Common Module - спільні компоненти для MCP серверів
Містить загальні функції, схеми інструментів та обробники для локального та віддаленого MCP серверів
"""

import json
import sys
from typing import Dict, Any, List

# Список інструментів з підкресленнями для Cursor (зрозумілі назви)
TOOLS_SCHEMA = [
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

# Мапінг назв інструментів з підкресленнями на назви з крапками для HTTP серверів
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


class MCPHandler:
    """Базовий клас для обробки MCP запитів"""
    
    def __init__(self, server_name: str, server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
    
    def handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Обробляє запит ініціалізації MCP"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.server_version
                }
            }
        }
    
    def handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Обробляє запит списку інструментів"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS_SCHEMA
            }
        }
    
    def handle_tools_call(self, request_id: Any, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє виклик інструмента - повинен бути перевизначений в підкласах"""
        raise NotImplementedError("handle_tools_call must be implemented by subclasses")
    
    def handle_ping(self, request_id: Any) -> Dict[str, Any]:
        """Обробляє ping запит"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
    
    def handle_notifications_initialized(self, request_id: Any) -> Dict[str, Any]:
        """Обробляє notification про ініціалізацію"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Основний обробник MCP запитів"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return self.handle_initialize(request_id)
        elif method == "tools/list":
            return self.handle_tools_list(request_id)
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            return self.handle_tools_call(request_id, tool_name, tool_args)
        elif method == "ping":
            return self.handle_ping(request_id)
        elif method == "notifications/initialized":
            return self.handle_notifications_initialized(request_id)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


def create_mcp_response(request_id: Any, result: Any) -> Dict[str, Any]:
    """Створює стандартну MCP відповідь з результатом"""
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


def create_error_response(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    """Створює стандартну MCP відповідь з помилкою"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }


def run_stdio_server(handler: MCPHandler, debug: bool = False):
    """Запускає stdio MCP сервер з заданим обробником"""
    if debug:
        print(f"MCP Server '{handler.server_name}' ready", file=sys.stderr)
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = handler.handle_request(request)
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = create_error_response(
                    None, -32700, f"Parse error: {str(e)}"
                )
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
            except Exception as e:
                error_response = create_error_response(
                    None, -32603, f"Internal error: {str(e)}"
                )
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
    except KeyboardInterrupt:
        if debug:
            print(f"MCP Server '{handler.server_name}' stopped", file=sys.stderr)
        pass
