#!/usr/bin/env python3
"""
MCP Local Server - stdio прослойка для локального HTTP API сервера
Використовує mcp_common для спільної функціональності
"""

import json
import urllib.request
from typing import Dict, Any
from mcp_client_common import MCPHandler, TOOL_NAME_MAPPING, create_mcp_response, run_stdio_server

# Адреса локального сервера
LOCAL_SERVER_URL = "http://localhost:3000"


class LocalMCPHandler(MCPHandler):
    """Обробник MCP запитів для локального сервера"""
    
    def __init__(self):
        super().__init__("qa-search-local", "1.0.0")
        self.local_url = LOCAL_SERVER_URL
    
    def call_local_server(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Викликає локальний HTTP API сервер через JSON-RPC"""
        try:
            # Конвертуємо qa_xxx в qa.xxx для HTTP сервера
            if method.startswith("qa_"):
                server_method = method.replace("qa_", "qa.", 1)
            else:
                server_method = method
            
            # Для локального сервера використовуємо прямий виклик методу
            payload = {
                "jsonrpc": "2.0",
                "method": server_method,
                "params": params,
                "id": 1
            }
            
            req = urllib.request.Request(
                f"{self.local_url}/jsonrpc",
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            if "error" in result and result["error"] is not None:
                return {"error": f"Local server error: {result['error']}", "success": False}
            
            # Повертаємо результат або пустий dict якщо результат None
            return result.get("result") or {}
            
        except Exception as e:
            return {"error": f"Failed to call local server: {str(e)}", "success": False}
    
    def handle_tools_call(self, request_id: Any, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє виклик інструмента через локальний сервер"""
        result = self.call_local_server(tool_name, tool_args)
        return create_mcp_response(request_id, result)


def main():
    """Основна функція для stdio MCP сервера"""
    handler = LocalMCPHandler()
    run_stdio_server(handler, debug=True)


if __name__ == "__main__":
    main()