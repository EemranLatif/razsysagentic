#
# <h1>RAZ Systems </h1>
#
# ASSIGNMENT 1 — Fetch MCP Server
# =================================
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
#
# YOUR TASK:
# Connect to the fetch MCP server, list its available tools, then call the
# "fetch" tool on a URL of your choice and print the result.

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    # TODO 1: Build the fetch_params dict.
    # - command: the program to run ("uvx")
    # - args: a list containing the package name to run ("mcp-server-fetch")
    fetch_params = {
        # your code here
    }

    # TODO 2: Open the MCP session using "async with MCPServerStdio(...)".
    # - Pass params=fetch_params
    # - Pass client_session_timeout_seconds=60 (first run downloads the
    #   package from PyPI, which can take longer than the 5-second default)
    async with None:  # replace None with your MCPServerStdio(...) call

        # TODO 3: List the tools this server exposes and print them.
        tools = None
        print(tools)

        # TODO 4: Call the "fetch" tool.
        # - Pass a dict with one key, "url", set to a website of your choice
        #   (e.g. a company site, a Wikipedia page, a blog post)
        # - Store the result and print it
        response = None
        print(f"Tool Response:\n{response}")


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION QUESTIONS
# ─────────────────────────────────────────────────────
#
# 1. What would happen if you called server.session.call_tool("fetch", {})
#    with an empty dict -- no "url" key at all? Where would that error surface
#    (client side or server side), and why?
#
# 2. client_session_timeout_seconds=60 is set generously here. What's the
#    tradeoff of setting this value very high vs. very low in a real
#    application?
#
# 3. mcp-server-fetch converts HTML to Markdown before returning it. Why is
#    that conversion useful for an LLM consuming the result, compared to
#    returning raw HTML?
