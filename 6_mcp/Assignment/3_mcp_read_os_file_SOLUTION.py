#
# <h1>RAZ Systems </h1>
#
# SOLUTION 3 — Filesystem MCP Server
# =====================================

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    fs_params = {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "D:/raz_training/6_mcp",
        ],
        "env": {},
    }

    async with MCPServerStdio(
        params=fs_params,
        client_session_timeout_seconds=60,
    ) as server:

        print("Connected to Filesystem MCP server")

        tools_response = await server.session.list_tools()
        for tool in tools_response.tools:
            print("TOOL:", tool.name)

        read_result = await server.session.call_tool(
            "read_file",
            {"path": "D:/raz_training/6_mcp/account_balance.txt"},
        )

        print("File contents:")
        print(read_result.content[0].text)


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION ANSWERS (sketch)
# ─────────────────────────────────────────────────────
#
# 1. A filesystem tool can read AND (depending on which tools are exposed)
#    write/delete real files on disk -- an LLM misinterpreting a request or
#    being prompt-injected could do real, hard-to-reverse damage if it had
#    unrestricted access to the whole machine. Scoping it to one folder at
#    startup means even a misbehaving agent can only affect files inside
#    that sandbox, regardless of what path string it's tricked into passing.
#    The fetch server, by contrast, only reads public web content -- there's
#    no local file to protect, so that specific risk doesn't apply there
#    (though other risks, like fetching malicious content, still do).
#
# 2. The overall shape is identical across all three: build a params dict
#    with "command" and "args" (and optionally "env"), open a session with
#    "async with MCPServerStdio(params=..., client_session_timeout_seconds=...)
#    as server", call "await server.session.list_tools()" to discover what's
#    available, and call "await server.session.call_tool(name, args_dict)" to
#    actually use one. Only the launch command/args and the specific tool
#    names/arguments change per server -- the client-side pattern for talking
#    to any MCP server stays the same, which is the whole point of MCP being
#    a standard protocol rather than a bespoke integration per tool.
