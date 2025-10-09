#!/usr/bin/env python3
"""QA MCP Server entrypoint."""

from __future__ import annotations

import asyncio
import logging
import sys

from fastmcp import FastMCP

from .dependencies import get_qa_repository
from .mcp import create_mcp_server
from .mcp_tools import (
    qa_docs_by_feature,
    qa_get_checklists,
    qa_get_configs,
    qa_get_full_structure,
    qa_get_sections,
    qa_get_statistics,
    qa_get_testcases,
    qa_health,
    qa_list_features,
    qa_search_documents,
    qa_search_testcases,
    qa_search_testcases_text,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Backwards compatibility: expose tool callables at module level
qa_get_sections_mcp = qa_get_sections


async def initialize_server() -> None:
    """Initialize infrastructure components before the server starts."""
    logger.info("Initializing QA MCP Server...")
    repo = get_qa_repository()
    try:
        await asyncio.to_thread(repo.create_tables)
        logger.info("Database tables initialized successfully")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to initialize database tables: %s", exc)


async def cleanup_server() -> None:
    """Clean up allocated resources."""
    logger.info("Cleaning up server resources...")
    repo = get_qa_repository()
    try:
        await asyncio.to_thread(repo.close)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error during cleanup: %s", exc)
    else:
        logger.info("Server cleanup completed")


def main() -> None:
    """Run the FastMCP server."""
    mcp = create_mcp_server()

    try:
        asyncio.run(initialize_server())
        logger.info("Starting QA MCP Server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Server error: %s", exc)
        raise
    finally:
        asyncio.run(cleanup_server())


if __name__ == "__main__":
    main()
