"""FastMCP tool registrations for feature queries."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from ...mcp_tools import qa_docs_by_feature, qa_list_features


def register_feature_tools(mcp: FastMCP) -> None:
    """Register feature-related tools on the given MCP instance."""

    @mcp.tool()
    async def qa_list_features_tool(
        limit: int = 100,
        offset: int = 0,
        with_documents: bool = True,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(
                "Listing features",
                meta={"limit": limit, "offset": offset, "with_documents": with_documents},
            )
        return await qa_list_features(limit=limit, offset=offset, with_documents=with_documents)

    @mcp.tool()
    async def qa_docs_by_feature_tool(
        feature_name: Optional[str] = None,
        feature_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Optional[Context] = None,
    ) -> dict:
        if ctx:
            await ctx.info(
                "Retrieving feature documents",
                meta={"feature_name": feature_name, "feature_id": feature_id, "limit": limit, "offset": offset},
            )
        return await qa_docs_by_feature(
            feature_name=feature_name,
            feature_id=feature_id,
            limit=limit,
            offset=offset,
        )
