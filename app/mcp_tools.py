#!/usr/bin/env python3
"""
MCP Tools - QA інструменти з бізнес-логікою
Містить всі QA функції без MCP декораторів для універсального використання
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.qa_repository import QARepository
from app.models.qa_models import QASection, Checklist, TestCase, Config

# Configure logging
logger = logging.getLogger(__name__)

# Initialize repository
qa_repo = QARepository()


async def qa_search_documents(
    query: str, 
    top_k: int = 10, 
    feature_names: Optional[List[str]] = None,
    space_keys: Optional[List[str]] = None, 
    filters: Optional[Dict[str, Any]] = None, 
    return_chunks: bool = True
) -> Dict[str, Any]:
    """Vector search in QA knowledge base (documents and chunks)"""
    try:
        from app.ai.embedder import OpenAIEmbedder
        from app.data.vectordb_repo import VectorDBRepository
        
        # Initialize components
        embedder = OpenAIEmbedder()
        vector_repo = VectorDBRepository()
        
        # Generate query embedding
        query_embedding = embedder.embed_text(query)
        if not query_embedding:
            return {
                "success": False,
                "error": "Failed to generate query embedding",
                "query": query,
                "results": [],
                "count": 0
            }
        
        # Perform vector search in documents/chunks
        search_results = vector_repo.search(
            query_vector=query_embedding,
            top_k=top_k,
            feature_names=feature_names,
            space_keys=space_keys,
            filters=filters
        )
        
        formatted_results = []
        for result in search_results:
            formatted_result = {
                "score": result.get("score", 0),
                "feature": result.get("feature", ""),
                "document": result.get("document", ""),
                "space": result.get("space", ""),
                "url": result.get("url", "")
            }
            
            if return_chunks and "chunk" in result:
                formatted_result["chunk"] = result["chunk"]
            
            formatted_results.append(formatted_result)
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "took_ms": 1,
            "search_type": "vector_documents"
        }
    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0
        }


async def qa_search_testcases(
    query: str,
    limit: int = 10,
    min_similarity: float = 0.5,
    section_id: Optional[int] = None,
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None
) -> Dict[str, Any]:
    """Semantic search of test cases using AI embeddings"""
    try:
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
        logger.error(f"Testcase semantic search failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def qa_search_testcases_text(
    query: str,
    section_id: Optional[int] = None,
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Text search of test cases in step or expected_result fields"""
    try:
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
                "checklist_id": testcase.checklist_id,
                "checklist_title": testcase.checklist.title if testcase.checklist else None,
                "section_title": testcase.checklist.section.title if testcase.checklist and testcase.checklist.section else None
            }
            formatted_testcases.append(testcase_data)
        
        return {
            "success": True,
            "query": query,
            "testcases": formatted_testcases,
            "count": len(formatted_testcases)
        }
        
    except Exception as e:
        logger.error(f"Text search testcases failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def qa_list_features(
    limit: int = 100, 
    offset: int = 0, 
    with_documents: bool = True
) -> Dict[str, Any]:
    """List all features with descriptions"""
    try:
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
            "error": str(e)
        }


async def qa_docs_by_feature(
    feature_name: Optional[str] = None,
    feature_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Get documents for a specific feature"""
    try:
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
            "error": str(e)
        }


async def qa_health() -> Dict[str, Any]:
    """Check QA system health"""
    try:
        health_status = {
            "success": True,
            "ok": True,
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
            "ok": False,
            "error": str(e)
        }


async def qa_get_sections(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get list of QA sections"""
    try:
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
        
        sections, total = qa_repo.get_qa_sections(limit=limit, offset=offset)
        
        formatted_sections = []
        for section in sections:
            section_data = {
                "id": section.id,
                "title": section.title,
                "description": section.description or "",
                "url": section.url,
                "confluence_page_id": section.confluence_page_id,
                "checklists_count": len(section.checklists) if section.checklists else 0
            }
            formatted_sections.append(section_data)
        
        return {
            "success": True,
            "sections": formatted_sections,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Get QA sections failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def qa_get_checklists(
    section_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get list of checklists, optionally filtered by section"""
    try:
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
            "error": str(e)
        }


async def qa_get_testcases(
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    subcategory: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get list of test cases with filters"""
    try:
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
            "error": str(e)
        }


async def qa_get_configs(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get list of configurations"""
    try:
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
            "error": str(e)
        }


async def qa_get_statistics() -> Dict[str, Any]:
    """Get QA structure statistics"""
    try:
        stats = qa_repo.get_qa_statistics()
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Get statistics failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def qa_get_full_structure() -> Dict[str, Any]:
    """Get full QA structure with hierarchy"""
    try:
        structure = qa_repo.get_full_qa_structure()
        return {
            "success": True,
            "structure": structure
        }
        
    except Exception as e:
        logger.error(f"Get full structure failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }



