"""FastMCP tool registrations for configs."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import qa_get_configs


def register_config_tools(mcp: FastMCP) -> None:
    """Register config-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_get_configs_tool(
        limit: int = 100,
        offset: int = 0,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(f"Getting configs with limit={limit}, offset={offset}")
        return await qa_get_configs(limit=limit, offset=offset)
