#!/usr/bin/env python3
"""
MCP Tools - QA інструменти з бізнес-логікою
Містить всі QA функції без MCP декораторів для універсального використання
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import ValidationError

from .dependencies import get_qa_service
from .services.qa_service import QAService
from .schemas.requests import (
    ChecklistsQuery,
    ConfigsQuery,
    FeatureDocumentsQuery,
    FeaturesQuery,
    SectionsQuery,
    TestcaseSemanticSearchQuery,
    TestcaseTextSearchQuery,
    TestcasesQuery,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .data.qa_repository import QARepository

# Configure logging
logger = logging.getLogger(__name__)


qa_repo: Optional["QARepository"] = None


def _get_service() -> QAService:
    """Return QA service instance, respecting test overrides."""
    if qa_repo is not None:
        return QAService(qa_repo)
    return get_qa_service()


def _validation_error_response(error: ValidationError) -> Dict[str, Any]:
    messages = []
    for err in error.errors():
        location = ".".join(str(loc) for loc in err.get("loc", ())) or "params"
        messages.append(f"{location}: {err.get('msg')}")
    return {"success": False, "error": "; ".join(messages)}


async def qa_search_documents(
    query: str,
    top_k: int = 10,
    feature_names: Optional[List[str]] = None,
    space_keys: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    return_chunks: bool = True
) -> Dict[str, Any]:
    """Vector search in QA knowledge base (documents and chunks)."""
    try:
        from .ai.embedder import OpenAIEmbedder
        from .data.vectordb_repo import VectorDBRepository

        embedder = OpenAIEmbedder()
        vector_repo = VectorDBRepository()

        query_embedding = embedder.embed_text(query)
        if not query_embedding:
            return {
                "success": False,
                "error": "Failed to generate query embedding",
                "query": query,
                "results": [],
                "count": 0
            }

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
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Document search failed: %s", exc)
        return {
            "success": False,
            "error": str(exc),
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
    """Semantic search of test cases using AI embeddings."""
    try:
        params = TestcaseSemanticSearchQuery(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
        )
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().search_testcases_semantic(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Testcase semantic search failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_search_testcases_text(
    query: str,
    section_id: Optional[int] = None,
    checklist_id: Optional[str] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Text search of test cases in step or expected_result fields."""
    try:
        params = TestcaseTextSearchQuery(
            query=query,
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
            limit=limit,
        )
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().search_testcases_text(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Text search testcases failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_list_features(
    limit: int = 100,
    offset: int = 0,
    with_documents: bool = True
) -> Dict[str, Any]:
    """List all features with descriptions."""
    try:
        params = FeaturesQuery(limit=limit, offset=offset, with_documents=with_documents)
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().list_features(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("List features failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_docs_by_feature(
    feature_name: Optional[str] = None,
    feature_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Get documents for a specific feature."""
    try:
        params = FeatureDocumentsQuery(
            feature_name=feature_name,
            feature_id=feature_id,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        return _validation_error_response(exc)

    service = _get_service()
    try:
        response = await service.documents_by_feature(params)
        payload = response.model_dump()
        payload.setdefault("feature_name", params.feature_name)
        return payload
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get docs by feature failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_health() -> Dict[str, Any]:
    """Check QA system health."""
    try:
        response = await _get_service().health_check()
        payload = response.model_dump()
        payload.setdefault("ok", payload.get("success", False))
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Health check failed: %s", exc)
        return {"success": False, "ok": False, "error": str(exc)}


async def qa_get_sections(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get list of QA sections."""
    try:
        params = SectionsQuery(limit=limit, offset=offset)
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().list_sections(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get QA sections failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_get_checklists(
    section_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get list of checklists, optionally filtered by section."""
    try:
        params = ChecklistsQuery(section_id=section_id, limit=limit, offset=offset)
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().list_checklists(params)
        payload = response.model_dump()
        payload["filtered_by_section_id"] = payload.get("section_id")
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get checklists failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_get_testcases(
    checklist_id: Optional[int] = None,
    test_group: Optional[str] = None,
    functionality: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get list of test cases with filters."""
    try:
        params = TestcasesQuery(
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().list_testcases(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get testcases failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_get_configs(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get list of configurations."""
    try:
        params = ConfigsQuery(limit=limit, offset=offset)
    except ValidationError as exc:
        return _validation_error_response(exc)

    try:
        response = await _get_service().list_configs(params)
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get configs failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_get_statistics() -> Dict[str, Any]:
    """Get QA structure statistics."""
    try:
        response = await _get_service().get_statistics()
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get statistics failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def qa_get_full_structure() -> Dict[str, Any]:
    """Get full QA structure with hierarchy."""
    try:
        response = await _get_service().get_full_structure()
        return response.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Get full structure failed: %s", exc)
        return {"success": False, "error": str(exc)}
