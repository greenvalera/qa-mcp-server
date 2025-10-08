"""Pydantic DTOs for QA responses."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.qa_models import Priority, TestGroup


class QASectionDTO(BaseModel):
    """DTO representing a QA section."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = Field(default="")
    url: str
    confluence_page_id: str
    space_key: Optional[str] = None
    checklists_count: int = 0

    @field_validator("description", mode="before")
    @classmethod
    def empty_description(cls, value: Optional[str]) -> str:
        return value or ""


class ChecklistDTO(BaseModel):
    """DTO representing a checklist."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = Field(default="")
    url: str
    section_id: int
    section_title: Optional[str] = None
    configs_count: int = 0
    testcases_count: int = 0

    @field_validator("description", mode="before")
    @classmethod
    def empty_description(cls, value: Optional[str]) -> str:
        return value or ""


class TestCaseDTO(BaseModel):
    """DTO representing a test case."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    step: str
    expected_result: str
    screenshot: Optional[str] = None
    priority: Optional[str] = None
    test_group: Optional[str] = None
    functionality: Optional[str] = None
    order_index: Optional[int] = None
    checklist_id: str
    config_id: Optional[int] = None
    qa_auto_coverage: Optional[str] = None
    checklist_title: Optional[str] = None
    section_title: Optional[str] = None
    config_name: Optional[str] = None
    similarity: Optional[float] = None

    @field_validator("priority", mode="before")
    @classmethod
    def priority_to_value(cls, value: Optional[Priority | str]) -> Optional[str]:
        if isinstance(value, Priority):
            return value.value
        return value

    @field_validator("test_group", mode="before")
    @classmethod
    def test_group_to_value(cls, value: Optional[TestGroup | str]) -> Optional[str]:
        if isinstance(value, TestGroup):
            return value.value
        return value


class ConfigDTO(BaseModel):
    """DTO representing a config entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: Optional[str] = None
    description: Optional[str] = Field(default="")
    testcases_count: int = 0
    checklists_count: int = 0

    @field_validator("description", mode="before")
    @classmethod
    def empty_description(cls, value: Optional[str]) -> str:
        return value or ""


class FeatureDTO(BaseModel):
    """DTO representing a feature/functionality entry."""

    id: int
    name: str
    description: Optional[str] = None
    documents: Optional[List[str]] = None


class FeatureDocumentDTO(BaseModel):
    """DTO representing a checklist linked to a feature."""

    id: str
    title: str
    url: str
    section_title: Optional[str] = None


class SectionsResponse(BaseModel):
    success: bool = True
    sections: List[QASectionDTO]
    total: int
    limit: int
    offset: int


class ChecklistsResponse(BaseModel):
    success: bool = True
    checklists: List[ChecklistDTO]
    total: int
    limit: int
    offset: int
    section_id: Optional[int] = None


class TestcasesResponse(BaseModel):
    success: bool = True
    testcases: List[TestCaseDTO]
    total: int
    limit: int
    offset: int
    filters: dict


class SearchResponse(BaseModel):
    success: bool = True
    query: str
    testcases: List[TestCaseDTO]
    count: int
    filters: Optional[dict] = None
    min_similarity: Optional[float] = None
    search_type: Optional[str] = None


class ConfigsResponse(BaseModel):
    success: bool = True
    configs: List[ConfigDTO]
    total: int
    limit: int
    offset: int


class FeaturesResponse(BaseModel):
    success: bool = True
    features: List[FeatureDTO]
    count: int
    total: int
    limit: int
    offset: int


class FeatureDocumentsResponse(BaseModel):
    success: bool = True
    feature_name: str
    documents: List[FeatureDocumentDTO]
    count: int
    limit: int
    offset: int
    total: Optional[int] = None


class StatisticsResponse(BaseModel):
    success: bool = True
    statistics: dict


class FullStructureResponse(BaseModel):
    success: bool = True
    structure: dict


class HealthResponse(BaseModel):
    success: bool
    timestamp: float
    services: dict
    statistics: Optional[dict] = None
