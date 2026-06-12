"""MCP server entry point using MCP Python SDK."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Tessera MCP server starting")
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server

        server = Server("tessera-mcp")

        @server.list_tools()
        async def list_tools():
            from mcp.types import Tool

            return [
                Tool(
                    name="search_documents",
                    description="Search Tessera knowledge base with permission enforcement",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "space_ids": {"type": "array", "items": {"type": "string"}},
                            "language": {"type": "string"},
                            "top_k": {"type": "integer", "default": 10},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="read_document",
                    description="Read a document's full canonical content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {"type": "string"},
                            "version": {"type": "integer"},
                        },
                        "required": ["document_id"],
                    },
                ),
            ]

        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            from mcp.types import TextContent

            if name == "search_documents":
                result = await _search_documents(arguments)
                return [TextContent(type="text", text=str(result))]
            elif name == "read_document":
                result = await _read_document(arguments)
                return [TextContent(type="text", text=str(result))]
            else:
                raise ValueError(f"Unknown tool: {name}")

        import asyncio
        asyncio.run(stdio_server(server))

    except ImportError:
        logger.warning("MCP SDK not installed — server cannot start")


async def _search_documents(args: dict) -> dict:
    return {"results": [], "dont_know": True, "suggested_owner": None}


async def _read_document(args: dict) -> dict:
    return {"error": "not_found"}


if __name__ == "__main__":
    main()
