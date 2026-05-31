#
#<h1>RAZ Systems </h1>
#

import asyncio
from agents.mcp.server import MCPServerStdio

# Simple — install Node.js on Windows:
# Option 1: Direct download (easiest)

# Go to https://nodejs.org
# Download the LTS version (recommended)
# Run the .msi installer — click Next → Next → Finish
# Verify install:
# node the javascript runtime
# npm Node Package manager/installs packages
# npx Node Package exeutor
# node --version
# npm --version
# npx --version

# 
# npm install @modelcontextprotocol/sdk
# node index.js
#

async def main():

    fs_params = {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "D:/raz_training/6_mcp"
        ],
        "env": {}
    }

    async with MCPServerStdio(params=fs_params,
          client_session_timeout_seconds=60) as server:

        print("Connected to Filesystem MCP server")

        # List available tools
        tools_response = await server.session.list_tools()
        for tool in tools_response.tools:
            print("TOOL:", tool.name)

        # Read the file
        read_result = await server.session.call_tool(
            "read_file",
            {
                "path": "D:/raz_training/6_mcp/account_balance.txt"
            }
        )

        print("File contents:")
        print(read_result.content[0].text)

asyncio.run(main())