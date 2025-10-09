"""FastMCP tool registrations for sections and checklists."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import qa_get_checklists, qa_get_sections


def register_section_tools(mcp: FastMCP) -> None:
    """Register section-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_get_sections_tool(
        limit: int = 100,
        offset: int = 0,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(f"Getting QA sections with limit={limit}, offset={offset}")
        return await qa_get_sections(limit=limit, offset=offset)

    @mcp.tool()
    async def qa_get_checklists_tool(
        section_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(
                "Getting checklists", meta={"section_id": section_id, "limit": limit, "offset": offset}
            )
        return await qa_get_checklists(section_id=section_id, limit=limit, offset=offset)
