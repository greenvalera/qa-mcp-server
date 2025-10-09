"""FastMCP tool registrations for testcase operations."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import (
    qa_get_testcases,
    qa_search_testcases,
    qa_search_testcases_text,
)


def register_testcase_tools(mcp: FastMCP) -> None:
    """Register testcase-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_get_testcases_tool(
        checklist_id: Optional[int] = None,
        test_group: Optional[str] = None,
        functionality: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(
                "Getting testcases",
                meta={
                    "checklist_id": checklist_id,
                    "test_group": test_group,
                    "functionality": functionality,
                    "priority": priority,
                    "limit": limit,
                    "offset": offset,
                },
            )
        return await qa_get_testcases(
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
            limit=limit,
            offset=offset,
        )

    @mcp.tool()
    async def qa_search_testcases_semantic(
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
        section_id: Optional[int] = None,
        checklist_id: Optional[int] = None,
        test_group: Optional[str] = None,
        functionality: Optional[str] = None,
        priority: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info("Semantic testcase search", meta={"query": query, "limit": limit})
        return await qa_search_testcases(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
        )

    @mcp.tool()
    async def qa_search_testcases_text_tool(
        query: str,
        section_id: Optional[int] = None,
        checklist_id: Optional[str] = None,
        test_group: Optional[str] = None,
        functionality: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info("Text testcase search", meta={"query": query, "limit": limit})
        return await qa_search_testcases_text(
            query=query,
            section_id=section_id,
            checklist_id=checklist_id,
            test_group=test_group,
            functionality=functionality,
            priority=priority,
            limit=limit,
        )
