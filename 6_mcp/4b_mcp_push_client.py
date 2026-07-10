#
#<h1>RAZ Systems </h1>
#

import asyncio
from agents.mcp.server import MCPServerStdio
import os
from dotenv import load_dotenv

async def main():
    load_dotenv()
    # The full set of MCP servers for the trader: Accounts, Push Notification and the Market
    PUSHOVER_USER_KEY  = os.getenv("PUSHOVER_USER")
    PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN")
    push_params = {
        "command": "uv",
        "args": ["run", "D:/git/agentic/6_mcp/4a_mcp_push_server.py"],
        "client_session_timeout_seconds": 60,
        "env": {
            "PUSHOVER_USER": PUSHOVER_USER_KEY,
            "PUSHOVER_TOKEN": PUSHOVER_APP_TOKEN
        }
    }


    # =========================================================
    # 2. CONNECT TO MCP SERVER
    # =========================================================
    async with MCPServerStdio(params=push_params,
          client_session_timeout_seconds=60) as server:

        print("Connected to DB MCP server")

        tools_response = await server.session.list_tools()

        for tool in tools_response.tools:
            print("\n===================")
            print("TOOL NAME:", tool.name)
            print("DESCRIPTION:", tool.description)
            print("INPUT SCHEMA:", tool.inputSchema)

        # Execute the push tool
        result = await server.session.call_tool(
            name="push",
            arguments={
                "args": {
                    "message": "Hello from MCP! This is a test push notification."
                }
            }
        )

        print("Tool result:", result)
# =========================================================
# RUN PROGRAM
# =========================================================
asyncio.run(main())