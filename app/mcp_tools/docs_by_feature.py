"""Documents by feature tool."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator

from .base import MCPToolBase, MCPToolError


class DocsByFeatureParams(BaseModel):
    """Parameters for qa.docs_by_feature tool."""
    
    feature_name: Optional[str] = Field(
        default=None, 
        description="Feature name to search for"
    )
    feature_id: Optional[int] = Field(
        default=None, 
        description="Feature ID to search for"
    )
    limit: int = Field(
        default=50, 
        ge=1, 
        le=200, 
        description="Maximum number of documents to return"
    )
    offset: int = Field(
        default=0, 
        ge=0, 
        description="Number of documents to skip"
    )
    
    @validator('feature_name', 'feature_id')
    def validate_feature_identifier(cls, v, values):
        """Ensure at least one feature identifier is provided."""
        if 'feature_name' in values and 'feature_id' in values:
            feature_name = values.get('feature_name')
            feature_id = values.get('feature_id')
            if not feature_name and not feature_id:
                raise ValueError('Either feature_name or feature_id must be provided')
        return v


class DocsByFeatureTool(MCPToolBase):
    """Tool for getting all documents associated with a specific feature."""
    
    @property
    def name(self) -> str:
        return "qa.docs_by_feature"
    
    @property
    def description(self) -> str:
        return "Get all documents associated with a specific feature"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feature_name": {
                    "type": "string",
                    "description": "Feature name to search for"
                },
                "feature_id": {
                    "type": "integer",
                    "description": "Feature ID to search for"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 50,
                    "description": "Maximum number of documents to return"
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Number of documents to skip"
                }
            },
            "oneOf": [
                {"required": ["feature_name"]},
                {"required": ["feature_id"]}
            ]
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute docs by feature."""
        with self.measure_time() as timer:
            try:
                # Validate parameters
                docs_params = self.validate_params(params, DocsByFeatureParams)
                
                # Ensure at least one identifier is provided
                if not docs_params.feature_name and not docs_params.feature_id:
                    raise MCPToolError("Either feature_name or feature_id must be provided")
                
                # Get documents for the feature
                documents, total, feature = self.mysql_repo.get_documents_by_feature(
                    feature_id=docs_params.feature_id,
                    feature_name=docs_params.feature_name,
                    limit=docs_params.limit,
                    offset=docs_params.offset
                )
                
                if not feature:
                    # Feature not found
                    feature_identifier = docs_params.feature_name or str(docs_params.feature_id)
                    raise MCPToolError(f"Feature not found: {feature_identifier}")
                
                # Format documents
                formatted_documents = []
                for doc in documents:
                    doc_data = {
                        "id": doc.id,
                        "title": doc.title,
                        "url": doc.url,
                        "space": doc.space_key,
                        "labels": doc.labels or [],
                        "confluence_page_id": doc.confluence_page_id,
                        "version": doc.version,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
                    }
                    formatted_documents.append(doc_data)
                
                return self.create_response(
                    {
                        "feature": {
                            "id": feature.id,
                            "name": feature.name,
                            "description": feature.description or ""
                        },
                        "documents": formatted_documents,
                        "total": total,
                        "limit": docs_params.limit,
                        "offset": docs_params.offset
                    },
                    took_ms=timer.elapsed_ms
                )
                
            except MCPToolError:
                raise
            except Exception as e:
                raise MCPToolError(f"Get documents by feature failed: {str(e)}")
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'mysql_repo'):
            self.mysql_repo.close()
        if hasattr(self, 'vector_repo'):
            self.vector_repo.close()
