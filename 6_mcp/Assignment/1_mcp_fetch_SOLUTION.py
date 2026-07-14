#
# <h1>RAZ Systems </h1>
#
# SOLUTION 1 — Fetch MCP Server
# ===============================
#
# mcp-server-fetch is an official Anthropic reference MCP server (from the
# modelcontextprotocol/servers repo). Given a URL, it fetches the page over
# HTTP and converts the raw HTML into clean, LLM-friendly Markdown -- stripping
# out scripts, nav bars, ads, and other clutter so the model reads useful text
# instead of markup noise. It exposes this as a single MCP tool (commonly
# "fetch") that any MCP client can call, passing in a URL and getting back the
# page content as a string.
#
# Reminder on where/how this runs:
# - It runs LOCALLY as a subprocess on this machine, not on any remote server.
# - The client talks to it over stdio (its stdin/stdout) using MCP/JSON-RPC.
# - "uvx mcp-server-fetch" downloads the package from PyPI into a temporary
#   uv-managed environment (if not already cached) and runs it immediately.
# - The subprocess starts when the client session opens and stops when it
#   closes -- it is not a persistent background service.

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    fetch_params = {
        "command": "uvx",
        "args": ["mcp-server-fetch"],
    }

    async with MCPServerStdio(
        params=fetch_params,
        client_session_timeout_seconds=60,
    ) as server:

        tools = await server.session.list_tools()
        print(tools)

        response = await server.session.call_tool(
            "fetch",
            {"url": "https://razsystems.com"},
        )
        print(f"Tool Response:\n{response}")


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION ANSWERS (sketch)
# ─────────────────────────────────────────────────────
#
# 1. Calling "fetch" with an empty dict would fail MCP-side input schema
#    validation -- the server declares "url" as a required parameter in its
#    tool's inputSchema, so the MCP protocol layer (or the server itself)
#    rejects the call before ever attempting an HTTP request. The client
#    would see this as a tool-call error result, not a Python exception like
#    a bare KeyError.
#
# 2. A very low timeout risks failing on slow first-time PyPI downloads or
#    slow network conditions, even though the server would have succeeded
#    given more time. A very high timeout means a genuinely broken/hung
#    server takes a long time to surface as an error to the user -- there's
#    a real tradeoff between "don't fail too eagerly" and "don't hang
#    forever on a truly broken connection."
#
# 3. Raw HTML is full of tags, scripts, and styling markup that add token
#    count without adding meaning -- an LLM has to "see past" all of that
#    noise to find the actual content. Markdown keeps structure (headings,
#    lists, links) in a much more compact, readable form, which means better
#    signal-to-noise ratio per token the model has to process.
