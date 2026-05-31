# 
# <h1>RAZ Systems </h1>
# 
# the program can wait for slow operations (network calls,
# subprocesses, APIs) WITHOUT freezing the entire application.
import asyncio
# Import the MCP client class.
#
# MCPServerStdio allows Python to communicate with an MCP server
# through standard input/output pipes (stdin/stdout).
#
# Think of it like:
#
# Python App  <---- text messages ---->  MCP Server
#
from agents.mcp.server import MCPServerStdio
# =====================================================
# MCP SERVER CONFIGURATION
# =====================================================

# This dictionary tells Python HOW to start the MCP server.
#
# Equivalent terminal command:
#
# uvx mcp-server-fetch
#
# Explanation:
#
# command = executable/program to run
# args    = arguments passed to that program
#
async def main():
    fetch_params = {
        "command": "uvx",
        "args": ["mcp-server-fetch"]
    }
    # It automatically:
    #
    # 1. Starts the MCP server process
    # 2. Opens communication pipes
    # 3. Establishes MCP session
    # 4. Cleans everything up automatically when done
    # If Server takes more than 60 seconds it throws timeout error
    async with MCPServerStdio(
        params=fetch_params,
        client_session_timeout_seconds=60
    ) as server:
        tools = await server.session.list_tools()    #exposes tools it has, fetch 
        print(tools)
        response1 = await server.session.call_tool(
            "fetch",
            {
                "url": "https://razsystems.com"
            }
        )
        print(f" Tool Response :\n {response1}")
asyncio.run(main())

"""
MCP TOOL CALL FLOW (6 STEPS)

1. Tool Discovery:
   The MCP server sends available tools with names, descriptions, and input schemas.

2. LLM Reads Tools:
   The LLM reviews tool metadata and understands what each tool can do.

3. User Request:
   User asks a question or gives an instruction. “What services are offered by RAZ?”

4. Tool Selection:
   The LLM decides which tool to use and generates a structured tool call
   (tool name + required parameters).
   {
        "tool_name": "fetch",
        "arguments": {
            "url": "https://example.com"
        }
   }

5. Tool Execution (Agent Runtime):
   The agent framework receives the tool call and executes it by sending
   the request to the MCP server or external system.
   Agent → MCP Server: call fetch(url=...)
6. Response + Final Answer:
   Tool result is returned to the LLM, which uses it to generate the final response. HTML / text / structured data
"""



from agents.mcp.server import MCPServerStdio
import asyncio

async def main():

    serper_params = {
        "command": "uvx",
        "args": ["serper-mcp-server"],
        "env": {
            "SERPER_API_KEY": "a7648495593312f27771ecb236dea9a88be6c713"
        }
    }

    async with MCPServerStdio(params=serper_params) as server:

        tools = await server.session.list_tools()
        print(tools)

asyncio.run(main())