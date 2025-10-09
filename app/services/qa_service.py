"""Service layer that orchestrates QA repository operations for MCP tools."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Callable, List

from ..data.qa_repository import QARepository
from ..models.qa_models import TestCase
from ..schemas.requests import (
    ChecklistsQuery,
    ConfigsQuery,
    FeatureDocumentsQuery,
    FeaturesQuery,
    SectionsQuery,
    TestcaseSemanticSearchQuery,
    TestcaseTextSearchQuery,
    TestcasesQuery,
)
from ..schemas.responses import (
    ChecklistDTO,
    ChecklistsResponse,
    ConfigDTO,
    ConfigsResponse,
    FeatureDTO,
    FeatureDocumentDTO,
    FeatureDocumentsResponse,
    FeaturesResponse,
    FullStructureResponse,
    HealthResponse,
    QASectionDTO,
    SectionsResponse,
    SearchResponse,
    StatisticsResponse,
    TestCaseDTO,
    TestcasesResponse,
)


class QAService:
    """Facade that provides asynchronous helpers around the synchronous repository."""

    def __init__(self, repository: QARepository):
        self._repository = repository

    async def _run_repo(self, func: Callable, *args, **kwargs):
        """Execute a synchronous repository call in a worker thread."""
        return await asyncio.to_thread(partial(func, *args, **kwargs))

    async def list_sections(self, params: SectionsQuery) -> SectionsResponse:
        sections, total = await self._run_repo(
            self._repository.get_qa_sections,
            params.limit,
            params.offset,
        )
        items = [QASectionDTO.model_validate(section) for section in sections]
        return SectionsResponse(
            sections=items,
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def list_checklists(self, params: ChecklistsQuery) -> ChecklistsResponse:
        checklists, total = await self._run_repo(
            self._repository.get_checklists,
            section_id=params.section_id,
            limit=params.limit,
            offset=params.offset,
        )
        items: List[ChecklistDTO] = []
        for checklist in checklists:
            dto = ChecklistDTO.model_validate(checklist)
            dto.section_title = checklist.section.title if checklist.section else None
            dto.configs_count = len(checklist.configs) if checklist.configs else 0
            dto.testcases_count = len(checklist.testcases) if checklist.testcases else 0
            items.append(dto)
        return ChecklistsResponse(
            checklists=items,
            total=total,
            limit=params.limit,
            offset=params.offset,
            section_id=params.section_id,
        )

    async def list_testcases(self, params: TestcasesQuery) -> TestcasesResponse:
        testcases, total = await self._run_repo(
            self._repository.get_testcases,
            checklist_id=params.checklist_id,
            test_group=params.test_group,
            functionality=params.functionality,
            priority=params.priority,
            limit=params.limit,
            offset=params.offset,
        )
        items = [self._build_testcase_dto(testcase) for testcase in testcases]
        return TestcasesResponse(
            testcases=items,
            total=total,
            limit=params.limit,
            offset=params.offset,
            filters={
                "checklist_id": params.checklist_id,
                "test_group": params.test_group.value if params.test_group else None,
                "functionality": params.functionality,
                "priority": params.priority.value if params.priority else None,
            },
        )

    async def search_testcases_text(
        self, params: TestcaseTextSearchQuery
    ) -> SearchResponse:
        testcases = await self._run_repo(
            self._repository.search_testcases,
            query=params.query,
            section_id=params.section_id,
            checklist_id=params.checklist_id,
            test_group=params.test_group,
            functionality=params.functionality,
            priority=params.priority,
            limit=params.limit,
        )
        items = [self._build_testcase_dto(testcase) for testcase in testcases]
        return SearchResponse(
            query=params.query,
            testcases=items,
            count=len(items),
            filters=self._build_filter_summary(params),
            search_type="text",
        )

    async def search_testcases_semantic(
        self, params: TestcaseSemanticSearchQuery
    ) -> SearchResponse:
        results = await self._run_repo(
            self._repository.semantic_search_testcases,
            query=params.query,
            limit=params.limit,
            min_similarity=params.min_similarity,
            section_id=params.section_id,
            checklist_id=params.checklist_id,
            test_group=params.test_group,
            functionality=params.functionality,
            priority=params.priority,
        )
        items: List[TestCaseDTO] = []
        for result in results:
            dto = self._build_testcase_dto(result["testcase"])
            dto.similarity = round(result["similarity"], 4)
            dto.checklist_title = result.get("checklist_title")
            dto.config_name = result.get("config_name")
            items.append(dto)
        return SearchResponse(
            query=params.query,
            testcases=items,
            count=len(items),
            filters=self._build_filter_summary(params),
            min_similarity=params.min_similarity,
            search_type="semantic",
        )

    async def list_configs(self, params: ConfigsQuery) -> ConfigsResponse:
        configs, total = await self._run_repo(
            self._repository.get_configs,
            limit=params.limit,
            offset=params.offset,
        )
        items: List[ConfigDTO] = []
        for config in configs:
            dto = ConfigDTO.model_validate(config)
            dto.testcases_count = len(config.testcases) if config.testcases else 0
            dto.checklists_count = len(config.checklists) if config.checklists else 0
            items.append(dto)
        return ConfigsResponse(
            configs=items,
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get_statistics(self) -> StatisticsResponse:
        stats = await self._run_repo(self._repository.get_qa_statistics)
        return StatisticsResponse(statistics=stats)

    async def get_full_structure(self) -> FullStructureResponse:
        structure = await self._run_repo(self._repository.get_full_qa_structure)
        return FullStructureResponse(structure=structure)

    async def list_features(self, params: FeaturesQuery) -> FeaturesResponse:
        functionalities, total = await self._run_repo(
            self._repository.list_functionalities,
            limit=params.limit,
            offset=params.offset,
        )
        features: List[FeatureDTO] = []
        for idx, functionality in enumerate(functionalities, start=1):
            feature = FeatureDTO(
                id=params.offset + idx,
                name=functionality,
                description=f"Functionality: {functionality}",
            )
            if params.with_documents:
                documents = await self._run_repo(
                    self._repository.list_documents_for_functionality,
                    functionality,
                )
                feature.documents = [doc.title for doc in documents]
            features.append(feature)
        return FeaturesResponse(
            features=features,
            count=len(features),
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def documents_by_feature(
        self, params: FeatureDocumentsQuery
    ) -> FeatureDocumentsResponse:
        functionality = params.feature_name
        if not functionality:
            functionality = await self._run_repo(
                self._repository.resolve_functionality_by_id,
                params.feature_id,
            )
        documents, total = await self._run_repo(
            self._repository.list_checklists_for_functionality,
            functionality,
            limit=params.limit,
            offset=params.offset,
        )
        items = [
            FeatureDocumentDTO(
                id=checklist.id,
                title=checklist.title,
                url=checklist.url,
                section_title=checklist.section.title if checklist.section else None,
            )
            for checklist in documents
        ]
        return FeatureDocumentsResponse(
            feature_name=functionality,
            documents=items,
            count=len(items),
            limit=params.limit,
            offset=params.offset,
            total=total,
        )

    async def health_check(self) -> HealthResponse:
        def _check_mysql_sync() -> tuple[str, dict]:
            from sqlalchemy import text

            try:
                session = self._repository.get_session()
                session.execute(text("SELECT 1"))
                session.close()
                return "mysql", {"status": "healthy", "message": "Connection OK"}
            except Exception as exc:  # pragma: no cover - defensive
                return "mysql", {"status": "unhealthy", "message": str(exc)}

        mysql_key, mysql_status = await asyncio.to_thread(_check_mysql_sync)
        services = {mysql_key: mysql_status}
        success = mysql_status["status"] == "healthy"
        try:
            stats = await self._run_repo(self._repository.get_qa_statistics)
        except Exception as exc:  # pragma: no cover - defensive
            services["statistics"] = {"status": "unhealthy", "message": str(exc)}
            stats = None
            success = False
        loop = asyncio.get_running_loop()
        return HealthResponse(
            success=success,
            timestamp=loop.time(),
            services=services,
            statistics=stats,
        )

    def _build_filter_summary(self, params: TestcaseTextSearchQuery) -> dict:
        return {
            "section_id": params.section_id,
            "checklist_id": params.checklist_id,
            "test_group": params.test_group.value if params.test_group else None,
            "functionality": params.functionality,
            "priority": params.priority.value if params.priority else None,
        }

    def _build_testcase_dto(self, testcase: TestCase) -> TestCaseDTO:
        dto = TestCaseDTO.model_validate(testcase)
        if testcase.checklist:
            dto.checklist_title = testcase.checklist.title
            if testcase.checklist.section:
                dto.section_title = testcase.checklist.section.title
        if testcase.config:
            dto.config_name = testcase.config.name
        return dto
