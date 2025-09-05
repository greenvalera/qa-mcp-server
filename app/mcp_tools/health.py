"""Health check tool."""

from typing import Any, Dict
from pydantic import BaseModel

from .base import MCPToolBase, MCPToolError


class HealthParams(BaseModel):
    """Parameters for qa.health tool (no parameters needed)."""
    pass


class HealthTool(MCPToolBase):
    """Tool for checking the health status of databases and connections."""
    
    @property
    def name(self) -> str:
        return "qa.health"
    
    @property
    def description(self) -> str:
        return "Check the health status of vector database, MySQL, and AI services"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute health check."""
        with self.measure_time() as timer:
            try:
                health_status = {
                    "vector_db": {"status": "unknown"},
                    "mysql": {"status": "unknown"},
                    "openai": {"status": "unknown"},
                    "ok": False
                }
                
                # Check Vector DB (Qdrant)
                try:
                    vector_stats = self.vector_repo.get_health_stats()
                    health_status["vector_db"] = vector_stats
                except Exception as e:
                    health_status["vector_db"] = {
                        "status": "error",
                        "error": str(e),
                        "collections": [],
                        "count": 0
                    }
                
                # Check MySQL
                try:
                    mysql_stats = self.mysql_repo.get_health_stats()
                    health_status["mysql"] = mysql_stats
                except Exception as e:
                    health_status["mysql"] = {
                        "status": "error",
                        "error": str(e),
                        "features": 0,
                        "documents": 0,
                        "associations": 0
                    }
                
                # Check OpenAI connections
                try:
                    embedder_ok = self.embedder.test_connection()
                    llm_ok = self.feature_tagger.test_connection()
                    
                    if embedder_ok and llm_ok:
                        health_status["openai"] = {
                            "status": "ok",
                            "embedder": "ok",
                            "llm": "ok",
                            "embedding_model": self.embedder.model,
                            "llm_model": self.feature_tagger.model
                        }
                    else:
                        health_status["openai"] = {
                            "status": "partial",
                            "embedder": "ok" if embedder_ok else "error",
                            "llm": "ok" if llm_ok else "error",
                            "embedding_model": self.embedder.model,
                            "llm_model": self.feature_tagger.model
                        }
                except Exception as e:
                    health_status["openai"] = {
                        "status": "error",
                        "error": str(e),
                        "embedder": "error",
                        "llm": "error"
                    }
                
                # Determine overall health
                vector_ok = health_status["vector_db"]["status"] == "ok"
                mysql_ok = health_status["mysql"]["status"] == "ok"
                openai_ok = health_status["openai"]["status"] in ["ok", "partial"]
                
                health_status["ok"] = vector_ok and mysql_ok and openai_ok
                
                # Add summary information
                if vector_ok and mysql_ok:
                    health_status["summary"] = {
                        "total_documents": health_status["mysql"].get("documents", 0),
                        "total_features": health_status["mysql"].get("features", 0),
                        "total_chunks": health_status["vector_db"].get("count", 0),
                        "has_data": (
                            health_status["mysql"].get("documents", 0) > 0 and
                            health_status["vector_db"].get("count", 0) > 0
                        )
                    }
                else:
                    health_status["summary"] = {
                        "total_documents": 0,
                        "total_features": 0,
                        "total_chunks": 0,
                        "has_data": False
                    }
                
                return self.create_response(
                    health_status,
                    took_ms=timer.elapsed_ms
                )
                
            except Exception as e:
                # If health check itself fails, return error status
                return self.create_response(
                    {
                        "vector_db": {"status": "error", "error": "Health check failed"},
                        "mysql": {"status": "error", "error": "Health check failed"},
                        "openai": {"status": "error", "error": "Health check failed"},
                        "ok": False,
                        "summary": {
                            "total_documents": 0,
                            "total_features": 0,
                            "total_chunks": 0,
                            "has_data": False
                        }
                    },
                    took_ms=timer.elapsed_ms,
                    error=f"Health check failed: {str(e)}"
                )
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'mysql_repo'):
            self.mysql_repo.close()
        if hasattr(self, 'vector_repo'):
            self.vector_repo.close()
