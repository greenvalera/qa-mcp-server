"""Dependency container utilities for QA services."""

from __future__ import annotations

from functools import partial
from threading import RLock
from typing import Callable, Optional

from .data.qa_repository import QARepository
from .services.qa_service import QAService

__all__ = [
    "get_qa_repository",
    "get_qa_service",
    "override_qa_repository",
    "override_qa_service",
]


_lock = RLock()
_repo_factory: Callable[[], QARepository] = QARepository
_service_factory: Callable[[QARepository], QAService] = QAService
_repo_instance: Optional[QARepository] = None
_service_instance: Optional[QAService] = None


def _reset_singletons() -> None:
    global _repo_instance, _service_instance
    _repo_instance = None
    _service_instance = None


def override_qa_repository(factory: Callable[[], QARepository]) -> None:
    """Override the default QARepository factory (useful for tests)."""
    global _repo_factory
    with _lock:
        _repo_factory = factory
        _reset_singletons()


def override_qa_service(factory: Callable[[QARepository], QAService]) -> None:
    """Override the default QAService factory (useful for tests)."""
    global _service_factory
    with _lock:
        _service_factory = factory
        _reset_singletons()


def get_qa_repository() -> QARepository:
    """Return a lazily-instantiated QARepository instance."""
    global _repo_instance
    with _lock:
        if _repo_instance is None:
            _repo_instance = _repo_factory()
        return _repo_instance


def get_qa_service() -> QAService:
    """Return a lazily-instantiated QAService instance."""
    global _service_instance
    with _lock:
        if _service_instance is None:
            repository = get_qa_repository()
            _service_instance = _service_factory(repository)
        return _service_instance
