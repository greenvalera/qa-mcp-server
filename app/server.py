"""MCP QA Search Server main application."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from .config import settings
from .models import Base
from .data import MySQLRepository
from .mcp_tools import SearchTool, ListFeaturesTool, DocsByFeatureTool, HealthTool
from .mcp_tools.base import MCPToolError, MCPToolValidationError


# Initialize FastAPI app
app = FastAPI(
    title="MCP QA Search Server",
    description="Model Context Protocol server for QA document search",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tools
TOOLS = {
    "qa.search": SearchTool(),
    "qa.list_features": ListFeaturesTool(),
    "qa.docs_by_feature": DocsByFeatureTool(),
    "qa.health": HealthTool()
}



# Pydantic models for HTTP API
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    feature_names: Optional[List[str]] = None
    space_keys: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    return_chunks: bool = True


class ListFeaturesRequest(BaseModel):
    with_documents: bool = True
    limit: int = 100
    offset: int = 0


class DocsByFeatureRequest(BaseModel):
    feature_name: Optional[str] = None
    feature_id: Optional[int] = None
    limit: int = 50
    offset: int = 0


# JSON-RPC models
class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database tables."""
    try:
        # Create MySQL tables if they don't exist
        mysql_repo = MySQLRepository()
        mysql_repo.create_tables()
        mysql_repo.close()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize database tables: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    for tool in TOOLS.values():
        if hasattr(tool, 'close'):
            tool.close()


# HTTP API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_tool = TOOLS["qa.health"]
        result = await health_tool.execute({})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_documents(request: SearchRequest):
    """Search for documents."""
    try:
        search_tool = TOOLS["qa.search"]
        result = await search_tool.execute(request.dict())
        return result
    except MCPToolValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MCPToolError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/features")
async def list_features(
    with_documents: bool = True,
    limit: int = 100,
    offset: int = 0
):
    """List features."""
    try:
        list_tool = TOOLS["qa.list_features"]
        params = {
            "with_documents": with_documents,
            "limit": limit,
            "offset": offset
        }
        result = await list_tool.execute(params)
        return result
    except MCPToolValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MCPToolError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/features/{feature_identifier}/documents")
async def get_documents_by_feature(
    feature_identifier: str,
    limit: int = 50,
    offset: int = 0
):
    """Get documents for a feature (by ID or name)."""
    try:
        docs_tool = TOOLS["qa.docs_by_feature"]
        
        # Try to parse as integer (feature ID), otherwise treat as name
        params = {"limit": limit, "offset": offset}
        try:
            feature_id = int(feature_identifier)
            params["feature_id"] = feature_id
        except ValueError:
            params["feature_name"] = feature_identifier
        
        result = await docs_tool.execute(params)
        return result
    except MCPToolValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MCPToolError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





# JSON-RPC endpoint
@app.post("/jsonrpc")
async def jsonrpc_handler(request: JsonRpcRequest):
    """Handle JSON-RPC requests for MCP tools."""
    try:
        # Check if method exists in our tools
        if request.method not in TOOLS:
            error = JsonRpcError(
                code=-32601,
                message=f"Method not found: {request.method}",
                data={"available_methods": list(TOOLS.keys())}
            )
            return JsonRpcResponse(error=error.dict(), id=request.id)
        
        # Execute tool
        tool = TOOLS[request.method]
        params = request.params or {}
        result = await tool.execute(params)
        
        return JsonRpcResponse(result=result, id=request.id)
        
    except MCPToolValidationError as e:
        error = JsonRpcError(code=-32602, message="Invalid params", data=str(e))
        return JsonRpcResponse(error=error.dict(), id=request.id)
    except MCPToolError as e:
        error = JsonRpcError(code=-32603, message="Internal error", data=str(e))
        return JsonRpcResponse(error=error.dict(), id=request.id)
    except ValidationError as e:
        error = JsonRpcError(code=-32700, message="Parse error", data=str(e))
        return JsonRpcResponse(error=error.dict(), id=request.id)
    except Exception as e:
        error = JsonRpcError(code=-32603, message="Internal error", data=str(e))
        return JsonRpcResponse(error=error.dict(), id=request.id)


# MCP Tools info endpoint
@app.get("/tools")
async def list_mcp_tools():
    """List available MCP tools."""
    tools_info = []
    for name, tool in TOOLS.items():
        tools_info.append({
            "name": name,
            "description": tool.description,
            "input_schema": tool.input_schema
        })
    return {"tools": tools_info}




# Stdio JSON-RPC handler for MCP
async def stdio_jsonrpc_handler():
    """Handle JSON-RPC over stdio for MCP clients using Content-Length framing."""

    async def read_message() -> Optional[Dict[str, Any]]:
        """Read one MCP-framed message from stdin (Content-Length headers)."""
        headers: Dict[str, str] = {}
        # Read headers
        while True:
            line = await asyncio.to_thread(sys.stdin.buffer.readline)
            if not line:
                return None
            try:
                decoded = line.decode("ascii", errors="ignore")
            except Exception:
                decoded = ""
            decoded_stripped = decoded.strip("\r\n")
            if decoded_stripped == "":
                break
            if ":" in decoded_stripped:
                key, value = decoded_stripped.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0") or "0")
        if content_length <= 0:
            return None
        # Read body
        body = b""
        remaining = content_length
        while remaining > 0:
            chunk = await asyncio.to_thread(sys.stdin.buffer.read, remaining)
            if not chunk:
                return None
            body += chunk
            remaining -= len(chunk)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error", "data": str(e)},
            }

    def write_message(payload: Dict[str, Any]) -> None:
        """Write one MCP-framed message to stdout (Content-Length headers)."""
        try:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            body_bytes = json.dumps({
                "jsonrpc": "2.0",
                "id": payload.get("id") if isinstance(payload, dict) else None,
                "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            }).encode("utf-8")
        header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("ascii")
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.write(body_bytes)
        sys.stdout.buffer.flush()

    while True:
        try:
            incoming = await read_message()
            if incoming is None:
                break

            if isinstance(incoming, dict) and "error" in incoming and "method" not in incoming:
                write_message(incoming)
                continue

            try:
                request = JsonRpcRequest(**incoming)
            except ValidationError as e:
                error_response = JsonRpcResponse(
                    error=JsonRpcError(code=-32700, message="Parse error", data=str(e)).dict(),
                    id=incoming.get("id") if isinstance(incoming, dict) else None,
                )
                write_message(error_response.dict(exclude_unset=True))
                continue

            try:
                response_model = await jsonrpc_handler(request)
                write_message(response_model.dict(exclude_unset=True))
            except Exception as e:
                error_response = JsonRpcResponse(
                    error=JsonRpcError(code=-32603, message="Internal error", data=str(e)).dict(),
                    id=request.id,
                )
                write_message(error_response.dict(exclude_unset=True))

        except KeyboardInterrupt:
            break
        except Exception as e:
            # Log error and continue
            print(f"Error in stdio handler: {e}", file=sys.stderr)


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP clients
        print("Starting MCP server in stdio mode...", file=sys.stderr)
        asyncio.run(stdio_jsonrpc_handler())
    else:
        # Run HTTP server
        print(f"Starting MCP server on port {settings.app_port}")
        uvicorn.run(
            "app.server:app",
            host="0.0.0.0",
            port=settings.app_port,
            reload=settings.is_development
        )


if __name__ == "__main__":
    main()
