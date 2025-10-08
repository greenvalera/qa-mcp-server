"""FastMCP tool registrations for statistics and structure."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import qa_get_full_structure, qa_get_statistics


def register_statistics_tools(mcp: FastMCP) -> None:
    """Register statistics-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_get_statistics_tool(ctx: Optional[Context] = None) -> dict:
        if ctx:
            await ctx.info("Fetching QA statistics")
        return await qa_get_statistics()

    @mcp.tool()
    async def qa_get_full_structure_tool(ctx: Optional[Context] = None) -> dict:
        if ctx:
            await ctx.info("Fetching full QA structure")
        return await qa_get_full_structure()
