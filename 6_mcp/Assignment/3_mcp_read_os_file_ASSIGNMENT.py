#
# <h1>RAZ Systems </h1>
#
# ASSIGNMENT 3 — Filesystem MCP Server
# =======================================
#
# @modelcontextprotocol/server-filesystem is an official reference MCP server
# that gives an MCP client secure, sandboxed file operations (read, write,
# list directories) restricted to a folder you specify at startup -- the
# server refuses to touch anything outside that folder.
#
# This one runs via Node's package tools rather than uv/uvx:
#   node        -- the JavaScript runtime
#   npm         -- Node Package Manager (installs packages)
#   npx         -- Node Package eXecutor (downloads + runs a package in one
#                  step, same idea as uvx but for the Node ecosystem)
#
# Setup (Windows):
#   1. Go to https://nodejs.org, download the LTS installer, run it.
#   2. Verify: node --version / npm --version / npx --version
#
# YOUR TASK:
# Connect to the filesystem MCP server scoped to D:/raz_training/6_mcp, list
# its tools, then read the account_balance.txt file produced in assignment 2b
# and print its contents.

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    # TODO 1: Build fs_params.
    # - command: "npx"
    # - args: ["-y", "@modelcontextprotocol/server-filesystem", "D:/raz_training/6_mcp"]
    #   ("-y" auto-confirms the npx download prompt so it doesn't hang
    #   waiting for interactive confirmation)
    # - env: {} (no special environment variables needed here)
    fs_params = {
        # your code here
    }

    # TODO 2: Open the session with MCPServerStdio(params=fs_params,
    # client_session_timeout_seconds=60)
    async with None:  # replace None with your MCPServerStdio(...) call

        print("Connected to Filesystem MCP server")

        # TODO 3: List available tools and print each tool's name.
        tools_response = None

        # TODO 4: Call the "read_file" tool with a "path" argument pointing
        # at D:/raz_training/6_mcp/account_balance.txt
        read_result = None

        print("File contents:")
        print(read_result.content[0].text)


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION QUESTIONS
# ─────────────────────────────────────────────────────
#
# 1. This server is scoped to a single folder (D:/raz_training/6_mcp) at
#    startup. Why is that sandboxing important for a filesystem-access tool
#    specifically, compared to, say, the fetch server from assignment 1?
#
# 2. This is the third different MCP server you've connected to in this
#    course (fetch, sqlite, filesystem), each launched with a different
#    command (uvx, uvx, npx) and different args. What stays exactly the same
#    across all three scripts, regardless of which server you're talking to?
