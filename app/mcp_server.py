#!/usr/bin/env python3
"""MCP QA Search Server using official MCP Python SDK."""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP, Context

from .config import settings
from .data import MySQLRepository, VectorDBRepository
from .ai import OpenAIEmbedder, FeatureTagger
from .models import Base


# Configure logging to stderr (not stdout for STDIO servers)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("qa-search")

# Initialize repositories and services
mysql_repo = MySQLRepository()
vector_repo = VectorDBRepository()
embedder = OpenAIEmbedder()
feature_tagger = FeatureTagger()


@mcp.tool()
async def qa_search(
    query: str,
    top_k: int = 10,
    feature_names: Optional[List[str]] = None,
    space_keys: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    return_chunks: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Search for relevant documents and chunks in the QA knowledge base.
    
    Args:
        query: Search query
        top_k: Number of results to return (1-50)
        feature_names: Filter by feature names
        space_keys: Filter by Confluence space keys
        filters: Additional filters
        return_chunks: Whether to return chunk information
    """
    try:
        # Use context logging if available, fallback to logger
        if ctx:
            await ctx.info(f"Executing search for query: {query}")
        else:
            logger.info(f"Executing search for query: {query}")
        
        # Validate top_k
        if top_k < 1 or top_k > settings.max_top_k:
            return {
                "success": False,
                "error": f"top_k must be between 1 and {settings.max_top_k}"
            }
        
        # Generate query embedding
        query_embedding = embedder.embed_text(query)
        if not query_embedding:
            return {
                "success": False,
                "error": "Failed to generate query embedding"
            }
        
        # Perform vector search
        search_results = vector_repo.search(
            query_vector=query_embedding,
            top_k=top_k,
            feature_names=feature_names,
            space_keys=space_keys,
            filters=filters
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_result = {
                "score": result["score"],
                "feature": result["feature"],
                "document": result["document"]
            }
            
            if return_chunks:
                formatted_result["chunk"] = result["chunk"]
            
            formatted_results.append(formatted_result)
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }
        
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        else:
            logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


@mcp.tool()
async def qa_list_features(
    limit: int = 100,
    with_documents: bool = True,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """List all features with descriptions and associated document names.
    
    Args:
        limit: Maximum number of features to return (1-500)
        with_documents: Include document names for each feature
        offset: Number of features to skip
    """
    try:
        if ctx:
            await ctx.info(f"Listing features with limit={limit}, offset={offset}")
        else:
            logger.info(f"Listing features with limit={limit}, offset={offset}")
        
        # Validate parameters
        if limit < 1 or limit > 500:
            return {
                "success": False,
                "error": "limit must be between 1 and 500"
            }
        
        if offset < 0:
            return {
                "success": False,
                "error": "offset must be >= 0"
            }
        
        # Get features from database
        features, total = mysql_repo.list_features(
            limit=limit,
            offset=offset,
            with_documents=with_documents
        )
        
        # Format results
        formatted_features = []
        for feature in features:
            feature_data = {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description or ""
            }
            
            if with_documents:
                # Get document titles for this feature
                document_names = []
                if hasattr(feature, 'documents') and feature.documents:
                    document_names = [doc.title for doc in feature.documents]
                feature_data["documents"] = document_names
            
            formatted_features.append(feature_data)
        
        return {
            "success": True,
            "features": formatted_features,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List features failed: {str(e)}")
        return {
            "success": False,
            "error": f"List features failed: {str(e)}"
        }


@mcp.tool()
async def qa_docs_by_feature(
    feature_name: Optional[str] = None,
    feature_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """Get documents for a specific feature.
    
    Args:
        feature_name: Feature name (either this or feature_id required)
        feature_id: Feature ID (either this or feature_name required)
        limit: Maximum number of documents to return (1-200)
        offset: Number of documents to skip
    """
    try:
        logger.info(f"Getting docs for feature: {feature_name or feature_id}")
        
        # Validate parameters
        if not feature_name and not feature_id:
            return {
                "success": False,
                "error": "Either feature_name or feature_id must be provided"
            }
        
        if limit < 1 or limit > 200:
            return {
                "success": False,
                "error": "limit must be between 1 and 200"
            }
        
        if offset < 0:
            return {
                "success": False,
                "error": "offset must be >= 0"
            }
        
        # Get documents from database
        documents, total, feature = mysql_repo.get_documents_by_feature(
            feature_name=feature_name,
            feature_id=feature_id,
            limit=limit,
            offset=offset
        )
        
        # Format results
        formatted_documents = []
        for doc in documents:
            doc_data = {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
                "space_key": doc.space_key,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            formatted_documents.append(doc_data)
        
        return {
            "success": True,
            "feature_name": feature_name,
            "feature_id": feature_id,
            "documents": formatted_documents,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Get documents by feature failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get documents by feature failed: {str(e)}"
        }


@mcp.tool()
async def qa_health(ctx: Context = None) -> Dict[str, Any]:
    """Check system health.
    
    Returns status of databases and services.
    """
    try:
        if ctx:
            await ctx.info("Performing health check")
        else:
            logger.info("Performing health check")
        
        health_status = {
            "success": True,
            "timestamp": asyncio.get_event_loop().time(),
            "services": {}
        }
        
        # Check MySQL connection
        try:
            mysql_repo.get_session().execute("SELECT 1").fetchone()
            health_status["services"]["mysql"] = {"status": "healthy", "message": "Connection OK"}
        except Exception as e:
            health_status["services"]["mysql"] = {"status": "unhealthy", "message": str(e)}
            health_status["success"] = False
        
        # Check Vector DB connection
        try:
            vector_repo.health_check()
            health_status["services"]["vectordb"] = {"status": "healthy", "message": "Connection OK"}
        except Exception as e:
            health_status["services"]["vectordb"] = {"status": "unhealthy", "message": str(e)}
            health_status["success"] = False
        
        # Check OpenAI embedder
        try:
            # Just check if we have the API key
            if embedder.client.api_key:
                health_status["services"]["openai"] = {"status": "healthy", "message": "API key configured"}
            else:
                health_status["services"]["openai"] = {"status": "unhealthy", "message": "No API key"}
                health_status["success"] = False
        except Exception as e:
            health_status["services"]["openai"] = {"status": "unhealthy", "message": str(e)}
            health_status["success"] = False
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "success": False,
            "error": f"Health check failed: {str(e)}"
        }


async def initialize_server():
    """Initialize the server and create database tables if needed."""
    try:
        logger.info("Initializing MCP QA Search Server...")
        
        # Create MySQL tables if they don't exist
        mysql_repo.create_tables()
        logger.info("Database tables initialized successfully")
        
    except Exception as e:
        logger.warning(f"Failed to initialize database tables: {e}")


async def cleanup_server():
    """Clean up resources."""
    try:
        logger.info("Cleaning up server resources...")
        
        # Close database connections
        if mysql_repo:
            mysql_repo.close()
        
        if vector_repo:
            vector_repo.close()
            
        logger.info("Server cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point for the MCP server."""
    try:
        # Initialize server
        asyncio.run(initialize_server())
        
        # Run the FastMCP server with stdio transport (default)
        logger.info("Starting MCP QA Search Server...")
        mcp.run()  # FastMCP 2.x uses stdio by default
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        asyncio.run(cleanup_server())


if __name__ == "__main__":
    main()
