"""Utilities for building the FastMCP server application."""

from __future__ import annotations

from fastmcp import FastMCP

from .routes.configs import register_config_tools
from .routes.features import register_feature_tools
from .routes.health import register_health_tools
from .routes.sections import register_section_tools
from .routes.statistics import register_statistics_tools
from .routes.testcases import register_testcase_tools

__all__ = ["create_mcp_server"]


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP instance for QA tools."""
    mcp = FastMCP("qa-testcases")

    register_section_tools(mcp)
    register_testcase_tools(mcp)
    register_config_tools(mcp)
    register_feature_tools(mcp)
    register_statistics_tools(mcp)
    register_health_tools(mcp)

    return mcp
