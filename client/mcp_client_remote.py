#!/usr/bin/env python3
"""
MCP Remote Server - stdio прослойка для віддаленого HTTP API сервера
Використовує mcp_common для спільної функціональності
"""

import json
import urllib.request
from typing import Dict, Any
from mcp_client_common import MCPHandler, TOOL_NAME_MAPPING, create_mcp_response, run_stdio_server

# Адреса віддаленого сервера
REMOTE_SERVER_URL = "http://10.11.0.128:3000"


class RemoteMCPHandler(MCPHandler):
    """Обробник MCP запитів для віддаленого сервера"""
    
    def __init__(self):
        super().__init__("qa-search-remote", "1.0.0")
        self.remote_url = REMOTE_SERVER_URL
    
    def call_remote_server(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
                f"{self.remote_url}/jsonrpc",
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
    
    def handle_tools_call(self, request_id: Any, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє виклик інструмента через віддалений сервер"""
        result = self.call_remote_server(tool_name, tool_args)
        return create_mcp_response(request_id, result)


def main():
    """Основна функція для stdio MCP сервера"""
    handler = RemoteMCPHandler()
    run_stdio_server(handler, debug=False)


if __name__ == "__main__":
    main()