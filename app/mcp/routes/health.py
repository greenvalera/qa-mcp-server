"""FastMCP tool registrations for health checks."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import qa_health


def register_health_tools(mcp: FastMCP) -> None:
    """Register health-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_health_tool(ctx: Optional[Context] = None) -> dict:
        if ctx:
            await ctx.info("Performing QA health check")
        return await qa_health()
