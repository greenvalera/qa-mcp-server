"""Search tool for QA documents."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import MCPToolBase, MCPToolError
from ..config import settings


class SearchParams(BaseModel):
    """Parameters for qa.search tool."""
    
    query: str = Field(..., description="Search query")
    top_k: int = Field(
        default=10, 
        ge=1, 
        le=settings.max_top_k, 
        description="Number of results to return"
    )
    feature_names: Optional[List[str]] = Field(
        default=None, 
        description="Filter by feature names"
    )
    space_keys: Optional[List[str]] = Field(
        default=None, 
        description="Filter by Confluence space keys"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional filters"
    )
    return_chunks: bool = Field(
        default=True, 
        description="Whether to return chunk information"
    )


class SearchTool(MCPToolBase):
    """Search tool for finding relevant documents and chunks."""
    
    @property
    def name(self) -> str:
        return "qa.search"
    
    @property
    def description(self) -> str:
        return "Search for relevant documents and chunks in the QA knowledge base"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": settings.max_top_k,
                    "default": 10,
                    "description": "Number of results to return"
                },
                "feature_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by feature names"
                },
                "space_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by Confluence space keys"
                },
                "filters": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Additional filters"
                },
                "return_chunks": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to return chunk information"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search."""
        with self.measure_time() as timer:
            try:
                # Validate parameters
                search_params = self.validate_params(params, SearchParams)
                
                # Generate query embedding
                query_embedding = self.embedder.embed_text(search_params.query)
                if not query_embedding:
                    raise MCPToolError("Failed to generate query embedding")
                
                # Perform vector search
                search_results = self.vector_repo.search(
                    query_vector=query_embedding,
                    top_k=search_params.top_k,
                    feature_names=search_params.feature_names,
                    space_keys=search_params.space_keys,
                    filters=search_params.filters
                )
                
                # Format results
                formatted_results = []
                for result in search_results:
                    formatted_result = {
                        "score": result["score"],
                        "feature": result["feature"],
                        "document": result["document"]
                    }
                    
                    if search_params.return_chunks:
                        formatted_result["chunk"] = result["chunk"]
                    
                    formatted_results.append(formatted_result)
                
                return self.create_response(
                    {
                        "query": search_params.query,
                        "results": formatted_results
                    },
                    took_ms=timer.elapsed_ms
                )
                
            except MCPToolError:
                raise
            except Exception as e:
                raise MCPToolError(f"Search failed: {str(e)}")
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'mysql_repo'):
            self.mysql_repo.close()
        if hasattr(self, 'vector_repo'):
            self.vector_repo.close()
