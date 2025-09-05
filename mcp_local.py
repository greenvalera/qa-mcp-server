#!/usr/bin/env python3
"""Local MCP server with Docker backend."""

import json
import sys
import subprocess
import time
from typing import Dict, Any

# Mock tools data - using underscore names for Cursor compatibility
TOOLS = [
    {
        "name": "qa_search",
        "description": "Search for relevant documents and chunks in the QA knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
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
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "qa_docs_by_feature",
        "description": "Get documents for a specific feature", 
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string", "description": "Feature name"}
            },
            "required": ["feature_name"]
        }
    },
    {
        "name": "qa_health",
        "description": "Check system health",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

def create_response(result: Any, request_id: Any) -> Dict[str, Any]:
    """Create JSON-RPC response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }

def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP request."""
    method = request.get("method")
    request_id = request.get("id")
    
    if method == "initialize":
        return create_response({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "qa-search-server", "version": "0.1.0"}
        }, request_id)
    
    elif method == "tools/list":
        return create_response({"tools": TOOLS}, request_id)
    
    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Call real Docker server via HTTP API
        try:
            import urllib.request
            import urllib.parse
            
            # Create JSON-RPC request for HTTP API
            # Convert tool name from qa_health to qa.health format
            if tool_name and tool_name.startswith("qa_"):
                method_name = tool_name.replace("_", ".", 1)
            else:
                method_name = tool_name
            
                
            docker_request = {
                "jsonrpc": "2.0",
                "method": method_name,
                "params": arguments,
                "id": 1
            }
            
            # Call HTTP API
            data = json.dumps(docker_request).encode('utf-8')
            req = urllib.request.Request(
                'http://localhost:3000/jsonrpc',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                docker_response = json.loads(response_data)
                
                if "result" in docker_response:
                    # Format the result for MCP
                    real_result = docker_response["result"]
                    return create_response({
                        "content": [{"type": "text", "text": json.dumps(real_result, indent=2)}]
                    }, request_id)
            
            # Fallback to mock if HTTP fails
            result = {"error": "HTTP server unavailable", "tool": tool_name, "arguments": arguments}
            
        except Exception as e:
            # Fallback to mock on error
            result = {"error": f"Failed to call Docker server: {str(e)}", "tool": tool_name}
            
        return create_response({
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
        }, request_id)
    
    elif method == "ping":
        return create_response({}, request_id)
    
    elif method == "notifications/initialized":
        return create_response({}, request_id)
    
    else:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id
        }

def main():
    """Main stdio loop."""
    try:
        # Send initial ready signal
        sys.stderr.write("MCP Local Server ready\n")
        sys.stderr.flush()
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = handle_request(request)
                print(json.dumps(response, separators=(',', ':')))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                    "id": None
                }
                print(json.dumps(error_response, separators=(',', ':')))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0", 
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                    "id": None
                }
                print(json.dumps(error_response, separators=(',', ':')))
                sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stderr.write("MCP Local Server shutting down\n")
    except Exception as e:
        sys.stderr.write(f"MCP Local Server error: {e}\n")

if __name__ == "__main__":
    main()

