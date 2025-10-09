"""Pydantic schemas describing incoming parameters for QA tools."""

from __future__ import annotations

from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.qa_models import Priority, TestGroup


class StrippingModel(BaseModel):
    """Base model that strips leading/trailing whitespace from string fields."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class PaginationParams(StrippingModel):
    """Base pagination parameters with classic validation messages."""

    limit: int = Field(default=100)
    offset: int = Field(default=0)

    limit_max: ClassVar[int] = 500

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1 or value > cls.limit_max:
            raise ValueError(f"limit must be between 1 and {cls.limit_max}")
        return value

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, value: int) -> int:
        if value < 0:
            raise ValueError("offset must be >= 0")
        return value


class SectionsQuery(PaginationParams):
    """Parameters for listing QA sections."""


class ChecklistsQuery(PaginationParams):
    """Parameters for listing checklists."""

    limit_max: ClassVar[int] = 200
    section_id: Optional[int] = Field(default=None, ge=1)


class TestcasesQuery(PaginationParams):
    """Parameters for listing testcases."""

    checklist_id: Optional[str] = None
    test_group: Optional[TestGroup | str] = None
    functionality: Optional[str] = None
    priority: Optional[Priority | str] = None

    @field_validator("test_group", mode="before")
    @classmethod
    def validate_test_group(cls, value: Optional[TestGroup | str]) -> Optional[TestGroup]:
        if value in (None, ""):
            return None
        if isinstance(value, TestGroup):
            return value
        return TestGroup(value)

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: Optional[Priority | str]) -> Optional[Priority]:
        if value in (None, ""):
            return None
        if isinstance(value, Priority):
            return value
        return Priority(value)


class TestcaseTextSearchQuery(StrippingModel):
    """Parameters for text-based testcase search."""

    query: str
    section_id: Optional[int] = Field(default=None, ge=1)
    checklist_id: Optional[str] = None
    test_group: Optional[TestGroup | str] = None
    functionality: Optional[str] = None
    priority: Optional[Priority | str] = None
    limit: int = Field(default=100)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("query must be at least 2 characters long")
        return value

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1 or value > 200:
            raise ValueError("limit must be between 1 and 200")
        return value

    @field_validator("test_group", mode="before")
    @classmethod
    def validate_test_group(cls, value: Optional[TestGroup | str]) -> Optional[TestGroup]:
        if value in (None, ""):
            return None
        if isinstance(value, TestGroup):
            return value
        return TestGroup(value)

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: Optional[Priority | str]) -> Optional[Priority]:
        if value in (None, ""):
            return None
        if isinstance(value, Priority):
            return value
        return Priority(value)


class TestcaseSemanticSearchQuery(TestcaseTextSearchQuery):
    """Parameters for semantic testcase search."""

    query: str
    limit: int = Field(default=10)
    min_similarity: float = Field(default=0.5)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("query must be at least 3 characters long")
        return value

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1 or value > 50:
            raise ValueError("limit must be between 1 and 50")
        return value

    @field_validator("min_similarity")
    @classmethod
    def validate_similarity(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")
        return value


class ConfigsQuery(PaginationParams):
    """Parameters for listing configs."""

    limit_max: ClassVar[int] = 200


class FeaturesQuery(PaginationParams):
    """Parameters for listing features (functionalities)."""

    limit_max: ClassVar[int] = 500
    with_documents: bool = True


class FeatureDocumentsQuery(StrippingModel):
    """Parameters for retrieving documents attached to a feature."""

    feature_name: Optional[str] = None
    feature_id: Optional[int] = Field(default=None, ge=1)
    limit: int = Field(default=50)
    offset: int = Field(default=0)

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1 or value > 200:
            raise ValueError("limit must be between 1 and 200")
        return value

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, value: int) -> int:
        if value < 0:
            raise ValueError("offset must be non-negative")
        return value

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, value: Optional[int], info):
        feature_name = info.data.get("feature_name")
        if (value is None or value <= 0) and not feature_name:
            raise ValueError("Either feature_name or feature_id is required")
        return value


class HealthCheckQuery(StrippingModel):
    """Placeholder for health check parameters (currently none)."""

    pass
