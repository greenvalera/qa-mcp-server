#!/usr/bin/env python3
"""Simple MCP client to test FastMCP server."""

import json
import subprocess
import sys

def send_mcp_request(message):
    """Send MCP request with proper Content-Length headers."""
    body = json.dumps(message)
    content_length = len(body.encode('utf-8'))
    
    # Format with Content-Length header
    request = f"Content-Length: {content_length}\r\n\r\n{body}"
    return request

def test_fastmcp_server():
    """Test FastMCP server with proper MCP protocol."""
    
    # Start FastMCP server
    cmd = [
        "docker", "run", "--rm", "-i", "--network", "qa_mcp_qa_network",
        "-e", "MYSQL_DSN=mysql+pymysql://qa:qa@qa_mysql:3306/qa",
        "-e", "VECTORDB_URL=http://qa_qdrant:6333",
        "-e", "OPENAI_API_KEY=test",
        "qa_mcp-mcp-server", "python", "-m", "app.mcp_server"
    ]
    
    # Prepare requests
    initialize_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        },
        "id": 1
    }
    
    health_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "qa_health",
            "arguments": {}
        },
        "id": 2
    }
    
    # Format requests with Content-Length
    input_data = (
        send_mcp_request(initialize_request) +
        send_mcp_request(health_request)
    )
    
    print("🚀 Testing FastMCP server...")
    print("📨 Sending initialize + qa_health requests...")
    
    try:
        # Run FastMCP server
        process = subprocess.run(
            cmd,
            input=input_data,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print("📤 Server output:")
        print(process.stdout)
        
        if process.stderr:
            print("⚠️  Server errors:")
            print(process.stderr)
            
        print(f"✅ Process exit code: {process.returncode}")
        
    except subprocess.TimeoutExpired:
        print("⏰ Server timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_fastmcp_server()
