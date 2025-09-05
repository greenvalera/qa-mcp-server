"""Base classes for MCP tools."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError

from ..data import MySQLRepository, VectorDBRepository
from ..ai import OpenAIEmbedder, FeatureTagger
from ..config import settings


class MCPToolError(Exception):
    """Base exception for MCP tool errors."""
    pass


class MCPToolValidationError(MCPToolError):
    """Validation error for MCP tool inputs."""
    pass


class MCPToolBase(ABC):
    """Base class for MCP tools."""
    
    def __init__(self):
        """Initialize the tool."""
        self.mysql_repo = MySQLRepository()
        self.vector_repo = VectorDBRepository()
        self.embedder = OpenAIEmbedder()
        self.feature_tagger = FeatureTagger()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool input."""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass
    
    def validate_params(self, params: Dict[str, Any], schema_class: BaseModel) -> BaseModel:
        """Validate parameters against schema."""
        try:
            return schema_class(**params)
        except ValidationError as e:
            raise MCPToolValidationError(f"Invalid parameters: {e}")
    
    def create_response(
        self, 
        data: Any, 
        took_ms: Optional[int] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized response."""
        response = {}
        
        if error:
            response["error"] = error
            response["success"] = False
        else:
            response.update(data)
            response["success"] = True
        
        if took_ms is not None:
            response["took_ms"] = took_ms
        
        return response
    
    def measure_time(self):
        """Context manager to measure execution time."""
        return TimeContext()


class TimeContext:
    """Context manager for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
    
    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0
