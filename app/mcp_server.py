#!/usr/bin/env python3
"""
MCP Server - FastMCP сервер з декораторами для stdio MCP клієнтів
Використовує функції з mcp_tools.py для бізнес-логіки
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP, Context

from .config import settings
from .mcp_tools import (
    qa_search_documents,
    qa_search_testcases,
    qa_search_testcases_text,
    qa_list_features,
    qa_docs_by_feature,
    qa_health,
    qa_get_sections,
    qa_get_checklists,
    qa_get_testcases,
    qa_get_configs,
    qa_get_statistics,
    qa_get_full_structure,
    qa_update_embeddings
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("qa-testcases")


@mcp.tool()
async def qa_get_sections_mcp(
    limit: int = 100,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """Отримує список QA секцій (Checklist WEB, Checklist MOB, etc.).
    
    Args:
        limit: Максимальна кількість секцій для повернення (1-500)
        offset: Кількість секцій для пропуску
    """
    try:
        if ctx:
            await ctx.info(f"Getting QA sections with limit={limit}, offset={offset}")
        
        # Використовуємо функцію з mcp_tools.py
        result = await qa_get_sections(limit=limit, offset=offset)
        return result
        
    except Exception as e:
        logger.error(f"Get QA sections failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get QA sections failed: {str(e)}"
        }


@mcp.tool()
async def qa_get_checklists(
    section_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """Отримує список чекліст, опціонально фільтрує по секції.
    
    Args:
        section_id: ID секції для фільтрації (опціонально)
        limit: Максимальна кількість чекліст для повернення (1-200)
        offset: Кількість чекліст для пропуску
    """
    try:
        if ctx:
            await ctx.info(f"Getting checklists for section_id={section_id}")
        
        # Validate parameters
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
        
        checklists, total = qa_repo.get_checklists(
            section_id=section_id,
            limit=limit,
            offset=offset
        )
        
        formatted_checklists = []
        for checklist in checklists:
            checklist_data = {
                "id": checklist.id,
                "title": checklist.title,
                "description": checklist.description or "",
                "url": checklist.url,
                "confluence_page_id": checklist.confluence_page_id,
                "section_id": checklist.section_id,
                "testcases_count": len(checklist.testcases) if checklist.testcases else 0,
                "configs_count": len(checklist.configs) if checklist.configs else 0,
                "updated_at": checklist.updated_at.isoformat() if checklist.updated_at else None
            }
            formatted_checklists.append(checklist_data)
        
        return {
            "success": True,
            "checklists": formatted_checklists,
            "total": total,
            "limit": limit,
            "offset": offset,
            "section_id": section_id
        }
        
    except Exception as e:
        logger.error(f"Get checklists failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get checklists failed: {str(e)}"
        }


@mcp.tool()
async def qa_get_testcases(
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    subcategory: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """Отримує список тесткейсів з фільтрами.
    
    Args:
        checklist_id: ID чекліста для фільтрації (опціонально)
        test_group: Група тестів (GENERAL або CUSTOM)
        functionality: Функціональність (конкретна функціональність в межах test_group)
        subcategory: Субкатегорія (належність до субсторінки)
        priority: Пріоритет (LOW, MEDIUM, HIGH, CRITICAL)
        limit: Максимальна кількість тесткейсів (1-500)
        offset: Кількість тесткейсів для пропуску
    """
    try:
        if ctx:
            await ctx.info(f"Getting testcases with filters: checklist_id={checklist_id}, test_group={test_group}")
        
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
        
        # Validate enum values
        if test_group and test_group not in ['GENERAL', 'CUSTOM']:
            return {
                "success": False,
                "error": "test_group must be GENERAL or CUSTOM"
            }
        
        if priority and priority not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            return {
                "success": False,
                "error": "priority must be LOW, MEDIUM, HIGH, or CRITICAL"
            }
        
        testcases, total = qa_repo.get_testcases(
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            subcategory=subcategory,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        formatted_testcases = []
        for testcase in testcases:
            testcase_data = {
                "id": testcase.id,
                "step": testcase.step,
                "expected_result": testcase.expected_result,
                "screenshot": testcase.screenshot,
                "priority": testcase.priority.value if testcase.priority else None,
                "test_group": testcase.test_group.value if testcase.test_group else None,
                "functionality": testcase.functionality,
                "subcategory": testcase.subcategory,
                "order_index": testcase.order_index,
                "checklist_id": testcase.checklist_id,
                "config_id": testcase.config_id,
                "qa_auto_coverage": testcase.qa_auto_coverage
            }
            formatted_testcases.append(testcase_data)
        
        return {
            "success": True,
            "testcases": formatted_testcases,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "checklist_id": checklist_id,
                "test_group": test_group,
                "functionality": functionality,
                "subcategory": subcategory,
                "priority": priority
            }
        }
        
    except Exception as e:
        logger.error(f"Get testcases failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get testcases failed: {str(e)}"
        }


@mcp.tool()
async def qa_search_testcases(
    query: str,
    section_id: Optional[int] = None,
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    ctx: Context = None
) -> Dict[str, Any]:
    """Пошук тесткейсів за текстом у step або expected_result.
    
    Args:
        query: Пошуковий запит
        section_id: ID секції для фільтрації (опціонально)
        checklist_id: ID чекліста для фільтрації (опціонально)
        test_group: Група тестів (GENERAL або CUSTOM)
        functionality: Функціональність (конкретна функціональність)
        priority: Пріоритет (LOW, MEDIUM, HIGH, CRITICAL)
        limit: Максимальна кількість результатів (1-200)
    """
    try:
        if ctx:
            await ctx.info(f"Searching testcases for query: {query}")
        
        # Validate parameters
        if not query or len(query.strip()) < 2:
            return {
                "success": False,
                "error": "query must be at least 2 characters long"
            }
        
        if limit < 1 or limit > 200:
            return {
                "success": False,
                "error": "limit must be between 1 and 200"
            }
        
        # Validate enum values
        if test_group and test_group not in ['GENERAL', 'CUSTOM']:
            return {
                "success": False,
                "error": "test_group must be GENERAL or CUSTOM"
            }
        
        if priority and priority not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            return {
                "success": False,
                "error": "priority must be LOW, MEDIUM, HIGH, or CRITICAL"
            }
        
        testcases = qa_repo.search_testcases(
            query=query.strip(),
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
            limit=limit
        )
        
        formatted_testcases = []
        for testcase in testcases:
            testcase_data = {
                "id": testcase.id,
                "step": testcase.step,
                "expected_result": testcase.expected_result,
                "screenshot": testcase.screenshot,
                "priority": testcase.priority.value if testcase.priority else None,
                "test_group": testcase.test_group.value if testcase.test_group else None,
                "functionality": testcase.functionality,
                "subcategory": testcase.subcategory,
                "order_index": testcase.order_index,
                "checklist_id": testcase.checklist_id,
                "checklist_title": testcase.checklist.title if testcase.checklist else None,
                "section_title": testcase.checklist.section.title if testcase.checklist and testcase.checklist.section else None,
                "config_id": testcase.config_id,
                "config_name": testcase.config.name if testcase.config else None
            }
            formatted_testcases.append(testcase_data)
        
        return {
            "success": True,
            "query": query,
            "testcases": formatted_testcases,
            "count": len(formatted_testcases),
            "filters": {
                "section_id": section_id,
                "checklist_id": checklist_id,
                "test_group": test_group,
                "functionality": functionality,
                "priority": priority
            }
        }
        
    except Exception as e:
        logger.error(f"Search testcases failed: {str(e)}")
        return {
            "success": False,
            "error": f"Search testcases failed: {str(e)}"
        }


@mcp.tool()
async def qa_get_configs(
    limit: int = 100,
    offset: int = 0,
    ctx: Context = None
) -> Dict[str, Any]:
    """Отримує список конфігів.
    
    Args:
        limit: Максимальна кількість конфігів (1-200)
        offset: Кількість конфігів для пропуску
    """
    try:
        if ctx:
            await ctx.info(f"Getting configs with limit={limit}, offset={offset}")
        
        # Validate parameters
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
        
        configs, total = qa_repo.get_configs(limit=limit, offset=offset)
        
        formatted_configs = []
        for config in configs:
            config_data = {
                "id": config.id,
                "name": config.name,
                "url": config.url,
                "description": config.description or "",
                "testcases_count": len(config.testcases) if config.testcases else 0,
                "checklists_count": len(config.checklists) if config.checklists else 0
            }
            formatted_configs.append(config_data)
        
        return {
            "success": True,
            "configs": formatted_configs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Get configs failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get configs failed: {str(e)}"
        }


@mcp.tool()
async def qa_get_statistics(ctx: Context = None) -> Dict[str, Any]:
    """Отримує статистику по QA структурі."""
    try:
        if ctx:
            await ctx.info("Getting QA statistics")
        
        stats = qa_repo.get_qa_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Get statistics failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get statistics failed: {str(e)}"
        }


@mcp.tool()
async def qa_get_full_structure(ctx: Context = None) -> Dict[str, Any]:
    """Отримує повну QA структуру з ієрархією секцій, чекліст і тесткейсів."""
    try:
        if ctx:
            await ctx.info("Getting full QA structure")
        
        structure = qa_repo.get_full_qa_structure()
        
        return {
            "success": True,
            "structure": structure
        }
        
    except Exception as e:
        logger.error(f"Get full structure failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get full structure failed: {str(e)}"
        }


@mcp.tool()
async def qa_list_features(
    limit: int = 100,
    offset: int = 0,
    with_documents: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Отримує список всіх фіч з описами та пов'язаними документами.
    
    Args:
        limit: Максимальна кількість фіч для повернення (1-500)
        offset: Кількість фіч для пропуску
        with_documents: Чи включати назви документів для кожної фічі
    """
    try:
        if ctx:
            await ctx.info(f"Getting features list with limit={limit}, offset={offset}")
        
        # Validate parameters
        if limit < 1 or limit > 500:
            return {
                "success": False,
                "error": "limit must be between 1 and 500"
            }
        
        if offset < 0:
            return {
                "success": False,
                "error": "offset must be non-negative"
            }
        
        # Get features from repository
        session = qa_repo.get_session()
        try:
            from sqlalchemy import func, distinct
            from sqlalchemy.orm import joinedload
            
            # Get unique features from test cases
            base_query = session.query(TestCase.functionality).filter(
                TestCase.functionality.isnot(None),
                TestCase.functionality != ''
            ).distinct()
            
            # Get total count first
            total_count = base_query.count()
            
            # Apply pagination
            query = base_query
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            features = query.all()
            
            # Format results
            result_features = []
            for i, (functionality,) in enumerate(features):
                feature_data = {
                    "id": offset + i + 1,  # Simple ID generation
                    "name": functionality,
                    "description": f"Functionality: {functionality}"
                }
                
                # Add documents if requested
                if with_documents:
                    # Get checklists that contain this functionality
                    docs_query = session.query(Checklist.title).join(TestCase).filter(
                        TestCase.functionality == functionality
                    ).distinct()
                    
                    documents = [doc[0] for doc in docs_query.all()]
                    feature_data["documents"] = documents
                
                result_features.append(feature_data)
            
            return {
                "success": True,
                "features": result_features,
                "count": len(result_features),
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
            
        finally:
            session.close()
            
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
    """Отримує документи для конкретної фічі.
    
    Args:
        feature_name: Назва фічі (або feature_name, або feature_id обов'язковий)
        feature_id: ID фічі (або feature_name, або feature_id обов'язковий)
        limit: Максимальна кількість документів для повернення (1-200)
        offset: Кількість документів для пропуску
    """
    try:
        if ctx:
            await ctx.info(f"Getting documents for feature: {feature_name or feature_id}")
        
        # Validate parameters
        if not feature_name and not feature_id:
            return {
                "success": False,
                "error": "Either feature_name or feature_id is required"
            }
        
        if limit < 1 or limit > 200:
            return {
                "success": False,
                "error": "limit must be between 1 and 200"
            }
        
        if offset < 0:
            return {
                "success": False,
                "error": "offset must be non-negative"
            }
        
        # Get documents from repository
        session = qa_repo.get_session()
        try:
            # Build query based on feature_name (we'll use functionality field)
            if feature_name:
                search_functionality = feature_name
            else:
                # For feature_id, we need to map it to functionality
                # This is a simple mapping - in real world you'd have a proper features table
                functionalities = session.query(TestCase.functionality).filter(
                    TestCase.functionality.isnot(None),
                    TestCase.functionality != ''
                ).distinct().all()
                
                if feature_id <= 0 or feature_id > len(functionalities):
                    return {
                        "success": False,
                        "error": f"Invalid feature_id: {feature_id}"
                    }
                
                search_functionality = functionalities[feature_id - 1][0]
            
            # Get checklists that contain this functionality
            query = session.query(Checklist).join(TestCase).filter(
                TestCase.functionality == search_functionality
            ).distinct()
            
            if offset > 0:
                query = query.offset(offset)
            
            if limit:
                query = query.limit(limit)
            
            checklists = query.all()
            
            # Format results
            documents = []
            for checklist in checklists:
                doc_data = {
                    "id": checklist.id,
                    "title": checklist.title,
                    "url": checklist.url,
                    "space": checklist.space_key,
                    "description": checklist.description
                }
                documents.append(doc_data)
            
            # Get total count
            total_count = session.query(Checklist).join(TestCase).filter(
                TestCase.functionality == search_functionality
            ).distinct().count()
            
            return {
                "success": True,
                "feature_name": search_functionality,
                "documents": documents,
                "count": len(documents),
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Get docs by feature failed: {str(e)}")
        return {
            "success": False,
            "error": f"Get docs by feature failed: {str(e)}"
        }


@mcp.tool()
async def qa_semantic_search(
    query: str,
    limit: int = 10,
    min_similarity: float = 0.5,
    section_id: Optional[int] = None,
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Семантичний пошук тесткейсів за змістом (використовує AI embeddings).
    
    Args:
        query: Пошуковий запит (семантичний)
        limit: Максимальна кількість результатів (1-50)
        min_similarity: Мінімальна подібність (0.0-1.0, за замовчуванням 0.5)
        section_id: ID секції для фільтрації (опціонально)
        checklist_id: ID чекліста для фільтрації (опціонально)
        test_group: Група тестів (GENERAL або CUSTOM)
        functionality: Функціональність для фільтрації
        priority: Пріоритет для фільтрації
    """
    try:
        if ctx:
            await ctx.info(f"Semantic search for: {query}")
        
        # Validate parameters
        if not query or len(query.strip()) < 3:
            return {
                "success": False,
                "error": "query must be at least 3 characters long"
            }
        
        if limit < 1 or limit > 50:
            return {
                "success": False,
                "error": "limit must be between 1 and 50"
            }
        
        if min_similarity < 0.0 or min_similarity > 1.0:
            return {
                "success": False,
                "error": "min_similarity must be between 0.0 and 1.0"
            }
        
        # Validate enum values
        if test_group and test_group not in ['GENERAL', 'CUSTOM']:
            return {
                "success": False,
                "error": "test_group must be GENERAL or CUSTOM"
            }
        
        if priority and priority not in ['LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST', 'CRITICAL']:
            return {
                "success": False,
                "error": "priority must be one of: LOWEST, LOW, MEDIUM, HIGH, HIGHEST, CRITICAL"
            }
        
        # Perform semantic search
        search_results = qa_repo.semantic_search_testcases(
            query=query.strip(),
            limit=limit,
            min_similarity=min_similarity,
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            testcase = result['testcase']
            formatted_results.append({
                "id": testcase.id,
                "step": testcase.step,
                "expected_result": testcase.expected_result,
                "priority": testcase.priority.value if testcase.priority else None,
                "test_group": testcase.test_group.value if testcase.test_group else None,
                "functionality": testcase.functionality,
                "subcategory": testcase.subcategory,
                "checklist_id": testcase.checklist_id,
                "checklist_title": result['checklist_title'],
                "config_name": result['config_name'],
                "similarity": round(result['similarity'], 4),
                "screenshot": testcase.screenshot,
                "qa_auto_coverage": testcase.qa_auto_coverage
            })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "min_similarity": min_similarity,
            "search_type": "semantic"
        }
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        return {
            "success": False,
            "error": f"Semantic search failed: {str(e)}"
        }




@mcp.tool()
async def qa_health(ctx: Context = None) -> Dict[str, Any]:
    """Перевіряє стан QA системи."""
    try:
        if ctx:
            await ctx.info("Performing QA health check")
        
        health_status = {
            "success": True,
            "timestamp": asyncio.get_event_loop().time(),
            "services": {}
        }
        
        # Check MySQL connection
        try:
            from sqlalchemy import text
            session = qa_repo.get_session()
            session.execute(text("SELECT 1"))
            session.close()
            health_status["services"]["mysql"] = {"status": "healthy", "message": "Connection OK"}
        except Exception as e:
            health_status["services"]["mysql"] = {"status": "unhealthy", "message": str(e)}
            health_status["success"] = False
        
        # Get basic statistics
        try:
            stats = qa_repo.get_qa_statistics()
            health_status["statistics"] = stats
        except Exception as e:
            health_status["services"]["statistics"] = {"status": "unhealthy", "message": str(e)}
        
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
        logger.info("Initializing QA MCP Server...")
        
        # Create MySQL tables if they don't exist
        qa_repo.create_tables()
        logger.info("Database tables initialized successfully")
        
    except Exception as e:
        logger.warning(f"Failed to initialize database tables: {e}")


async def cleanup_server():
    """Clean up resources."""
    try:
        logger.info("Cleaning up server resources...")
        
        # Close database connections
        if qa_repo:
            qa_repo.close()
            
        logger.info("Server cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point for the QA MCP server."""
    try:
        # Initialize server
        asyncio.run(initialize_server())
        
        # Run the FastMCP server with stdio transport
        logger.info("Starting QA MCP Server...")
        mcp.run()
        
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
