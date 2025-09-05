"""List features tool."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from .base import MCPToolBase, MCPToolError


class ListFeaturesParams(BaseModel):
    """Parameters for qa.list_features tool."""
    
    with_documents: bool = Field(
        default=True, 
        description="Include document names for each feature"
    )
    limit: int = Field(
        default=100, 
        ge=1, 
        le=500, 
        description="Maximum number of features to return"
    )
    offset: int = Field(
        default=0, 
        ge=0, 
        description="Number of features to skip"
    )


class ListFeaturesTool(MCPToolBase):
    """Tool for listing features with descriptions and associated documents."""
    
    @property
    def name(self) -> str:
        return "qa.list_features"
    
    @property
    def description(self) -> str:
        return "List all features with descriptions and associated document names"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "with_documents": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include document names for each feature"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 100,
                    "description": "Maximum number of features to return"
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Number of features to skip"
                }
            }
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list features."""
        with self.measure_time() as timer:
            try:
                # Validate parameters
                list_params = self.validate_params(params, ListFeaturesParams)
                
                # Get features from database
                features, total = self.mysql_repo.list_features(
                    limit=list_params.limit,
                    offset=list_params.offset,
                    with_documents=list_params.with_documents
                )
                
                # Format results
                formatted_features = []
                for feature in features:
                    feature_data = {
                        "id": feature.id,
                        "name": feature.name,
                        "description": feature.description or ""
                    }
                    
                    if list_params.with_documents:
                        # Get document titles for this feature
                        document_names = []
                        if hasattr(feature, 'documents') and feature.documents:
                            document_names = [doc.title for doc in feature.documents]
                        feature_data["documents"] = document_names
                    
                    formatted_features.append(feature_data)
                
                return self.create_response(
                    {
                        "features": formatted_features,
                        "total": total,
                        "limit": list_params.limit,
                        "offset": list_params.offset
                    },
                    took_ms=timer.elapsed_ms
                )
                
            except MCPToolError:
                raise
            except Exception as e:
                raise MCPToolError(f"List features failed: {str(e)}")
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'mysql_repo'):
            self.mysql_repo.close()
        if hasattr(self, 'vector_repo'):
            self.vector_repo.close()
